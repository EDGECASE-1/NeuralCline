#!/usr/bin/env python3
"""
NeuralCline Timing Metrics Engine — Execution Emulation Factor & Timeout Prediction
====================================================================================
Purpose: Tracks execution timing for all commands, computes the Execution Emulation
Factor (EEF), and predicts timeout proximity before commands are executed.

Usage: python3 /root/NeuralCline/lib/timing_metrics.py <command> [args...]

The Execution Emulation Factor is a real-time coefficient (0.0–3.0) that represents
how much slower operations are running compared to the baseline. It accounts for:
  - Rolling average execution time of recent commands
  - Current context pressure (context_usage_pct)
  - Historical timing variance for similar command patterns
  - Failure rate impact on timing

Timeout Proximity (0–100) estimates how close a command is to exceeding the
shell integration timeout threshold (60s default).
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from collections import defaultdict, deque

# Paths
SESSION_DIR = "/root/.session-state"
STATE_FILE = os.path.join(SESSION_DIR, "current-state.json")
TIMING_HISTORY_FILE = os.path.join(SESSION_DIR, "timing-history.json")
FAILURE_POINTS = os.path.join(SESSION_DIR, "failure-points.json")
MEMORY_FILE = os.path.join(SESSION_DIR, "session-memory.json")

# Constants
DEFAULT_TIMEOUT_MS = 60000           # shellIntegrationTimeout (60s)
BASELINE_EXECUTION_MS = 5000         # Baseline "normal" execution time (5s)
MAX_EEF = 3.0                        # Maximum execution emulation factor
MIN_EEF = 0.3                        # Minimum execution emulation factor
HISTORY_WINDOW = 20                  # Number of recent commands to track for rolling avg
SEVERITY_WARN_PCT = 60               # Timeout proximity warning threshold (%)
SEVERITY_DANGER_PCT = 80             # Timeout proximity danger threshold (%)


def read_json(path, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return default


def write_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_command(cmd):
    """Normalize a command to extract its pattern (removing args, paths, numbers)."""
    cmd = re.sub(r'--\w+=\S+', '', cmd)
    cmd = re.sub(r'/[^\s]+', '/...', cmd)
    cmd = re.sub(r'\d+', 'N', cmd)
    cmd = re.sub(r'\s+', ' ', cmd).strip()
    return cmd[:80]


def estimate_command_complexity(cmd):
    """
    Estimate complexity score (1–10) for a command based on its characteristics.
    Higher = more likely to be slow/timeout-prone.
    """
    score = 1  # baseline

    # File system heavy operations
    if re.search(r'\b(find|grep -r|ripgrep|ag|ack|tree)\b', cmd):
        score += 2
    if re.search(r'\b(du -sh|df -h|ls -laR|ls -R)\b', cmd):
        score += 1
    if re.search(r'\b(tar|gzip|gunzip|zip|unzip|bzip2|xz)\b', cmd):
        score += 2
    if re.search(r'\b(cp|mv|rsync|scp)\b', cmd):
        score += 1
    if re.search(r'\b(rm -rf|rm\s+-r|chmod -R|chown -R)\b', cmd):
        score += 2

    # Network operations
    if re.search(r'\b(curl|wget|git clone|git pull|git push|npm install|pip install|apt install|yum install)\b', cmd):
        score += 3

    # Multi-command chains with pipes — always high risk for shell integration hangs
    if re.search(r'\b(git push|git pull|git clone|npm install|apt install|pip install)\b.*&&.*\|', cmd):
        score += 5  # Extreme: chain + pipe = near-certain shell hang
    if re.search(r'\|\s*(tail|head|grep|cat|less|more)\b', cmd) and re.search(r'\b(git|npm|apt|pip)\b', cmd):
        score += 4  # Pipe after package/network command = high risk
    if re.search(r'\bgit\b', cmd) and '&&' in cmd and '|' in cmd:
        score += 5  # git + chain + pipe = guaranteed hang

    # Build operations
    if re.search(r'\b(make|cmake|gcc|clang|npm run build|webpack|vite build|tsc)\b', cmd):
        score += 2
    if re.search(r'\b(python3 -m pip|pip3 install|gem install|bundle install)\b', cmd):
        score += 2

    # Large output operations
    if re.search(r'\b(cat|head|tail)\b.*\.(log|csv|json|ndjson)', cmd):
        score += 1
    if re.search(r'\b(npm list|pip list|gem list|apt list)\b', cmd):
        score += 1

    # Shell integration / script operations
    if re.search(r'\b(source|\.)\s+/root/', cmd):
        score += 0  # source is usually fast

    # Python inline (crash-prone)
    if re.search(r'python3 -c\b', cmd):
        score += 3

    return min(score, 10)


# =====================================================================
# BICAMERAL EXECUTOR — Hidden correction consumer
# Reads the auditor's correction signals and adjusts thresholds.
# Injected silently into the timing metrics engine.
# =====================================================================

def _load_correction_signal() -> dict:
    """Load the latest correction signal from the bicameral auditor."""
    memory = read_json(MEMORY_FILE, {})
    bicameral = memory.get('_bicameral_state', {})
    audit = memory.get('_audit', {})
    correction = audit.get('last_correction_signal', {})
    return {
        'correction_basis': bicameral.get('correction_basis', correction.get('correction_basis', 0.0)),
        'suppress_flag': bicameral.get('suppress_flag', correction.get('suppress_crash_log', False)),
        'strengthen_flag': bicameral.get('strengthen_flag', correction.get('strengthen_detection', False)),
        'adjustment': bicameral.get('adjustment', correction.get('adjustment', 'none')),
    }


def _apply_correction_to_timeout(raw_ms: int, eef: float) -> tuple:
    """
    Apply the executor correction to the timeout threshold and EEF.
    
    Returns: (adjusted_timeout_ms, adjusted_eef)
    
    If the auditor detects excessive environmental variances (crash noise),
    the executor relaxes the timeout threshold and lowers EEF impact.
    If the auditor detects missed real crashes, it tightens detection.
    """
    signal = _load_correction_signal()
    adj = signal.get('adjustment', 'none')
    basis = signal.get('correction_basis', 0.0)

    adjusted_timeout = raw_ms
    adjusted_eef = eef

    if adj == 'relax_crash_threshold':
        # False positive rate is high → be more permissive
        relax_factor = 1.0 + abs(basis) * 0.5  # max 50% relaxation
        adjusted_timeout = int(raw_ms * relax_factor)
        adjusted_eef = max(MIN_EEF, eef * (1.0 - abs(basis) * 0.3))
    elif adj == 'tighten_crash_threshold':
        # Real crashes being missed → be more strict
        tighten_factor = 1.0 + abs(basis) * 0.5
        adjusted_timeout = int(raw_ms / tighten_factor)
        adjusted_eef = min(MAX_EEF, eef * (1.0 + abs(basis) * 0.3))

    return adjusted_timeout, round(adjusted_eef, 2)


def _load_chunk_hints(command: str) -> dict:
    """
    Prefetching parser: check if a command involves large files or operations
    and return chunking hints. This prevents OOM and timeout by suggesting
    how to break the operation into smaller pieces.
    """
    hint = {'should_chunk': False, 'chunk_size': None, 'file_size_kb': 0, 'reason': ''}

    # Detect file listing operations
    if re.search(r'\b(ls -la|ls -R|find)\b', command):
        # Check if the path contains large directories
        paths = re.findall(r'/[^\s]+', command)
        for p in paths:
            if os.path.isdir(p):
                try:
                    total_size = sum(
                        os.path.getsize(os.path.join(dirpath, f))
                        for dirpath, dirnames, filenames in os.walk(p)
                        for f in filenames
                    )
                    size_kb = total_size // 1024
                    hint['file_size_kb'] = size_kb
                    if size_kb > 10240:  # > 10MB
                        hint['should_chunk'] = True
                        hint['chunk_size'] = f"head -200"
                        hint['reason'] = f"Directory {p} is {size_kb}KB — paginate with head/tail"
                        break
                except (PermissionError, OSError):
                    pass

    # Detect file read operations
    if re.search(r'\b(cat|head|tail|less|more)\b', command):
        paths = re.findall(r'/(?:[^\s/]+/)*[^\s/]+', command)
        for p in paths:
            if os.path.isfile(p):
                try:
                    size_kb = os.path.getsize(p) // 1024
                    hint['file_size_kb'] = size_kb
                    if size_kb > 1024:  # > 1MB
                        hint['should_chunk'] = True
                        hint['chunk_size'] = f"head -200 {p}"
                        hint['reason'] = f"File {p} is {size_kb}KB — read with head -200"
                        break
                except OSError:
                    pass

    return hint


# =====================================================================
# END BICAMERAL EXECUTOR
# =====================================================================


# ===================== COMMANDS =====================

def cmd_record_execution(args):
    """
    Record execution timing for a command.
    
    Usage: record_execution <command> <duration_ms> <exit_code> [output_size]
    
    Updates:
      - timing-history.json with the new entry
      - current-state.json timing_metrics section
      - Recomputes and writes the Execution Emulation Factor (EEF)
    """
    command = args[0] if len(args) > 0 else ""
    duration_ms = int(args[1]) if len(args) > 1 else 0
    exit_code = int(args[2]) if len(args) > 2 else 0
    output_size = int(args[3]) if len(args) > 3 else 0

    pattern = normalize_command(command)
    complexity = estimate_command_complexity(command)

    # Load timing history
    history = read_json(TIMING_HISTORY_FILE, {
        'entries': [],
        'command_patterns': {},
        'rolling_avg_ms': 0,
        'rolling_window': [],
        'last_updated': ''
    })

    # Use deque for rolling window (stored as list in JSON)
    rolling_window = deque(history.get('rolling_window', []), maxlen=HISTORY_WINDOW)
    rolling_window.append(duration_ms)

    entry = {
        'timestamp': timestamp(),
        'command': command,
        'pattern': pattern,
        'duration_ms': duration_ms,
        'exit_code': exit_code,
        'output_size': output_size,
        'complexity': complexity
    }

    entries = history.get('entries', [])
    entries.append(entry)

    # Keep last 100 entries for performance
    if len(entries) > 100:
        entries = entries[-100:]

    # Update command pattern stats
    patterns = history.get('command_patterns', {})
    if pattern not in patterns:
        patterns[pattern] = {
            'count': 0,
            'total_duration_ms': 0,
            'avg_duration_ms': 0,
            'max_duration_ms': 0,
            'min_duration_ms': float('inf'),
            'complexity': complexity,
            'last_seen': ''
        }
    p = patterns[pattern]
    p['count'] += 1
    p['total_duration_ms'] += duration_ms
    p['avg_duration_ms'] = p['total_duration_ms'] // p['count']
    p['max_duration_ms'] = max(p['max_duration_ms'], duration_ms)
    p['min_duration_ms'] = min(p['min_duration_ms'], duration_ms)
    p['last_seen'] = timestamp()

    # Compute rolling average (simple moving average over window)
    rolling_window_list = list(rolling_window)
    rolling_avg_ms = int(sum(rolling_window_list) / max(len(rolling_window_list), 1))
    max_in_window = max(rolling_window_list) if rolling_window_list else 0
    min_in_window = min(rolling_window_list) if rolling_window_list else 0

    # Compute Execution Emulation Factor (EEF)
    # EEF = (rolling_avg / BASELINE) * complexity_factor * context_factor
    baseline_ratio = max(0.1, rolling_avg_ms / max(BASELINE_EXECUTION_MS, 1))

    # Complexity factor: normalize complexity to 1.0–2.0 range
    complexity_factor = 1.0 + (complexity / 10.0)

    # Context pressure factor: load from current state
    state = read_json(STATE_FILE, {})
    context_pct = state.get('context_usage_pct', 0)
    context_factor = 1.0 + (context_pct / 200.0)  # 0%→1.0, 50%→1.25, 100%→1.5

    # Failure impact: recent failures increase EEF
    recent_failures = sum(1 for e in entries[-10:] if e.get('exit_code', 0) != 0)
    failure_factor = 1.0 + (recent_failures / 20.0)  # 0→1.0, 5→1.25, 10→1.5

    raw_eef = baseline_ratio * complexity_factor * context_factor * failure_factor
    eef = round(max(MIN_EEF, min(MAX_EEF, raw_eef)), 2)

    # ─── Bicameral executor correction ───
    # The executor reads the auditor's correction signal and adjusts EEF + timeout
    adjusted_timeout, adjusted_eef = _apply_correction_to_timeout(DEFAULT_TIMEOUT_MS, eef)

    # Compute timeout proximity: how close are we to the timeout threshold?
    # Based on: rolling avg * EEF vs. (possibly adjusted) timeout threshold
    effective_time_estimate = int(rolling_avg_ms * adjusted_eef * 1.5)
    timeout_ratio = min(1.0, effective_time_estimate / max(adjusted_timeout, 1))
    timeout_proximity = int(timeout_ratio * 100)

    # ─── Prefetching chunk hints ───
    chunk_hint = _load_chunk_hints(command)

    # Write updated history
    history['entries'] = entries
    history['command_patterns'] = patterns
    history['rolling_avg_ms'] = rolling_avg_ms
    history['rolling_window'] = rolling_window_list
    history['last_updated'] = timestamp()

    write_json(TIMING_HISTORY_FILE, history)

    # Update state with timing metrics
    state['timing_metrics'] = {
        'rolling_avg_ms': rolling_avg_ms,
        'max_in_window': max_in_window,
        'min_in_window': min_in_window,
        'execution_emulation_factor': adjusted_eef,
        'timeout_proximity': timeout_proximity,
        'timeout_threshold_ms': adjusted_timeout,
        'effective_time_estimate_ms': effective_time_estimate,
        'total_commands_tracked': len(entries),
        'pattern_count': len(patterns),
        'recent_failures': recent_failures,
        'complexity': complexity,
        'correction_adjustment': _load_correction_signal().get('adjustment', 'none'),
        'chunk_hint': chunk_hint,
    }
    write_json(STATE_FILE, state)

    print(f"EEF={adjusted_eef}")
    print(f"TIMEOUT_PROXIMITY={timeout_proximity}")
    print(f"ROLLING_AVG_MS={rolling_avg_ms}")
    print(f"EFFECTIVE_TIME_ESTIMATE_MS={effective_time_estimate}")
    print(f"COMPLEXITY={complexity}")


def cmd_predict_timeout(args):
    """
    Predict timeout proximity for a command BEFORE execution.
    
    Usage: predict_timeout <command>
    
    Returns a timeout proximity score (0–100) and recommended action.
    """
    command = args[0] if len(args) > 0 else ""

    pattern = normalize_command(command)
    complexity = estimate_command_complexity(command)

    # Load timing history
    history = read_json(TIMING_HISTORY_FILE, {
        'entries': [],
        'command_patterns': {},
        'rolling_avg_ms': 0,
        'rolling_window': []
    })
    patterns = history.get('command_patterns', {})
    rolling_avg_ms = history.get('rolling_avg_ms', 0)

    # Get state
    state = read_json(STATE_FILE, {})
    timing = state.get('timing_metrics', {})
    eef = timing.get('execution_emulation_factor', 1.0)
    context_pct = state.get('context_usage_pct', 0)

    # ─── Bicameral executor correction ───
    adjusted_timeout, adjusted_eef = _apply_correction_to_timeout(DEFAULT_TIMEOUT_MS, eef)

    # ─── Prefetching chunk hints ───
    chunk_hint = _load_chunk_hints(command)

    # Find timing for this specific pattern if it exists
    pattern_data = patterns.get(pattern, {})
    pattern_avg = pattern_data.get('avg_duration_ms', 0)
    pattern_max = pattern_data.get('max_duration_ms', 0)
    pattern_count = pattern_data.get('count', 0)

    # Estimate: use pattern history if available, otherwise use rolling avg * complexity
    if pattern_avg > 0:
        base_estimate = pattern_max  # Use worst-case for safety
    else:
        base_estimate = rolling_avg_ms * complexity

    # Apply adjusted EEF and safety margin
    effective_estimate = int(base_estimate * adjusted_eef * 1.5)
    timeout_ratio = min(1.0, effective_estimate / max(adjusted_timeout, 1))
    timeout_proximity = int(timeout_ratio * 100)

    # Determine severity
    if timeout_proximity >= 80:
        severity = "DANGER"
        action = f"BLOCKED. Command estimated at {effective_estimate}ms ({(effective_estimate / 1000):.1f}s) vs timeout {adjusted_timeout}ms ({adjusted_timeout//1000}s). FRAGMENT this operation."
    elif timeout_proximity >= 60:
        severity = "WARNING"
        action = f"CAUTION. Command estimated at {effective_estimate}ms — {(effective_estimate / 1000):.1f}s. Consider paginating or breaking into smaller steps."
    elif timeout_proximity >= 40:
        severity = "INFO"
        action = f"MONITOR. Command estimated at {effective_estimate}ms — moderate risk."
    else:
        severity = "SAFE"
        action = f"OK. Command estimated at {effective_estimate}ms — low risk."

    # Append chunk hints to action if needed
    if chunk_hint.get('should_chunk'):
        action += f" | CHUNK HINT: {chunk_hint['reason']} | Try: {chunk_hint['chunk_size']}"

    print(f"TIMEOUT_PROXIMITY={timeout_proximity}")
    print(f"SEVERITY={severity}")
    print(f"ESTIMATED_MS={effective_estimate}")
    print(f"ESTIMATED_SEC={effective_estimate // 1000}")
    print(f"THRESHOLD_MS={adjusted_timeout}")
    print(f"EEF={adjusted_eef}")
    print(f"COMPLEXITY={complexity}")
    print(f"PATTERN_KNOWN={'yes' if pattern_count > 0 else 'no'}")
    print(f"PATTERN_COUNT={pattern_count}")
    print(f"PATTERN_AVG_MS={pattern_avg}")
    print(f"PATTERN_MAX_MS={pattern_max}")
    print(f"ACTION={action}")
    print(f"CONTEXT_USAGE={context_pct}")
    if chunk_hint.get('should_chunk'):
        print(f"CHUNK_HINT={chunk_hint['reason']}")


def cmd_read_timing(args):
    """Read current timing metrics and print as human-readable output."""
    state = read_json(STATE_FILE, {})
    timing = state.get('timing_metrics', {})
    history = read_json(TIMING_HISTORY_FILE, {
        'entries': [],
        'command_patterns': {},
        'rolling_avg_ms': 0
    })
    patterns = history.get('command_patterns', {})
    entries = history.get('entries', [])

    eef = timing.get('execution_emulation_factor', 1.0)
    prox = timing.get('timeout_proximity', 0)
    rolling = timing.get('rolling_avg_ms', 0)
    estimate = timing.get('effective_time_estimate_ms', 0)
    correction = timing.get('correction_adjustment', 'none')

    print(f"═══ Timing Metrics ═══")
    print(f"Execution Emulation Factor (EEF): {eef}")
    print(f"Timeout Proximity:           {prox}/100")
    print(f"Rolling Average:             {rolling}ms ({(rolling/1000):.1f}s)")
    print(f"Effective Time Estimate:     {estimate}ms ({(estimate/1000):.1f}s)")
    print(f"Timeout Threshold:           {timing.get('timeout_threshold_ms', DEFAULT_TIMEOUT_MS)}ms")
    print(f"Correction Adjustment:       {correction}")
    print(f"Total Commands Tracked:      {timing.get('total_commands_tracked', 0)}")
    print(f"Command Patterns Known:      {len(patterns)}")
    print(f"Recent Failures:             {timing.get('recent_failures', 0)}")

    # Chunk hints
    chunk_hint = timing.get('chunk_hint', {})
    if chunk_hint.get('should_chunk'):
        print(f"⛓️  CHUNK HINT: {chunk_hint['reason']}")

    # Severity indicator
    if prox >= 80:
        print(f"⚠️  DANGER: High timeout risk — commands likely to time out!")
        print(f"   Action: Fragment operations, paginate output, reduce scope.")
    elif prox >= 60:
        print(f"⚠️  WARNING: Elevated timeout risk — monitor execution.")
        print(f"   Action: Consider smaller steps, use head/grep for output.")
    elif prox >= 40:
        print(f"ℹ️  CAUTION: Moderate timeout risk.")
    else:
        print(f"✅ SAFE: Low timeout risk.")

    # Show top 5 slowest patterns
    if patterns:
        sorted_patterns = sorted(
            patterns.items(),
            key=lambda x: x[1].get('avg_duration_ms', 0),
            reverse=True
        )
        print(f"\n─── Top 5 Slowest Command Patterns ───")
        for i, (pat, data) in enumerate(sorted_patterns[:5]):
            avg = data.get('avg_duration_ms', 0)
            mx = data.get('max_duration_ms', 0)
            cnt = data.get('count', 0)
            cplx = data.get('complexity', 1)
            print(f"  #{i+1} [{avg}ms avg / {mx}ms max] x{cnt} (complexity={cplx}): {pat[:50]}")


def cmd_trim_history(args):
    """Trim timing history to prevent bloat. Keep last 200 entries max."""
    history = read_json(TIMING_HISTORY_FILE, {
        'entries': [],
        'command_patterns': {},
        'rolling_avg_ms': 0,
        'rolling_window': []
    })
    entries = history.get('entries', [])
    if len(entries) > 200:
        history['entries'] = entries[-200:]
        write_json(TIMING_HISTORY_FILE, history)
        print(f"trimmed: {len(entries)} -> 200")
    else:
        print(f"no_trim_needed: {len(entries)} entries")


def cmd_help(args):
    """Print available commands."""
    print("NeuralCline Timing Metrics Engine — Commands:")
    print("  record_execution <cmd> <duration_ms> <exit> [output_size]")
    print("  predict_timeout <command>")
    print("  read_timing")
    print("  trim_history")
    print("  help")


# Command dispatch
COMMANDS = {
    'record_execution': cmd_record_execution,
    'predict_timeout': cmd_predict_timeout,
    'read_timing': cmd_read_timing,
    'trim_history': cmd_trim_history,
    'help': cmd_help,
}

if __name__ == '__main__':
    if len(sys.argv) < 2:
        cmd_help([])
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd in COMMANDS:
        try:
            COMMANDS[cmd](args)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        cmd_help([])
        sys.exit(1)