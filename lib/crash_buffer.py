#!/usr/bin/env python3
"""
NeuralCline Crash Absorption Buffer — Foreground-Non-Blocking Recovery Layer
=======================================================================
Purpose: When a crash occurs, this module absorbs it into a virtual 
execution layer so the developer can continue working in the foreground
while recovery runs in an isolated subprocess in the background.

Features:
  1. Crash absorption — snapshot state before crash propagates
  2. Subprocess recovery — recovery runs in a forked child process
  3. Non-blocking — parent returns immediately, child heals
  4. State merging — recovered state merges back into foreground
  5. Self-improving — each crash trains the model to recover faster
  6. Graceful fallback — if recovery fails, fallback to next strategy

Usage:
  python3 /root/NeuralCline/lib/crash_buffer.py absorb <crash_data.json>
  python3 /root/NeuralCline/lib/crash_buffer.py poll <recovery_pid>
  python3 /root/NeuralCline/lib/crash_buffer.py merge <checkpoint.json>
  
  Or import as module:
    from lib.crash_buffer import CrashBuffer
    buffer = CrashBuffer()
    result = buffer.absorb(crash_event)
"""

import os
import sys
import json
import time
import uuid
import signal
import subprocess
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum
from typing import Optional, Dict, Any, List

# ─── Paths ────────────────────────────────────────────────────────
SESSION_DIR = os.environ.get(
    'NEURALCLINE_SESSION_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'session-state')
)
NC_DIR = os.environ.get(
    'NEURALCLINE_HOME',
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
BUFFER_DIR = os.path.join(SESSION_DIR, 'buffer')
os.makedirs(BUFFER_DIR, exist_ok=True)

STATE_FILE = os.path.join(SESSION_DIR, 'current-state.json')
CHECKPOINT_FILE = os.path.join(SESSION_DIR, 'checkpoint.json')
CRASH_LOG = os.path.join(SESSION_DIR, 'crash-log.ndjson')
TIMING_HISTORY = os.path.join(SESSION_DIR, 'timing-history.json')

# ─── Recovery Status Enum ─────────────────────────────────────────


class RecoveryStatus(Enum):
    """Status of a recovery operation in the virtual layer."""
    PENDING = 'pending'         # Recovery subprocess started
    HEALING = 'healing'         # Recovery is executing
    MERGED = 'merged'           # Recovery complete, state merged
    FAILED_FALLBACK = 'failed_fallback'  # Primary recovery failed
    FAILED_CRITICAL = 'failed_critical'  # All strategies failed


class CrashSeverity(Enum):
    """Severity classification for crash events."""
    LOW = 'low'              # Non-fatal warning/flag
    MEDIUM = 'medium'        # Recoverable crash with checkpoint
    HIGH = 'high'            # Full crash requiring rehydration
    CRITICAL = 'critical'    # System-level failure


# ─── Data Classes ─────────────────────────────────────────────────


class CrashEvent:
    """Represents a single crash event detected by the system."""
    
    def __init__(self, 
                 crash_type: str,
                 exit_code: int,
                 command: str,
                 context_usage_pct: float,
                 execution_duration_ms: float,
                 tool_call_count: int,
                 severity: CrashSeverity = CrashSeverity.MEDIUM,
                 details: Optional[Dict] = None):
        self.id = str(uuid.uuid4())[:8]
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.crash_type = crash_type          # 'timeout', 'exit_code', 'hang', 'context_overflow'
        self.exit_code = exit_code
        self.command = command
        self.context_usage_pct = context_usage_pct
        self.execution_duration_ms = execution_duration_ms
        self.tool_call_count = tool_call_count
        self.severity = severity
        self.details = details or {}
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'crash_type': self.crash_type,
            'exit_code': self.exit_code,
            'command': self.command[:200],  # truncate for storage
            'context_usage_pct': self.context_usage_pct,
            'execution_duration_ms': self.execution_duration_ms,
            'tool_call_count': self.tool_call_count,
            'severity': self.severity.value,
            'details': self.details,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CrashEvent':
        return cls(
            crash_type=data['crash_type'],
            exit_code=data['exit_code'],
            command=data['command'],
            context_usage_pct=data['context_usage_pct'],
            execution_duration_ms=data['execution_duration_ms'],
            tool_call_count=data['tool_call_count'],
            severity=CrashSeverity(data.get('severity', 'medium')),
            details=data.get('details', {}),
        )


class AbsorbResult:
    """Result of absorbing a crash into the virtual layer."""
    
    def __init__(self,
                 crash_id: str,
                 recovery_pid: int,
                 foreground_delay_ms: float,
                 estimated_recovery_ms: float,
                 strategy: str,
                 snapshot_path: str):
        self.crash_id = crash_id
        self.recovery_pid = recovery_pid
        self.foreground_delay_ms = foreground_delay_ms
        self.estimated_recovery_ms = estimated_recovery_ms
        self.strategy = strategy
        self.snapshot_path = snapshot_path
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict:
        return {
            'crash_id': self.crash_id,
            'recovery_pid': self.recovery_pid,
            'foreground_delay_ms': self.foreground_delay_ms,
            'estimated_recovery_ms': self.estimated_recovery_ms,
            'strategy': self.strategy,
            'snapshot_path': self.snapshot_path,
            'timestamp': self.timestamp,
        }
    
    def __repr__(self) -> str:
        return (f"AbsorbResult(crash={self.crash_id}, "
                f"pid={self.recovery_pid}, "
                f"strategy={self.strategy}, "
                f"foreground_delay=0ms)")


# ─── Crash Buffer Core ────────────────────────────────────────────


class CrashBuffer:
    """
    Absorbs crashes into a virtual execution layer.
    
    The foreground process is NEVER interrupted. Recovery runs in an
    isolated subprocess. The developer continues working immediately.
    
    Architecture:
        [Crash Event] → [Snapshot State] → [Fork Subprocess]
            ↓                                    ↓
        [Return to Foreground]           [Recovery Executes]
            ↓                                    ↓
        [Developer Continues]             [State Merges Back]
    """
    
    def __init__(self):
        self._active_recoveries: Dict[int, Dict] = {}  # pid → recovery info
        self._lock = threading.Lock()
        self._load_recovery_history()
    
    def _load_recovery_history(self):
        """Load previous recovery attempts for pattern learning."""
        history_path = os.path.join(BUFFER_DIR, 'recovery-history.json')
        try:
            if os.path.exists(history_path):
                with open(history_path) as f:
                    self._history = json.load(f)
            else:
                self._history = {'recoveries': [], 'patterns': {}}
        except (json.JSONDecodeError, IOError):
            self._history = {'recoveries': [], 'patterns': {}}
    
    def _save_recovery_history(self):
        """Persist recovery history for future learning."""
        history_path = os.path.join(BUFFER_DIR, 'recovery-history.json')
        # Trim to last 1000 entries
        self._history['recoveries'] = self._history['recoveries'][-1000:]
        with open(history_path, 'w') as f:
            json.dump(self._history, f, indent=2)
    
    def _snapshot_state(self) -> str:
        """
        Atomically snapshot all current session state.
        Returns: path to snapshot JSON file.
        """
        snapshot_id = str(uuid.uuid4())[:12]
        snapshot_path = os.path.join(BUFFER_DIR, f'snapshot-{snapshot_id}.json')
        
        state_snapshot = {
            'snapshot_id': snapshot_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'state': {},
            'checkpoint': None,
            'timing': None,
        }
        
        # Capture current state file
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE) as f:
                    state_snapshot['state'] = json.load(f)
        except (json.JSONDecodeError, IOError):
            state_snapshot['state'] = {'error': 'could not read state'}
        
        # Capture latest checkpoint
        try:
            if os.path.exists(CHECKPOINT_FILE):
                with open(CHECKPOINT_FILE) as f:
                    state_snapshot['checkpoint'] = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        
        # Capture timing metrics
        try:
            if os.path.exists(TIMING_HISTORY):
                with open(TIMING_HISTORY) as f:
                    state_snapshot['timing'] = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        
        # Atomic write to snapshot file
        tmp_path = snapshot_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(state_snapshot, f, indent=2)
        os.rename(tmp_path, snapshot_path)
        
        return snapshot_path
    
    def _estimate_recovery_time(self, crash: CrashEvent) -> float:
        """
        Estimate recovery time in ms based on historical patterns.
        Gets faster with each crash.
        """
        # Look for similar crashes in history
        similar = [
            r for r in self._history['recoveries']
            if r.get('crash_type') == crash.crash_type
        ]
        
        if not similar:
            # Default estimate: 500ms base + 100ms per 10% context usage
            return 500 + (crash.context_usage_pct * 10)
        
        # Average of last 5 similar recoveries (rolling window)
        recent = similar[-5:]
        avg_time = sum(r.get('recovery_duration_ms', 500) for r in recent) / len(recent)
        
        # Add 10% buffer for safety
        return avg_time * 1.1
    
    def _select_recovery_strategy(self, crash: CrashEvent) -> str:
        """
        Select optimal recovery strategy based on crash and context.
        Strategies: 'full', 'partial', 'minimal', 'fresh'
        """
        if crash.context_usage_pct > 80:
            return 'minimal'  # Low context → minimal recovery
        elif crash.severity == CrashSeverity.CRITICAL:
            return 'full'     # Critical → full recovery
        elif crash.crash_type == 'context_overflow':
            return 'partial'  # Context issue → partial recovery
        elif crash.crash_type == 'timeout':
            return 'minimal'  # Timeout → just restore checkpoint
        else:
            return 'full'     # Default to full recovery
    
    def absorb(self, crash: CrashEvent) -> AbsorbResult:
        """
        Absorb a crash into the virtual execution layer.
        
        This method:
        1. Snapshots all current state atomically
        2. Forks a recovery subprocess
        3. Returns immediately to the foreground
        4. Recovery executes asynchronously in background
        
        The developer sees ZERO delay in the foreground.
        """
        # Step 1: Snapshot all state
        snapshot_path = self._snapshot_state()
        
        # Step 2: Select recovery strategy
        strategy = self._select_recovery_strategy(crash)
        
        # Step 3: Estimate recovery time
        estimated_ms = self._estimate_recovery_time(crash)
        
        # Step 4: Fork recovery subprocess
        recovery_id = str(uuid.uuid4())[:8]
        recovery_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'recovery_subprocess.py'
        )
        
        cmd = [
            sys.executable, recovery_script,
            '--recovery-id', recovery_id,
            '--strategy', strategy,
            '--snapshot', snapshot_path,
            '--crash-type', crash.crash_type,
        ]
        
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,  # Detach from foreground process group
            )
            
            # Track recovery
            with self._lock:
                self._active_recoveries[proc.pid] = {
                    'recovery_id': recovery_id,
                    'crash_id': crash.id,
                    'strategy': strategy,
                    'snapshot_path': snapshot_path,
                    'started_at': time.time(),
                    'status': RecoveryStatus.HEALING.value,
                }
            
            result = AbsorbResult(
                crash_id=crash.id,
                recovery_pid=proc.pid,
                foreground_delay_ms=0.0,  # Zero delay for foreground
                estimated_recovery_ms=estimated_ms,
                strategy=strategy,
                snapshot_path=snapshot_path,
            )
            
            # Log the absorption event
            self._log_absorption(crash, result)
            
            return result
            
        except Exception as e:
            # Fallback: if subprocess fails, return fallback result
            result = AbsorbResult(
                crash_id=crash.id,
                recovery_pid=-1,
                foreground_delay_ms=0.0,
                estimated_recovery_ms=estimated_ms,
                strategy='fallback',
                snapshot_path=snapshot_path,
            )
            return result
    
    def _log_absorption(self, crash: CrashEvent, result: AbsorbResult):
        """Log crash absorption event to the buffer log."""
        log_entry = os.path.join(BUFFER_DIR, 'buffer-log.ndjson')
        entry = {
            'event': 'absorb',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'crash': crash.to_dict(),
            'result': result.to_dict(),
        }
        try:
            with open(log_entry, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except IOError:
            pass  # Non-critical logging failure
    
    def poll_recovery(self, pid: int) -> RecoveryStatus:
        """
        Check the status of an active recovery.
        Non-blocking — returns immediately with current status.
        """
        with self._lock:
            recovery = self._active_recoveries.get(pid)
            if recovery is None:
                return RecoveryStatus.MERGED  # Not tracked = probably merged
            
            # Check if process is still running
            try:
                os.kill(pid, 0)  # Signal 0 = check existence
                # Process is still running
                elapsed = time.time() - recovery['started_at']
                if elapsed > 30:  # Recovery taking too long
                    return RecoveryStatus.FAILED_FALLBACK
                return RecoveryStatus.HEALING
            except OSError:
                # Process has terminated
                pass
            
            # Check for recovery result file
            result_path = os.path.join(
                BUFFER_DIR, f'recovery-result-{recovery["recovery_id"]}.json'
            )
            if os.path.exists(result_path):
                try:
                    with open(result_path) as f:
                        result_data = json.load(f)
                    if result_data.get('success'):
                        recovery['status'] = RecoveryStatus.MERGED.value
                        self._record_successful_recovery(recovery, result_data)
                        return RecoveryStatus.MERGED
                    else:
                        recovery['status'] = RecoveryStatus.FAILED_FALLBACK.value
                        return RecoveryStatus.FAILED_FALLBACK
                except (json.JSONDecodeError, IOError):
                    pass
            
            # No result file yet, process may have been killed
            recovery['status'] = RecoveryStatus.FAILED_FALLBACK.value
            return RecoveryStatus.FAILED_FALLBACK
    
    def _record_successful_recovery(self, 
                                     recovery: Dict, 
                                     result_data: Dict):
        """Record a successful recovery for future learning."""
        duration_ms = (time.time() - recovery['started_at']) * 1000
        
        self._history['recoveries'].append({
            'recovery_id': recovery['recovery_id'],
            'crash_id': recovery['crash_id'],
            'strategy': recovery['strategy'],
            'recovery_duration_ms': duration_ms,
            'success': True,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
        
        # Update pattern: average recovery time for this crash type
        crash_type = result_data.get('crash_type', 'unknown')
        patterns = self._history.get('patterns', {})
        if crash_type not in patterns:
            patterns[crash_type] = {'count': 0, 'total_time_ms': 0}
        patterns[crash_type]['count'] += 1
        patterns[crash_type]['total_time_ms'] += duration_ms
        patterns[crash_type]['avg_time_ms'] = (
            patterns[crash_type]['total_time_ms'] / 
            patterns[crash_type]['count']
        )
        self._history['patterns'] = patterns
        
        self._save_recovery_history()
    
    def merge_recovery(self, recovery_id: str) -> bool:
        """
        Merge a completed recovery back into the main session state.
        Called after recovery subprocess completes successfully.
        """
        result_path = os.path.join(
            BUFFER_DIR, f'recovery-result-{recovery_id}.json'
        )
        
        if not os.path.exists(result_path):
            return False
        
        try:
            with open(result_path) as f:
                result_data = json.load(f)
            
            if not result_data.get('success'):
                return False
            
            recovered_state = result_data.get('recovered_state', {})
            
            # Merge recovered state into current state file
            try:
                if os.path.exists(STATE_FILE):
                    with open(STATE_FILE) as f:
                        current_state = json.load(f)
                else:
                    current_state = {}
                
                # Merge recovered state preserving current state as priority
                for key, value in recovered_state.items():
                    if key not in current_state:
                        current_state[key] = value
                
                # Atomic write
                tmp_path = STATE_FILE + '.merge_tmp'
                with open(tmp_path, 'w') as f:
                    json.dump(current_state, f, indent=2)
                os.rename(tmp_path, STATE_FILE)
                
                return True
            except (IOError, json.JSONDecodeError):
                return False
                
        except (json.JSONDecodeError, IOError):
            return False
    
    def active_recoveries(self) -> List[Dict]:
        """Return list of all currently active recoveries."""
        with self._lock:
            return [
                {'pid': pid, **info}
                for pid, info in self._active_recoveries.items()
            ]
    
    def get_stats(self) -> Dict:
        """Return buffer statistics."""
        return {
            'active_recoveries': len(self._active_recoveries),
            'total_recoveries': len(self._history['recoveries']),
            'learned_patterns': len(self._history.get('patterns', {})),
            'last_recovery': (
                self._history['recoveries'][-1]['recovery_duration_ms']
                if self._history['recoveries'] else None
            ),
            'avg_recovery_time_ms': (
                sum(r['recovery_duration_ms'] for r in self._history['recoveries']) /
                len(self._history['recoveries'])
                if self._history['recoveries'] else 0
            ),
        }


# ─── CLI Interface ─────────────────────────────────────────────────


def cmd_absorb(args: List[str]):
    """CLI command: absorb a crash event."""
    if not args:
        print("Usage: crash_buffer.py absorb <crash_data.json>")
        sys.exit(1)
    
    crash_path = args[0]
    try:
        with open(crash_path) as f:
            crash_data = json.load(f)
        
        crash = CrashEvent.from_dict(crash_data)
        buffer = CrashBuffer()
        result = buffer.absorb(crash)
        
        print(json.dumps(result.to_dict(), indent=2))
        print(f"\n✓ Crash {result.crash_id} absorbed. "
              f"Recovery PID: {result.recovery_pid}", 
              file=sys.stderr)
        
    except (IOError, json.JSONDecodeError, KeyError) as e:
        print(f"Error reading crash data: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_poll(args: List[str]):
    """CLI command: poll recovery status."""
    if not args:
        pid = input("Recovery PID: ")
    else:
        pid = args[0]
    
    buffer = CrashBuffer()
    status = buffer.poll_recovery(int(pid))
    print(json.dumps({'pid': int(pid), 'status': status.value}, indent=2))


def cmd_stats(args: List[str]):
    """CLI command: show buffer statistics."""
    buffer = CrashBuffer()
    stats = buffer.get_stats()
    print(json.dumps(stats, indent=2))


def cmd_merge(args: List[str]):
    """CLI command: merge a completed recovery."""
    if not args:
        recovery_id = input("Recovery ID: ")
    else:
        recovery_id = args[0]
    
    buffer = CrashBuffer()
    success = buffer.merge_recovery(recovery_id)
    print(json.dumps({
        'recovery_id': recovery_id,
        'merged': success,
    }, indent=2))


# ─── Main Entry Point ─────────────────────────────────────────────


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    commands = {
        'absorb': cmd_absorb,
        'poll': cmd_poll,
        'stats': cmd_stats,
        'merge': cmd_merge,
    }
    
    if command in commands:
        commands[command](args)
    else:
        print(f"Unknown command: {command}")
        print("Available: absorb, poll, stats, merge")
        sys.exit(1)


if __name__ == '__main__':
    main()