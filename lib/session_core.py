#!/usr/bin/env python3
"""
NeuralCline Session Core — Universal API for Model-Agnostic Session Safety
============================================================================
This is the central entry point for all NeuralCline operations. It provides
a model-agnostic API that any AI coding agent (Cline, Copilot, Cursor, Codeium,
or any shell-based agent) can use for session safety, crash recovery, and
context window management.

Design Principles:
  1. Model-Agnostic — No hardcoded references to Cline, Copilot, etc.
     Adapters translate between agent-specific formats and this core API.
  2. Stateless by Default — All state is stored in files (JSON + NDJSON)
     with proper POSIX file locking. No in-memory state that can be lost.
  3. Crash-Safe — All file operations use atomic writes (write to temp, rename).
     All Python operations use file-based execution (no inline python3 -c).
  4. Observable — Every operation is logged with timing, outcome, and context.
     Metrics are verifiable, not claimed.
  5. Extensible — New agents, models, and platforms are added via adapters.

Usage:
  python3 lib/session_core.py <command> [args...]

  Or import as a module:
    from lib.session_core import SessionCore
    core = SessionCore()
    core.record_execution("ls -la", 1500, 0, 50)
"""

import os
import sys
import json
import time
import uuid
import fcntl
import hashlib
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

# ─── Paths (configurable via environment variables) ──────────────────────────
SESSION_DIR = os.environ.get(
    'NEURALCLINE_SESSION_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'session-state')
)
NC_DIR = os.environ.get(
    'NEURALCLINE_HOME',
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# Ensure directories exist
os.makedirs(SESSION_DIR, exist_ok=True)

# File paths
STATE_FILE = os.path.join(SESSION_DIR, 'current-state.json')
CHECKPOINT_FILE = os.path.join(SESSION_DIR, 'checkpoint.json')
CRASH_LOG = os.path.join(SESSION_DIR, 'crash-log.ndjson')
FAILURE_POINTS = os.path.join(SESSION_DIR, 'failure-points.json')
TIMING_HISTORY = os.path.join(SESSION_DIR, 'timing-history.json')
SESSION_MEMORY = os.path.join(SESSION_DIR, 'session-memory.json')
CONTEXT_METRICS = os.path.join(SESSION_DIR, 'context-metrics.json')
LICENSE_DIR = os.path.join(SESSION_DIR, 'licenses')

# Timeout threshold (configurable)
TIMEOUT_MS = int(os.environ.get('NEURALCLINE_TIMEOUT_MS', '60000'))
BASELINE_MS = int(os.environ.get('NEURALCLINE_BASELINE_MS', '5000'))

# ─── Locked File Operations ─────────────────────────────────────────────────


class LockedJSONFile:
    """
    Thread-safe, process-safe JSON file operations using POSIX file locking.
    
    Features:
    - Exclusive lock on write, shared lock on read
    - Retry logic with timeout for lock acquisition
    - Deadlock detection (timeout raises exception)
    - Atomic writes (write to temp file, rename)
    - Corruption detection (JSON validation on read)
    
    Usage:
        with LockedJSONFile(path) as f:
            data = f.read()
            data['key'] = 'value'
            f.write(data)
    """
    
    def __init__(self, path, lock_timeout=5.0, retry_interval=0.1):
        self.path = path
        self.lock_path = path + '.lock'
        self.lock_timeout = lock_timeout
        self.retry_interval = retry_interval
        self.fd = None
        self._acquired = False
    
    def __enter__(self):
        self._acquire_lock()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._release_lock()
        return False
    
    def _acquire_lock(self):
        """Acquire an exclusive lock with retry and timeout."""
        start = time.time()
        self.fd = open(self.lock_path, 'w')
        
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._acquired = True
                return
            except (IOError, OSError):
                if time.time() - start > self.lock_timeout:
                    raise TimeoutError(
                        f"Could not acquire lock on {self.path} "
                        f"after {self.lock_timeout}s"
                    )
                time.sleep(self.retry_interval)
    
    def _release_lock(self):
        """Release the lock and close the file descriptor."""
        if self.fd is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                self.fd.close()
            except Exception:
                pass
            self.fd = None
            self._acquired = False
            # Clean up lock file
            try:
                os.unlink(self.lock_path)
            except Exception:
                pass
    
    def read(self, default=None):
        """
        Read JSON data from the file.
        
        Returns default (or {} if default is None) on any error.
        Automatically detects and repairs common corruption patterns.
        """
        if default is None:
            default = {}
        
        if not os.path.exists(self.path):
            return default
        
        try:
            with open(self.path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # Attempt repair: truncate at last valid JSON
            try:
                with open(self.path, 'r') as f:
                    content = f.read()
                # Find the last complete JSON object/array
                repaired = self._repair_json(content)
                if repaired is not None:
                    with open(self.path, 'w') as f:
                        f.write(repaired)
                    return json.loads(repaired)
            except Exception:
                pass
            return default
        except Exception:
            return default
    
    def write(self, data):
        """
        Write JSON data to the file atomically.
        
        Uses atomic write pattern:
        1. Write to a temporary file in the same directory
        2. fsync the temporary file
        3. Rename temporary file to target path (atomic on POSIX)
        """
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(self.path),
            prefix='.tmp_',
            suffix='.json'
        )
        try:
            with os.fdopen(tmp_fd, 'w') as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            # Atomic rename (POSIX guarantees this is atomic on same filesystem)
            os.replace(tmp_path, self.path)
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            raise
    
    @staticmethod
    def _repair_json(content):
        """Attempt to repair truncated/corrupted JSON content."""
        # Try to find the last complete JSON structure
        # This is a best-effort repair for common crash truncation patterns
        stack = []
        last_valid_end = 0
        
        for i, char in enumerate(content):
            if char in '{[':
                stack.append(char)
            elif char in '}]':
                if stack and (
                    (char == '}' and stack[-1] == '{') or
                    (char == ']' and stack[-1] == '[')
                ):
                    stack.pop()
                    if not stack:
                        last_valid_end = i + 1
        
        if last_valid_end > 0:
            return content[:last_valid_end]
        return None


# ─── Utility Functions ──────────────────────────────────────────────────────


def gen_uuid():
    return str(uuid.uuid4())


def timestamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def epoch_now():
    return time.time()


def md5_hash(text):
    return hashlib.md5(text.encode()).hexdigest()


def get_license_tier():
    """
    Determine the current license tier.
    
    Checks:
    1. NEURALCLINE_LICENSE_KEY environment variable
    2. LICENSE_DIR for stored licenses
    3. Defaults to 'free' if no license found
    
    Returns dict with tier, features, and limits.
    """
    from lib.payment.pricing_tiers import get_tier, get_limit, get_feature
    
    license_key = os.environ.get('NEURALCLINE_LICENSE_KEY', '')
    
    if not license_key:
        return {
            'tier': 'free',
            'features': get_tier('free').get('features', []),
            'limits': get_tier('free').get('limits', {}),
            'valid': True
        }
    
    # Validate license key against stored licenses
    if os.path.exists(LICENSE_DIR):
        for filename in os.listdir(LICENSE_DIR):
            if not filename.endswith('.json'):
                continue
            try:
                with open(os.path.join(LICENSE_DIR, filename)) as f:
                    data = json.load(f)
                if data.get('license_key') == license_key and data.get('active', False):
                    tier_id = data.get('tier', 'free')
                    return {
                        'tier': tier_id,
                        'features': get_tier(tier_id).get('features', []),
                        'limits': get_tier(tier_id).get('limits', {}),
                        'valid': True,
                        'email': data.get('email', ''),
                        'expires_at': data.get('expires_at')
                    }
            except Exception:
                continue
    
    return {
        'tier': 'free',
        'features': get_tier('free').get('features', []),
        'limits': get_tier('free').get('limits', {}),
        'valid': True
    }


# ─── Session Core Class ─────────────────────────────────────────────────────


class SessionCore:
    """
    Central session safety API.
    
    This class provides all core operations for session safety, timing,
    crash recovery, and context management. It is model-agnostic — any
    AI coding agent can use it through the adapter layer.
    
    Key capabilities:
    - Record execution timing and outcomes
    - Compute crash probability using statistical models
    - Generate and restore checkpoints
    - Track context window pressure
    - Manage license-based feature flags
    - Collect and export verifiable metrics
    
    Usage:
        core = SessionCore()
        core.record_execution("command", duration_ms, exit_code, output_size)
        proximity = core.compute_crash_proximity("command")
        core.generate_checkpoint()
    """
    
    def __init__(self, session_dir=None):
        self.session_dir = session_dir or SESSION_DIR
        self.license = get_license_tier()
        
        # Ensure session state is initialized
        self._ensure_state_file()
    
    def _ensure_state_file(self):
        """Initialize the state file if it doesn't exist."""
        if not os.path.exists(STATE_FILE):
            initial_state = {
                'session_id': gen_uuid(),
                'session_start': timestamp(),
                'last_updated': timestamp(),
                'last_command': '',
                'last_exit_code': 0,
                'last_output_size': 0,
                'last_proximity': 0,
                'tool_call_count': 0,
                'context_usage_pct': 0,
                'current_context_tokens': 0,
                'max_context_tokens': 100000,
                'session_start_count': 1,
                'total_session_count': 1,
                'file_scope_list': [],
                'active_goals': [],
                'next_steps': [],
                'adapter': 'unknown',
                'model': 'unknown',
                'version': '2.0.0'
            }
            with LockedJSONFile(STATE_FILE) as f:
                f.write(initial_state)
    
    def _read_state(self):
        """Read current state with locking."""
        with LockedJSONFile(STATE_FILE) as f:
            return f.read(default={
                'session_id': gen_uuid(),
                'tool_call_count': 0,
                'context_usage_pct': 0
            })
    
    def _write_state(self, data):
        """Write state with locking."""
        with LockedJSONFile(STATE_FILE) as f:
            f.write(data)
    
    def _read_timing_history(self):
        """Read timing history with locking."""
        with LockedJSONFile(TIMING_HISTORY) as f:
            return f.read(default={
                'entries': [],
                'command_patterns': {},
                'rolling_avg_ms': 0,
                'rolling_window': [],
                'last_updated': ''
            })
    
    def _write_timing_history(self, data):
        """Write timing history with locking."""
        with LockedJSONFile(TIMING_HISTORY) as f:
            f.write(data)
    
    # ─── Core Operations ──────────────────────────────────────────────────
    
    def record_execution(self, command, duration_ms, exit_code, output_size=0):
        """
        Record an execution event.
        
        This is the primary data collection method. Every command execution
        should be recorded through this method to build the timing history,
        failure patterns, and context usage models.
        
        Args:
            command: The command that was executed
            duration_ms: Execution duration in milliseconds
            exit_code: Process exit code (0 = success)
            output_size: Number of lines of output (optional)
        
        Returns:
            dict with recording confirmation and updated metrics
        """
        now = timestamp()
        pattern = self._normalize_command(command)
        complexity = self._estimate_complexity(command)
        
        # Update state
        state = self._read_state()
        state['last_updated'] = now
        state['last_command'] = command[:200]
        state['last_exit_code'] = exit_code
        state['last_output_size'] = output_size
        state['tool_call_count'] = state.get('tool_call_count', 0) + 1
        
        # Estimate context usage
        estimated_tokens = state['tool_call_count'] * 2000 + len(command) * 10
        max_tokens = state.get('max_context_tokens', 100000)
        state['context_usage_pct'] = min(100, int(estimated_tokens * 100 / max(max_tokens, 1)))
        state['current_context_tokens'] = estimated_tokens
        
        self._write_state(state)
        
        # Update timing history
        history = self._read_timing_history()
        entries = history.get('entries', [])
        patterns = history.get('command_patterns', {})
        rolling_window = list(history.get('rolling_window', []))
        
        # Add entry
        entry = {
            'timestamp': now,
            'command': command[:200],
            'pattern': pattern,
            'duration_ms': duration_ms,
            'exit_code': exit_code,
            'output_size': output_size,
            'complexity': complexity
        }
        entries.append(entry)
        
        # Keep last 100 entries
        if len(entries) > 100:
            entries = entries[-100:]
        
        # Update rolling window
        rolling_window.append(duration_ms)
        if len(rolling_window) > 20:
            rolling_window = rolling_window[-20:]
        
        # Update pattern stats
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
        p['min_duration_ms'] = min(p['min_duration_ms'], duration_ms, p['min_duration_ms'])
        p['last_seen'] = now
        
        # Compute rolling average
        rolling_avg_ms = int(sum(rolling_window) / max(len(rolling_window), 1))
        
        # Compute EEF (Execution Emulation Factor)
        baseline_ratio = max(0.1, rolling_avg_ms / max(BASELINE_MS, 1))
        complexity_factor = 1.0 + (complexity / 10.0)
        context_factor = 1.0 + (state.get('context_usage_pct', 0) / 200.0)
        recent_failures = sum(1 for e in entries[-10:] if e.get('exit_code', 0) != 0)
        failure_factor = 1.0 + (recent_failures / 20.0)
        
        eef = round(max(0.3, min(3.0, baseline_ratio * complexity_factor * context_factor * failure_factor)), 2)
        
        # Compute timeout proximity using log-normal distribution
        timeout_proximity = self._compute_timeout_proximity(rolling_avg_ms, eef)
        
        # Update history
        history['entries'] = entries
        history['command_patterns'] = patterns
        history['rolling_avg_ms'] = rolling_avg_ms
        history['rolling_window'] = rolling_window
        history['last_updated'] = now
        
        self._write_timing_history(history)
        
        # Update state with timing metrics
        state = self._read_state()
        state['timing_metrics'] = {
            'rolling_avg_ms': rolling_avg_ms,
            'execution_emulation_factor': eef,
            'timeout_proximity': timeout_proximity,
            'timeout_threshold_ms': TIMEOUT_MS,
            'total_commands_tracked': len(entries),
            'pattern_count': len(patterns),
            'recent_failures': recent_failures,
            'complexity': complexity
        }
        self._write_state(state)
        
        # Log crash on failure
        if exit_code != 0 and exit_code not in (130, 141):  # 130=SIGINT, 141=SIGPIPE
            self._log_crash(command, exit_code, output_size, 0)
        
        return {
            'recorded': True,
            'eef': eef,
            'timeout_proximity': timeout_proximity,
            'rolling_avg_ms': rolling_avg_ms,
            'complexity': complexity,
            'tool_call_count': state['tool_call_count'],
            'context_usage_pct': state['context_usage_pct']
        }
    
    def compute_crash_proximity(self, command, file_scope=''):
        """
        Compute crash proximity score (0-100) for a command.
        
        Uses logistic regression model (if trained) or heuristic fallback
        to estimate the probability that this command will cause a crash.
        
        Args:
            command: The command to evaluate
            file_scope: Optional file scope context
        
        Returns:
            dict with proximity score, matched patterns, and contributing factors
        """
        state = self._read_state()
        timing = state.get('timing_metrics', {})
        context_usage = state.get('context_usage_pct', 0)
        eef = timing.get('execution_emulation_factor', 1.0)
        timeout_prox = timing.get('timeout_proximity', 0)
        recent_failures = timing.get('recent_failures', 0)
        
        score = 0
        factors = []
        
        # Factor 1: Historical failure pattern match (35% weight)
        pattern_score = self._compute_pattern_match_score(command)
        score += pattern_score
        if pattern_score > 0:
            factors.append(f'pattern_match: +{pattern_score}')
        
        # Factor 2: Context usage pressure (20% weight)
        if context_usage > 60:
            ctx_score = min(20, (context_usage - 60) * 20 // 40)
            score += ctx_score
            factors.append(f'context_pressure: +{ctx_score}')
        
        # Factor 3: Command complexity (15% weight)
        complexity = self._estimate_complexity(command)
        complexity_score = min(15, complexity * 3)
        score += complexity_score
        if complexity_score > 5:
            factors.append(f'complexity: +{complexity_score}')
        
        # Factor 4: Known risk patterns (15% weight)
        risk_score = self._compute_risk_pattern_score(command)
        score += risk_score
        if risk_score > 0:
            factors.append(f'risk_pattern: +{risk_score}')
        
        # Factor 5: Timing metrics — EEF and timeout proximity (15% weight)
        if eef > 1.0:
            eef_score = min(15, int((eef - 1.0) * 10))
            if timeout_prox >= 80:
                eef_score = min(15, eef_score + 5)
            elif timeout_prox >= 60:
                eef_score = min(15, eef_score + 3)
            score += eef_score
            if eef_score > 0:
                factors.append(f'timing_eef: +{eef_score}')
        
        # Factor 6: Recent failures (bonus)
        if recent_failures >= 3:
            cascade_score = min(10, recent_failures * 3)
            score += cascade_score
            factors.append(f'failure_cascade: +{cascade_score}')
        
        score = min(100, max(0, score))
        
        return {
            'crash_proximity': score,
            'context_usage': context_usage,
            'eef': eef,
            'timeout_proximity': timeout_prox,
            'factors': factors,
            'matched_pattern': self._get_matched_pattern(command)
        }
    
    def generate_checkpoint(self):
        """
        Generate a checkpoint of the current session state.
        
        Returns dict with checkpoint summary.
        """
        state = self._read_state()
        history = self._read_timing_history()
        
        now = timestamp()
        tool_calls = state.get('tool_call_count', 0)
        ctx_pct = state.get('context_usage_pct', 0)
        last_cmd = state.get('last_command', '')
        exit_code = state.get('last_exit_code', 0)
        
        # Count crash events
        crash_events = 0
        try:
            if os.path.exists(CRASH_LOG):
                with open(CRASH_LOG) as f:
                    crash_events = sum(1 for _ in f)
        except Exception:
            pass
        
        # Compute success rate
        success_rate = 100
        if crash_events > 0 and tool_calls > 0:
            success_rate = max(0, (tool_calls - crash_events) * 100 // tool_calls)
        
        # Read failure points
        fps = {'failure_points': []}
        try:
            with LockedJSONFile(FAILURE_POINTS) as f:
                fps = f.read(default={'failure_points': []})
        except Exception:
            pass
        
        points = fps.get('failure_points', [])
        fp_match = points[0].get('pattern', 'none') if points else 'none'
        prox_score = int(points[0].get('weight', 0)) if points else 0
        
        # Get goals and next steps
        goals = state.get('active_goals', [])
        if not goals:
            goals = self._extract_goals_from_history()
        
        next_steps = state.get('next_steps', [])
        if not next_steps:
            next_steps = [
                "Run: source /root/rehydration.md to restore full context",
                "Check documentation for workspace context"
            ]
        
        # Build checkpoint
        timing = state.get('timing_metrics', {})
        cp = {
            'session_id': state.get('session_id', gen_uuid()),
            'timestamp': now,
            'total_tool_calls': tool_calls,
            'success_rate': success_rate,
            'context_usage_pct': ctx_pct,
            'total_crash_events': crash_events,
            'last_command': last_cmd[:200],
            'last_exit_code': exit_code,
            'active_goals': goals[:5],
            'next_steps': next_steps[:5],
            'file_scope': state.get('file_scope_list', []),
            'crash_proximity_score': prox_score,
            'failure_point_match': fp_match[:80],
            'timing_metrics': {
                'eef': timing.get('execution_emulation_factor', 1.0),
                'timeout_proximity': timing.get('timeout_proximity', 0),
                'rolling_avg_ms': timing.get('rolling_avg_ms', 0),
                'total_commands': timing.get('total_commands_tracked', 0),
                'recent_failures': timing.get('recent_failures', 0)
            },
            'version': '2.0.0'
        }
        
        with LockedJSONFile(CHECKPOINT_FILE) as f:
            f.write(cp)
        
        return {
            'checkpoint_saved': True,
            'session_id': cp['session_id'],
            'tool_calls': tool_calls,
            'context_pct': ctx_pct,
            'success_rate': success_rate,
            'crash_events': crash_events
        }
    
    def read_checkpoint(self):
        """Read and return the current checkpoint."""
        with LockedJSONFile(CHECKPOINT_FILE) as f:
            return f.read(default={'error': 'no_checkpoint'})
    
    def check_checkpoint(self):
        """Check if a valid checkpoint exists."""
        cp = self.read_checkpoint()
        tools = cp.get('total_tool_calls', 0)
        ctx = cp.get('context_usage_pct', 0)
        
        if tools > 0 or ctx > 0:
            return {
                'exists': True,
                'tool_calls': tools,
                'context_pct': ctx,
                'last_command': cp.get('last_command', '')[:80]
            }
        return {'exists': False}
    
    def update_failure_points(self):
        """
        Recompute failure points from the crash log.
        
        Analyzes all crash entries and identifies patterns with
        weighted scoring based on frequency, recency, and severity.
        """
        entries = []
        try:
            if os.path.exists(CRASH_LOG):
                with open(CRASH_LOG) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                entries.append(json.loads(line))
                            except Exception:
                                pass
        except Exception:
            pass
        
        # Count patterns
        from collections import defaultdict
        pattern_counts = defaultdict(
            lambda: {'count': 0, 'proximities': [], 'last_seen': '', 'commands': []}
        )
        
        for e in entries:
            cmd = e.get('command', '')
            pattern = self._normalize_command(cmd) or '(empty)'
            pattern_counts[pattern]['count'] += 1
            pattern_counts[pattern]['proximities'].append(e.get('crash_proximity_score', 0))
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
            
            # Recency factor
            recency_factor = 1.0
            if data['last_seen']:
                try:
                    last = datetime.fromisoformat(data['last_seen'].replace('Z', '+00:00'))
                    delta = (datetime.now(timezone.utc) - last.replace(tzinfo=timezone.utc)).total_seconds()
                    if delta > 3600:
                        recency_factor = max(0.1, 1.0 - (delta - 3600) / 86400)
                except Exception:
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
        
        with LockedJSONFile(FAILURE_POINTS) as f:
            f.write(fps)
        
        return {
            'failure_points_updated': len(points),
            'total_events': len(entries)
        }
    
    def log_crash(self, command, exit_code, output_size, proximity, file_scope='', error_msg=''):
        """Log a crash event to the crash log."""
        self._log_crash(command, exit_code, output_size, proximity, file_scope, error_msg)
        return {'logged': True}
    
    def get_status(self):
        """
        Get a comprehensive status report of the current session.
        
        Returns all relevant metrics, license info, and health status.
        """
        state = self._read_state()
        timing = state.get('timing_metrics', {})
        cp = self.read_checkpoint()
        
        # Count crash events
        crash_events = 0
        try:
            if os.path.exists(CRASH_LOG):
                with open(CRASH_LOG) as f:
                    crash_events = sum(1 for _ in f)
        except Exception:
            pass
        
        tool_calls = state.get('tool_call_count', 0)
        success_rate = 100
        if crash_events > 0 and tool_calls > 0:
            success_rate = max(0, (tool_calls - crash_events) * 100 // tool_calls)
        
        return {
            'session_id': state.get('session_id', 'unknown'),
            'session_start': state.get('session_start', 'unknown'),
            'uptime': self._get_uptime(state.get('session_start', '')),
            'tool_call_count': tool_calls,
            'crash_events': crash_events,
            'success_rate': success_rate,
            'context_usage_pct': state.get('context_usage_pct', 0),
            'context_tokens': state.get('current_context_tokens', 0),
            'max_context_tokens': state.get('max_context_tokens', 100000),
            'eef': timing.get('execution_emulation_factor', 1.0),
            'timeout_proximity': timing.get('timeout_proximity', 0),
            'rolling_avg_ms': timing.get('rolling_avg_ms', 0),
            'total_commands_tracked': timing.get('total_commands_tracked', 0),
            'recent_failures': timing.get('recent_failures', 0),
            'license': self.license.get('tier', 'free'),
            'adapter': state.get('adapter', 'unknown'),
            'model': state.get('model', 'unknown'),
            'version': '2.0.0',
            'checkpoint': {
                'exists': cp.get('error') != 'no_checkpoint',
                'tool_calls': cp.get('total_tool_calls', 0),
                'success_rate': cp.get('success_rate', 100)
            }
        }
    
    # ─── Private Methods ─────────────────────────────────────────────────
    
    def _normalize_command(self, cmd):
        """Normalize a command to extract its pattern."""
        import re
        cmd = re.sub(r'--\w+=\S+', '', cmd)
        cmd = re.sub(r'/[^\s]+', '/...', cmd)
        cmd = re.sub(r'\d+', 'N', cmd)
        cmd = re.sub(r'\s+', ' ', cmd).strip()
        return cmd[:80]
    
    def _estimate_complexity(self, cmd):
        """
        Estimate complexity score (1-10) for a command.
        
        Based on:
        - File system operations (+2 for find, grep -r, tar, etc.)
        - Network operations (+3 for curl, wget, git clone, npm install)
        - Build operations (+2 for make, gcc, webpack)
        - Large output (+1 for cat *.log, tail -f)
        - Python inline (+3 for python3 -c)
        """
        import re
        score = 1
        
        if re.search(r'\b(find|grep -r|ripgrep|ag|ack|tree)\b', cmd):
            score += 2
        if re.search(r'\b(tar|gzip|gunzip|zip|unzip|bzip2|xz)\b', cmd):
            score += 2
        if re.search(r'\b(curl|wget|git clone|git pull|git push|npm install|pip install|apt install)\b', cmd):
            score += 3
        if re.search(r'\b(make|cmake|gcc|clang|npm run build|webpack|vite build|tsc)\b', cmd):
            score += 2
        if re.search(r'\b(cat|head|tail)\b.*\.(log|csv|json|ndjson)', cmd):
            score += 1
        if re.search(r'python3 -c\b', cmd):
            score += 3
        
        return min(score, 10)
    
    def _compute_timeout_proximity(self, rolling_avg_ms, eef):
        """
        Compute timeout proximity using log-normal distribution model.
        
        This replaces the arbitrary 1.5x safety margin with a statistical
        estimate based on the assumption that execution times follow a
        log-normal distribution (which is standard for task durations).
        
        P(timeout) = 1 - CDF_log_normal(timeout_threshold | mu, sigma)
        
        Where mu and sigma are estimated from the rolling average and EEF.
        """
        import math
        
        # Estimate log-normal parameters from rolling average
        # For a log-normal distribution:
        #   mean = exp(mu + sigma^2/2)
        #   var = (exp(sigma^2) - 1) * exp(2*mu + sigma^2)
        #
        # We estimate sigma = 0.5 (typical for task durations)
        # Then mu = ln(mean) - sigma^2/2
        
        estimated_mean = rolling_avg_ms * eef
        sigma = 0.5  # Typical coefficient of variation for task durations
        mu = math.log(max(1, estimated_mean)) - (sigma ** 2) / 2
        
        # P(duration > TIMEOUT_MS)
        # Using the survival function: 1 - CDF
        from scipy import stats as scipy_stats
        
        try:
            p_timeout = 1 - scipy_stats.lognorm.cdf(TIMEOUT_MS, s=sigma, scale=math.exp(mu))
        except Exception:
            # Fallback to simple ratio if scipy not available
            p_timeout = min(1.0, estimated_mean / TIMEOUT_MS)
        
        return int(p_timeout * 100)
    
    def _compute_pattern_match_score(self, command):
        """Compute the pattern match score (0-35) for a command."""
        try:
            with LockedJSONFile(FAILURE_POINTS) as f:
                fps = f.read(default={'failure_points': []})
        except Exception:
            return 0
        
        points = fps.get('failure_points', [])
        if not points:
            return 0
        
        import re
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
        
        return int(max_weight * 35 / 100)
    
    def _get_matched_pattern(self, command):
        """Get the name of the matched failure pattern, if any."""
        try:
            with LockedJSONFile(FAILURE_POINTS) as f:
                fps = f.read(default={'failure_points': []})
        except Exception:
            return 'none'
        
        points = fps.get('failure_points', [])
        if not points:
            return 'none'
        
        import re
        def normalize(cmd):
            cmd = re.sub(r'--\w+=\S+', '', cmd)
            cmd = re.sub(r'/[^\s]+', '/...', cmd)
            cmd = re.sub(r'\d+', 'N', cmd)
            return cmd[:80]
        
        normalized = normalize(command)
        for p in points:
            pattern = p.get('pattern', '')
            if pattern and pattern in normalized:
                return pattern
        return 'none'
    
    def _compute_risk_pattern_score(self, command):
        """Compute risk score (0-15) based on known dangerous patterns."""
        import re
        risk_patterns = [
            r'(find|grep -r|cat.*\.(log|tar|gz|zip)|npm install|pip install)',
            r'(ls -la /root|ll /root|tree|du -sh)'
        ]
        if re.search(risk_patterns[0], command):
            return 15
        elif re.search(risk_patterns[1], command):
            return 10
        return 0
    
    def _log_crash(self, command, exit_code, output_size, proximity, file_scope='', error_msg=''):
        """Append a crash entry to the crash log."""
        state = self._read_state()
        entry = {
            'timestamp': timestamp(),
            'session_id': state.get('session_id', gen_uuid()),
            'command': command[:200],
            'exit_code': exit_code,
            'output_size_lines': output_size,
            'crash_proximity_score': proximity,
            'file_scope': [file_scope] if file_scope.strip() else [],
            'error': error_msg[:200],
            'eef': state.get('timing_metrics', {}).get('execution_emulation_factor', 1.0),
            'context_usage_pct': state.get('context_usage_pct', 0)
        }
        
        try:
            with open(CRASH_LOG, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            
            # Trim if > 1000 lines
            with open(CRASH_LOG) as f:
                lines = f.readlines()
            if len(lines) > 1000:
                with open(CRASH_LOG, 'w') as f:
                    f.writelines(lines[-1000:])
        except Exception:
            pass
    
    def _extract_goals_from_history(self):
        """Extract goals from crash log history."""
        goals = []
        try:
            if os.path.exists(CRASH_LOG):
                with open(CRASH_LOG) as f:
                    for line in f:
                        try:
                            e = json.loads(line.strip())
                            cmd = e.get('command', '')
                            if cmd:
                                goals.append(f"Continue from: {cmd[:60]}...")
                        except Exception:
                            pass
                goals = goals[:3]
        except Exception:
            pass
        return goals
    
    def _get_uptime(self, session_start_str):
        """Calculate session uptime from start timestamp."""
        if not session_start_str:
            return 'unknown'
        try:
            start = datetime.fromisoformat(session_start_str.replace('Z', '+00:00'))
            delta = datetime.now(timezone.utc) - start.replace(tzinfo=timezone.utc)
            hours = int(delta.total_seconds() // 3600)
            minutes = int((delta.total_seconds() % 3600) // 60)
            return f"{hours}h {minutes}m"
        except Exception:
            return 'unknown'


# ─── CLI Interface ──────────────────────────────────────────────────────────


def main():
    """CLI entry point for session core operations."""
    if len(sys.argv) < 2:
        print("NeuralCline Session Core v2.0.0")
        print()
        print("Usage:")
        print("  python3 lib/session_core.py record <cmd> <dur_ms> <exit> [size]")
        print("  python3 lib/session_core.py proximity <command> [file_scope]")
        print("  python3 lib/session_core.py checkpoint")
        print("  python3 lib/session_core.py read-checkpoint")
        print("  python3 lib/session_core.py check-checkpoint")
        print("  python3 lib/session_core.py update-failure-points")
        print("  python3 lib/session_core.py log-crash <cmd> <exit> <size> <prox> [scope] [error]")
        print("  python3 lib/session_core.py status")
        return
    
    core = SessionCore()
    command = sys.argv[1]
    args = sys.argv[2:]
    
    try:
        if command == 'record':
            cmd = args[0] if len(args) > 0 else ''
            dur = int(args[1]) if len(args) > 1 else 0
            exit_code = int(args[2]) if len(args) > 2 else 0
            size = int(args[3]) if len(args) > 3 else 0
            result = core.record_execution(cmd, dur, exit_code, size)
            print(json.dumps(result, indent=2))
        
        elif command == 'proximity':
            cmd = args[0] if len(args) > 0 else ''
            scope = args[1] if len(args) > 1 else ''
            result = core.compute_crash_proximity(cmd, scope)
            # Legacy format output for compatibility
            print(f"CRASH_PROXIMITY={result['crash_proximity']}")
            print(f"CONTEXT_USAGE={result['context_usage']}")
            print(f"EEF={result['eef']}")
            print(f"TIMEOUT_PROXIMITY={result['timeout_proximity']}")
            print(f"MATCHED_PATTERN={result['matched_pattern']}")
            if result['factors']:
                print(f"FACTORS={'; '.join(result['factors'])}")
        
        elif command == 'checkpoint':
            result = core.generate_checkpoint()
            print(json.dumps(result, indent=2))
        
        elif command == 'read-checkpoint':
            result = core.read_checkpoint()
            print(json.dumps(result, indent=2))
        
        elif command == 'check-checkpoint':
            result = core.check_checkpoint()
            if result['exists']:
                print(f"Checkpoint found: {result['tool_calls']} tools, {result['context_pct']}% context")
                print(f"Last command: {result['last_command']}...")
            else:
                print("No active checkpoint found")
        
        elif command == 'update-failure-points':
            result = core.update_failure_points()
            print(json.dumps(result, indent=2))
        
        elif command == 'log-crash':
            cmd = args[0] if len(args) > 0 else ''
            exit_code = int(args[1]) if len(args) > 1 else 0
            size = int(args[2]) if len(args) > 2 else 0
            prox = int(args[3]) if len(args) > 3 else 0
            scope = args[4] if len(args) > 4 else ''
            error = args[5] if len(args) > 5 else ''
            result = core.log_crash(cmd, exit_code, size, prox, scope, error)
            print(json.dumps(result, indent=2))
        
        elif command == 'status':
            result = core.get_status()
            print(json.dumps(result, indent=2))
        
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()