#!/usr/bin/env python3
"""
NeuralCline State Engine — Safe JSON Operations Library
=======================================================
Purpose: Eliminates inline `python3 -c` crash pattern by providing
stable, file-based Python operations for all session state management.

Usage: python3 /root/NeuralCline/lib/state_engine.py <command> [args...]
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from collections import defaultdict
import re

# Paths
SESSION_DIR = "/root/.session-state"
STATE_FILE = os.path.join(SESSION_DIR, "current-state.json")
CHECKPOINT_FILE = os.path.join(SESSION_DIR, "checkpoint.json")
CRASH_LOG = os.path.join(SESSION_DIR, "crash-log.ndjson")
FAILURE_POINTS = os.path.join(SESSION_DIR, "failure-points.json")
MASTER_PROFILE = "/root/master_profile.md"

os.makedirs(SESSION_DIR, exist_ok=True)


def read_json(path, default=None):
    """Safely read a JSON file, returning default on error."""
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
    """Safely write a JSON file."""
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def gen_uuid():
    return str(uuid.uuid4())


def timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ===================== COMMANDS =====================

def cmd_update_state(args):
    """Update current-state.json with new tool call data."""
    command = args[0] if len(args) > 0 else ""
    exit_code = int(args[1]) if len(args) > 1 else 0
    output_size = int(args[2]) if len(args) > 2 else 0
    proximity = int(args[3]) if len(args) > 3 else 0
    file_scope = args[4] if len(args) > 4 else ""

    state = read_json(STATE_FILE, {})
    if not state.get('session_id'):
        state['session_id'] = gen_uuid()

    now = timestamp()
    state['last_updated'] = now
    state['last_command'] = command
    state['last_exit_code'] = exit_code
    state['last_output_size'] = output_size
    state['last_proximity'] = proximity
    state['tool_call_count'] = state.get('tool_call_count', 0) + 1

    max_tokens = 1048576
    estimated = state['tool_call_count'] * 2000 + len(command) * 10
    context_pct = min(100, int(estimated * 100 / max_tokens))
    state['context_usage_pct'] = context_pct
    state['current_context_tokens'] = estimated
    state['max_context_tokens'] = max_tokens

    state['session_start_count'] = state.get('session_start_count', 0) + 1
    state['total_session_count'] = max(
        state.get('total_session_count', 0),
        state['session_start_count']
    )

    if isinstance(state.get('file_scope', ''), str):
        if file_scope.strip():
            state['file_scope_list'] = file_scope.split(',')
        else:
            state['file_scope_list'] = []

    write_json(STATE_FILE, state)
    print(f"context_usage_pct={context_pct}")
    print(f"tool_call_count={state['tool_call_count']}")


def cmd_write_crash_log(args):
    """Append a crash log entry to crash-log.ndjson."""
    command = args[0] if len(args) > 0 else ""
    exit_code = int(args[1]) if len(args) > 1 else 0
    output_size = int(args[2]) if len(args) > 2 else 0
    proximity = int(args[3]) if len(args) > 3 else 0
    file_scope = args[4] if len(args) > 4 else ""
    error_msg = args[5] if len(args) > 5 else ""

    state = read_json(STATE_FILE, {})
    entry = {
        "timestamp": timestamp(),
        "session_id": state.get('session_id', gen_uuid()),
        "command": command,
        "exit_code": exit_code,
        "output_size_lines": output_size,
        "crash_proximity_score": proximity,
        "file_scope": [file_scope] if file_scope.strip() else [],
        "error": error_msg
    }

    with open(CRASH_LOG, 'a') as f:
        f.write(json.dumps(entry) + "\n")

    # Trim if > 1000 lines
    try:
        lines = open(CRASH_LOG).readlines()
        if len(lines) > 1000:
            with open(CRASH_LOG, 'w') as f:
                f.writelines(lines[-1000:])
    except:
        pass

    print(f"crash_logged=True")


def cmd_update_failure_points(args):
    """Recompute failure-points.json from crash log."""
    entries = []
    try:
        if os.path.exists(CRASH_LOG):
            with open(CRASH_LOG) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except:
                            pass
    except:
        pass

    def normalize_cmd(cmd):
        cmd = re.sub(r'--\w+=\S+', '', cmd)
        cmd = re.sub(r'/[^\s]+', '/...', cmd)
        cmd = re.sub(r'\d+', 'N', cmd)
        cmd = re.sub(r'\s+', ' ', cmd).strip()
        return cmd[:60]

    pattern_counts = defaultdict(
        lambda: {'count': 0, 'proximities': [],
                 'last_seen': '', 'commands': []}
    )

    for e in entries:
        cmd = e.get('command', '')
        pattern = normalize_cmd(cmd) or '(empty)'
        pattern_counts[pattern]['count'] += 1
        pattern_counts[pattern]['proximities'].append(
            e.get('crash_proximity_score', 0)
        )
        pattern_counts[pattern]['last_seen'] = e.get('timestamp', '')
        if len(pattern_counts[pattern]['commands']) < 3:
            pattern_counts[pattern]['commands'].append(cmd[:80])

    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    points = []
    for pattern, data in pattern_counts.items():
        count = data['count']
        proximities = data['proximities']
        avg_prox = sum(proximities) / len(proximities) if proximities else 0
        max_prox = max(proximities) if proximities else 0

        recency_factor = 1.0
        if data['last_seen']:
            try:
                last = datetime.fromisoformat(
                    data['last_seen'].replace('Z', '+00:00')
                )
                delta = (datetime.now(timezone.utc) - last.replace(tzinfo=timezone.utc)).total_seconds()
                if delta > 3600:
                    recency_factor = max(0.1, 1.0 - (delta - 3600) / 86400)
            except:
                pass

        weight = count * (avg_prox / 100) * recency_factor
        points.append({
            'pattern': pattern,
            'count': count,
            'avg_proximity': round(avg_prox, 1),
            'max_proximity': round(max_prox, 1),
            'weight': round(weight, 2),
            'last_seen': data['last_seen'],
            'example_commands': data['commands']
        })

    points.sort(key=lambda p: p['weight'], reverse=True)

    fps = {
        'failure_points': points,
        'last_updated': now,
        'total_crash_events': len(entries)
    }

    write_json(FAILURE_POINTS, fps)
    print(f"failure_points_updated={len(points)}")
    print(f"total_events={len(entries)}")


def cmd_compute_proximity(args):
    """Compute crash proximity score (0-100) for a command.
    
    Enhanced with timing metrics:
    - 35% Historical failure pattern matching
    - 20% Context usage pressure
    - 15% Command size & complexity
    - 15% Known risk patterns
    - 15% ⏱️ Execution Emulation Factor (EEF) + timeout proximity (NEW)
    """
    command = args[0] if len(args) > 0 else ""
    file_scope = args[1] if len(args) > 1 else ""

    state = read_json(STATE_FILE, {})
    context_usage = state.get('context_usage_pct', 0)
    timing = state.get('timing_metrics', {})
    score = 0
    matched_pattern = "none"

    # 1. Historical failure point match (35%)
    fps = read_json(FAILURE_POINTS, {'failure_points': []})
    points = fps.get('failure_points', [])

    if points:
        def normalize(cmd):
            cmd = re.sub(r'--\w+=\S+', '', cmd)
            cmd = re.sub(r'/[^\s]+', '/...', cmd)
            cmd = re.sub(r'\d+', 'N', cmd)
            return cmd[:80]

        normalized = normalize(command)
        max_weight = 0
        for p in points:
            pattern = p.get('pattern', '')
            weight = p.get('weight', 0)
            if pattern and pattern in normalized:
                if weight > max_weight:
                    max_weight = weight
                    matched_pattern = pattern
        score += int(max_weight * 35 / 100)

    # 2. Context usage (20%)
    if context_usage > 60:
        ctx_score = min(20, (context_usage - 60) * 20 // 40)
        score += ctx_score

    # 3. Command size + complexity (15%)
    cmd_len = len(command)
    complexity = timing.get('complexity', 1)
    size_base = 0
    if cmd_len > 100:
        size_base = min(10, (cmd_len - 100) * 10 // 900)
    # Complexity adds to this: complexity 1-10, maps to 0-5 bonus
    complexity_bonus = min(5, complexity)
    score += min(15, size_base + complexity_bonus)

    # 4. Known risk patterns (15%)
    risk_patterns = [
        r'(find|grep -r|cat.*\.(log|tar|gz|zip)|npm install|pip install)',
        r'(ls -la /root|ll /root|tree|du -sh)'
    ]
    if re.search(risk_patterns[0], command):
        score += 15
    elif re.search(risk_patterns[1], command):
        score += 10

    # 5. ⏱️ Timing metrics — Execution Emulation Factor (15%) (NEW)
    eef = timing.get('execution_emulation_factor', 1.0)
    timeout_prox = timing.get('timeout_proximity', 0)
    rolling_avg = timing.get('rolling_avg_ms', 0)

    # EEF contribution: floor at 0 (no negative scores for fast systems)
    # map: 1.0→0, 1.5→5, 2.0→10, 2.5→13, 3.0→15
    if eef > 1.0:
        eef_score = min(15, int((eef - 1.0) * 10))
    else:
        eef_score = 0  # No penalty when system is running efficiently

    # Timeout proximity adds bonus if it's high
    if timeout_prox >= 80:
        eef_score = min(15, eef_score + 5)  # penalty for high timeout risk
    elif timeout_prox >= 60:
        eef_score = min(15, eef_score + 3)

    score += eef_score

    # If EEF is extremely high, amplify the pattern match
    if eef > 2.5 and max_weight > 0:
        matched_pattern = f"{matched_pattern} [EEF={eef}]"

    print(f"CRASH_PROXIMITY={score}")
    print(f"MATCHED_PATTERN={matched_pattern}")
    print(f"CONTEXT_USAGE={context_usage}")
    print(f"EEF={eef}")
    print(f"TIMEOUT_PROXIMITY={timeout_prox}")


def cmd_read_checkpoint(args):
    """Read and print the current checkpoint as JSON."""
    cp = read_json(CHECKPOINT_FILE, {'error': 'no_checkpoint'})
    print(json.dumps(cp, indent=2))


def cmd_generate_checkpoint(args):
    """Generate a complete checkpoint.json."""
    state = read_json(STATE_FILE, {})
    fps = read_json(FAILURE_POINTS, {'failure_points': []})
    crash_events = 0
    try:
        if os.path.exists(CRASH_LOG):
            crash_events = sum(1 for _ in open(CRASH_LOG))
    except:
        pass

    sid = state.get('session_id', gen_uuid())
    now = timestamp()
    tool_calls = state.get('tool_call_count', 0)
    ctx_pct = state.get('context_usage_pct', 0)
    last_cmd = state.get('last_command', '')
    exit_code = state.get('last_exit_code', 0)

    success_rate = 100
    if crash_events > 0 and tool_calls > 0:
        success_rate = max(0, (tool_calls - crash_events) * 100 // tool_calls)

    # Top failure point
    fp_match = "none"
    prox_score = 0
    points = fps.get('failure_points', [])
    if points:
        fp_match = points[0].get('pattern', 'none')
        prox_score = int(points[0].get('weight', 0))

    # Goals from state or crash log
    goals = state.get('active_goals', [])
    if not goals:
        try:
            if os.path.exists(CRASH_LOG):
                with open(CRASH_LOG) as f:
                    for line in f:
                        try:
                            e = json.loads(line)
                            cmd = e.get('command', '')
                            if cmd:
                                goals.insert(
                                    0,
                                    f"Continue from: {cmd[:60]}..."
                                )
                        except:
                            pass
                goals = goals[:3]
        except:
            pass

    # Next steps
    next_steps = state.get('next_steps', [])
    if not next_steps:
        next_steps = [
            "Run: source /root/rehydration.md to restore full context",
            "Check /root/master_profile.md for workspace context"
        ]
        try:
            if os.path.exists(CRASH_LOG):
                with open(CRASH_LOG) as f:
                    lines = f.readlines()
                if lines:
                    last = json.loads(lines[-1].strip())
                    cmd = last.get('command', '')
                    if cmd:
                        next_steps.insert(
                            0,
                            f"Review result of: {cmd[:60]}..."
                        )
        except:
            pass

    file_scope = state.get('file_scope_list', [])

    cp = {
        'session_id': sid,
        'timestamp': now,
        'total_tool_calls': tool_calls,
        'success_rate': success_rate,
        'context_usage_pct': ctx_pct,
        'total_crash_events': crash_events,
        'last_command': last_cmd,
        'last_exit_code': exit_code,
        'active_goals': goals,
        'next_steps': next_steps,
        'file_scope': file_scope,
        'crash_proximity_score': prox_score,
        'failure_point_match': fp_match
    }

    write_json(CHECKPOINT_FILE, cp)
    print(f"CHECKPOINT_SAVED session_id={sid} tool_calls={tool_calls} ctx={ctx_pct}%")


def cmd_check_checkpoint(args):
    """Check if checkpoint exists and print recovery info."""
    cp = read_json(CHECKPOINT_FILE, {})
    tools = cp.get('total_tool_calls', 0)
    ctx = cp.get('context_usage_pct', 0)
    cmd = cp.get('last_command', '')
    if tools > 0 or ctx > 0 or cmd:
        print(f'[Neural Safety] Session checkpoint found: {tools} tools, {ctx}% context')
        if cmd:
            print(f'[Neural Safety] Last command: {cmd[:60]}...')
        print('[Neural Safety] Run: source /root/rehydration.md')
    else:
        print('[Neural Safety] No active checkpoint found')


def cmd_read_failure_points(args):
    """Print top failure points."""
    fps = read_json(FAILURE_POINTS, {'failure_points': []})
    points = fps.get('failure_points', [])
    for i, p in enumerate(points[:5]):
        print(
            f"#{i+1} [{p.get('weight', 0):.0f}] "
            f"{p.get('pattern', '?')[:60]} (x{p.get('count', 0)})"
        )
    if len(points) > 5:
        print(f"... and {len(points) - 5} more")


def cmd_help(args):
    """Print available commands."""
    print("NeuralCline State Engine — Commands:")
    print("  update_state <cmd> <exit> <size> <prox> [scope]")
    print("  write_crash_log <cmd> <exit> <size> <prox> [scope] [error]")
    print("  update_failure_points")
    print("  compute_proximity <command> [file_scope]")
    print("  read_checkpoint")
    print("  generate_checkpoint")
    print("  check_checkpoint")
    print("  read_failure_points")
    print("  help")


# Command dispatch
COMMANDS = {
    'update_state': cmd_update_state,
    'write_crash_log': cmd_write_crash_log,
    'update_failure_points': cmd_update_failure_points,
    'compute_proximity': cmd_compute_proximity,
    'read_checkpoint': cmd_read_checkpoint,
    'generate_checkpoint': cmd_generate_checkpoint,
    'check_checkpoint': cmd_check_checkpoint,
    'read_failure_points': cmd_read_failure_points,
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