#!/usr/bin/env python3
"""
NeuralCline Recovery Subprocess — Executes in Isolated Background Process
=======================================================================
Purpose: This script is called as a subprocess by crash_buffer.py.
It executes the actual recovery strategy in an isolated process so the
foreground developer experience is never interrupted.

Usage (called internally, not directly by users):
  python3 recovery_subprocess.py --recovery-id <id> --strategy <strategy> --snapshot <path>

Exit codes:
  0 — Recovery successful, result written
  1 — Recovery failed, fallback suggested
  2 — Critical failure, manual intervention required
"""

import os
import sys
import json
import time
import argparse
import traceback
from datetime import datetime, timezone

SESSION_DIR = os.environ.get(
    'NEURALCLINE_SESSION_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'session-state')
)
BUFFER_DIR = os.path.join(SESSION_DIR, 'buffer')
os.makedirs(BUFFER_DIR, exist_ok=True)


def write_result(recovery_id: str, success: bool, data: dict):
    """Write recovery result to file for parent process to read."""
    result_path = os.path.join(BUFFER_DIR, f'recovery-result-{recovery_id}.json')
    data.update({
        'success': success,
        'recovery_id': recovery_id,
        'completed_at': datetime.now(timezone.utc).isoformat(),
    })
    tmp_path = result_path + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(data, f, indent=2)
    os.rename(tmp_path, result_path)


def recovery_full(snapshot: dict) -> dict:
    """Full recovery: restore complete session state from snapshot."""
    recovered = {
        'state': snapshot.get('state', {}),
        'checkpoint': snapshot.get('checkpoint', {}),
        'timing': snapshot.get('timing', {}),
        'recovery_type': 'full',
    }
    # Rewrite state files
    if snapshot.get('state'):
        state_path = os.path.join(SESSION_DIR, 'current-state.json')
        tmp = state_path + '.recovery_tmp'
        with open(tmp, 'w') as f:
            json.dump(snapshot['state'], f, indent=2)
        os.rename(tmp, state_path)
    return recovered


def recovery_partial(snapshot: dict) -> dict:
    """Partial recovery: restore only checkpoint and critical state."""
    recovered = {
        'checkpoint': snapshot.get('checkpoint', {}),
        'recovery_type': 'partial',
    }
    # Restore checkpoint as current state
    if snapshot.get('checkpoint'):
        check_path = os.path.join(SESSION_DIR, 'checkpoint.json')
        tmp = check_path + '.recovery_tmp'
        with open(tmp, 'w') as f:
            json.dump(snapshot['checkpoint'], f, indent=2)
        os.rename(tmp, check_path)
    return recovered


def recovery_minimal(snapshot: dict) -> dict:
    """Minimal recovery: just restore basic session metadata."""
    checkpoint = snapshot.get('checkpoint', {})
    if not checkpoint:
        checkpoint = {'recovered': True, 'timestamp': datetime.now(timezone.utc).isoformat()}
    return {
        'checkpoint': checkpoint,
        'recovery_type': 'minimal',
        'message': 'Minimal recovery applied. Full context may be limited.',
    }


def recovery_fresh(snapshot: dict) -> dict:
    """Fresh recovery: start new session but preserve crash history."""
    crash_log = snapshot.get('crash_log', [])
    crash_log.append({
        'event': 'session_reset',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'note': 'Session was reset. Crash history preserved.',
    })
    return {
        'recovery_type': 'fresh',
        'message': 'New session started. Previous crash data available in log.',
        'crash_log': crash_log,
    }


def main():
    parser = argparse.ArgumentParser(description='NeuralCline Recovery Subprocess')
    parser.add_argument('--recovery-id', required=True)
    parser.add_argument('--strategy', required=True, choices=['full', 'partial', 'minimal', 'fresh'])
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--crash-type', default='unknown')
    args = parser.parse_args()
    
    try:
        # Load snapshot
        if not os.path.exists(args.snapshot):
            write_result(args.recovery_id, False, {
                'error': f'Snapshot file not found: {args.snapshot}',
                'crash_type': args.crash_type,
            })
            sys.exit(1)
        
        with open(args.snapshot) as f:
            snapshot = json.load(f)
        
        # Execute recovery strategy
        strategy_map = {
            'full': recovery_full,
            'partial': recovery_partial,
            'minimal': recovery_minimal,
            'fresh': recovery_fresh,
        }
        
        executor = strategy_map.get(args.strategy, recovery_minimal)
        recovered_state = executor(snapshot)
        
        # Write success result
        write_result(args.recovery_id, True, {
            'recovered_state': recovered_state,
            'strategy': args.strategy,
            'crash_type': args.crash_type,
            'snapshot_id': snapshot.get('snapshot_id', 'unknown'),
        })
        
        sys.exit(0)
        
    except Exception as e:
        write_result(args.recovery_id, False, {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'crash_type': args.crash_type,
        })
        sys.exit(1)


if __name__ == '__main__':
    main()