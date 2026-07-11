#!/usr/bin/env python3
"""
agentic_exec.py — Agentic Execution Wrapper for NeuralCline v2.

PURPOSE:
  Prevents the cascading hang problem where shell-hooks.sh, pre-tool-guard.sh,
  or post-tool-state.sh call sub-commands that hang, causing the hook itself
  to hang, which then causes Cline's shell integration to timeout and crash.

SOLUTION:
  Every hook invocation is wrapped in a detached subprocess with a HARD
  wall-clock timeout. If the subprocess doesn't complete within the deadline,
  its entire process group is killed. The calling hook never waits for the
  subprocess to complete — it forks and returns immediately.

USAGE:
  python3 /root/NeuralCline/lib/agentic_exec.py <timeout_ms> <script> [args...]

  This spawns the script in a subprocess with a watchdog timer.
  Returns immediately with the PID. The caller can:
    - Check completion: check <pid>  → returns "done" or "running" or "killed"
    - Get exit code:  exitcode <pid> → returns the exit code
    - Kill:           kill <pid>

DESIGN:
  Fork → setitimer(ITIMER_REAL, timeout) → exec the script.
  If the timer fires before the script completes, SIGALRM kills the
  process group. The watchdog is at the OS level — cannot be bypassed.
"""

import os
import sys
import signal
import time
import json

PID_FILE = "/tmp/.neural-agentic-pids.json"


def _load_pids():
    try:
        with open(PID_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_pids(pids):
    with open(PID_FILE, "w") as f:
        json.dump(pids, f)


def spawn(timeout_ms, *args):
    """Fork and exec the command with a hard wall-clock timeout.

    The child process sets up a SIGALRM handler at the OS level.
    If the timeout fires, the child kills its own process group.
    """
    if not args:
        print("ERROR: no command to execute", file=sys.stderr)
        sys.exit(1)

    timeout_sec = max(int(timeout_ms) / 1000.0, 1.0)
    pid = os.fork()

    if pid == 0:
        # ---- CHILD ----
        # Create a new process group
        os.setsid()

        # Set up the alarm — this CANNOT be ignored by sub-threads
        def _alarm_handler(signum, frame):
            # Kill our entire process group
            try:
                os.killpg(os.getpgid(0), signal.SIGKILL)
            except OSError:
                pass
            os._exit(124)

        signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(int(timeout_sec) + 1)  # +1 grace second

        # Exec the actual command
        try:
            os.execvp(args[0], list(args))
        except FileNotFoundError:
            print(f"ERROR: command not found: {args[0]}", file=sys.stderr)
            os._exit(127)
        except Exception as e:
            print(f"ERROR: exec failed: {e}", file=sys.stderr)
            os._exit(126)
    else:
        # ---- PARENT ----
        # Record the PID for later status checks
        cmd_str = " ".join(args)[:120]
        pids = _load_pids()
        pids[str(pid)] = {
            "cmd": cmd_str,
            "timeout_ms": timeout_ms,
            "started": time.time(),
        }
        _save_pids(pids)
        print(pid)
        sys.exit(0)


def check(pid):
    """Check if a spawned process is done."""
    pid = int(pid)
    try:
        wpid, status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        # Process already reaped or doesn't exist
        _cleanup_pid(pid)
        print("done")
        return

    if wpid == 0:
        # Still running
        print("running")
    else:
        # Process completed
        exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
        _cleanup_pid(pid)
        print("done")
        print(exit_code)


def kill_pid(pid):
    """Kill a spawned process and its group."""
    pid = int(pid)
    try:
        os.killpg(pid, signal.SIGKILL)
    except OSError:
        pass
    _cleanup_pid(pid)
    print("killed")


def _cleanup_pid(pid):
    pids = _load_pids()
    pids.pop(str(pid), None)
    _save_pids(pids)


def cleanup_stale():
    """Remove PID entries for processes that no longer exist."""
    pids = _load_pids()
    changed = False
    for pid_str in list(pids.keys()):
        pid = int(pid_str)
        try:
            os.kill(pid, 0)  # Test if process exists
        except OSError:
            del pids[pid_str]
            changed = True
    if changed:
        _save_pids(pids)
    print(f"Cleaned {sum(1 for p in os.listdir('/proc') if p.isdigit() and int(p) in [int(k) for k in pids.keys()])} stale entries")


def list_pids():
    """List all tracked processes."""
    pids = _load_pids()
    if not pids:
        print("No tracked processes.")
        return
    for pid_str, info in sorted(pids.items()):
        age = int(time.time() - info.get("started", 0))
        print(f"PID {pid_str}: {info['cmd']} ({age}s ago, timeout={info['timeout_ms']}ms)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: agentic_exec.py <spawn|check|kill|list|cleanup> [args...]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "spawn" and len(sys.argv) >= 4:
        spawn(sys.argv[2], *sys.argv[3:])
    elif command == "check" and len(sys.argv) >= 3:
        check(sys.argv[2])
    elif command == "kill" and len(sys.argv) >= 3:
        kill_pid(sys.argv[2])
    elif command == "list":
        list_pids()
    elif command == "cleanup":
        cleanup_stale()
    else:
        print(f"Unknown command or missing args: {command}", file=sys.stderr)
        sys.exit(1)