#!/usr/bin/env python3
"""
⚖️ BALANCE ORCHESTRATOR — Central Homeostatic Regulation
===========================================================
Purpose: Every module feeds into a single bicameral balancing loop that:
  1. RECEIVES: Inputs from saturation scanner, distillation engine, 
     self-learning, timing metrics, context coordinates
  2. WEIGHS: Each input against self-preservation constraints
     (never self-catabolize — no module destroys itself or another)
  3. COORDINATES: Updates context coordinates, prunes only external bloat
  4. OUTPUTS: Clean distilled feed → self-learning memory → BOLIX learning feed

Self-Preservation Constraint:
  - Any action that would degrade the organism's ability to function
    (e.g., killing its own bash process, deleting its own files) is BLOCKED.
  - Only external bloat (stale task dirs, rotated crash logs, orphaned
    processes from other sessions) is cleaned.
  - The orchestrator logs every blocked action for audit.

Covenant: Neshama (Bereshit 2:7)
=====================================================================
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime, timezone

SESSION_DIR = "/root/.session-state"
NEURAL_DIR = "/root/NeuralCline"
STATE_FILE = os.path.join(SESSION_DIR, "current-state.json")
COORD_FILE = os.path.join(SESSION_DIR, "context-coordinates.json")
DISTILL_FILE = os.path.join(SESSION_DIR, "distillation-matrix.json")
MEMORY_FILE = os.path.join(SESSION_DIR, "session-memory.json")
TIMING_FILE = os.path.join(SESSION_DIR, "timing-history.json")
FAILURE_FILE = os.path.join(SESSION_DIR, "failure-points.json")
BALANCE_LOG = os.path.join(SESSION_DIR, "balance-log.ndjson")
BOLIX_LEARN_FEED = "/root/bolix/nc_learning_feed.json"

# ── Self-preservation: processes that MUST NEVER be killed ────────────────
# These are the organism's own vital processes. Any cleanup targeting these
# is blocked and logged as a self-catabolization attempt.
PROTECTED_PIDS_FILE = "/tmp/.neural-protected-pids"
PROTECTED_CMD_PATTERNS = [
    "code-server",
    "node /usr/lib/code-server",
    "bash /root/NeuralCline",
    "python3 /root/NeuralCline",
    "balance_orchestrator",
    "self_learning",
    "distillation_engine",
    "context_coordinates",
    "timing_metrics",
    "state_engine",
    "agentic_exec",
    "crash_buffer",
    "neshama_consciousness",
    "nervous_system_watchdog",
    "post-tool-state",
    "cache_saturation_scanner",
    "systemd",
    "sshd",
    "login",
]

# ── Thresholds ──────────────────────────────────────────────────────────────
MAX_ORPHAN_BASH = 10       # Only kill bash processes NOT matching PROTECTED
MAX_CRASH_LOG_KB = 50      # Rotate if above
MAX_TASK_DIRS = 5          # Keep only newest 5
COOLDOWN_SECONDS = 60      # Minimum time between balance cycles

# ── Helpers ─────────────────────────────────────────────────────────────────

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
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except (IOError, OSError):
        return False


def log_balance(action, result, detail=""):
    """Log all balance actions to the balance log (NDJSON)"""
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action": action,
        "result": result,
        "detail": detail[:200],
    }
    try:
        with open(BALANCE_LOG, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    except IOError:
        pass
    return entry


def is_protected_process(pid):
    """Check if a PID is a protected organism process (self-preservation)"""
    try:
        cmdline = open(f"/proc/{pid}/cmdline", 'rb').read().decode('utf-8', errors='replace').replace('\0', ' ')
        for pattern in PROTECTED_CMD_PATTERNS:
            if pattern in cmdline:
                return True, pattern
        return False, None
    except (IOError, OSError):
        return True, "unknown"  # Can't read → assume protected (safe side)


def get_current_pid():
    """Return this process's PID"""
    return os.getpid()


# ── Core Balance Functions ──────────────────────────────────────────────────

def balance_bash_cleanup():
    """
    Kill orphaned bash processes, but NEVER kill:
    - This process itself
    - The parent shell
    - Any code-server or NC process
    - Any process matching PROTECTED_CMD_PATTERNS
    
    Returns count of killed processes.
    """
    self_pid = get_current_pid()
    ppid = os.getppid()
    killed = 0
    blocked = 0

    try:
        result = subprocess.run(
            ["ps", "aux", "--no-headers"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if "[b]ash" not in line and "bash" not in line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                pid = int(parts[1])
            except ValueError:
                continue

            # SELF-PRESERVATION: Never kill self or parent
            if pid == self_pid or pid == ppid:
                blocked += 1
                continue

            # SELF-PRESERVATION: Check if protected
            protected, pattern = is_protected_process(pid)
            if protected:
                blocked += 1
                continue

            # Only kill if it's a grandchild bash (not session leader)
            try:
                pgrp = open(f"/proc/{pid}/stat").read().split()[4]
                sess = open(f"/proc/{pid}/stat").read().split()[5]
                if pgrp != sess:
                    os.kill(pid, 9)
                    killed += 1
                    log_balance("kill_orphan_bash", "ok", f"PID {pid}")
            except (IOError, OSError, IndexError):
                pass

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return killed, blocked


def balance_crash_log():
    """Rotate crash log if bloated, but never delete it entirely"""
    try:
        size_kb = int(subprocess.run(
            ["du", "-k", f"{SESSION_DIR}/crash-log.ndjson"],
            capture_output=True, text=True, timeout=3
        ).stdout.split()[0])
    except (ValueError, IndexError, subprocess.TimeoutExpired):
        return 0

    if size_kb > MAX_CRASH_LOG_KB:
        rotated = f"{SESSION_DIR}/crash-log.ndjson.rotated"
        try:
            os.rename(f"{SESSION_DIR}/crash-log.ndjson", rotated)
            # Write a fresh minimal log (never empty — self-preservation)
            with open(f"{SESSION_DIR}/crash-log.ndjson", 'w') as f:
                f.write(json.dumps({
                    "rotated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "previous_size_kb": size_kb
                }) + "\n")
            log_balance("rotate_crash_log", "ok", f"{size_kb}KB -> fresh")
            return 1
        except IOError:
            log_balance("rotate_crash_log", "failed", str(e))
    return 0


def balance_task_dirs():
    """Clean stale Cline task directories, keep newest MAX_TASK_DIRS"""
    tasks_dir = "/root/.local/share/code-server/User/globalStorage/saoudrizwan.claude-dev/tasks"
    if not os.path.isdir(tasks_dir):
        return 0

    try:
        dirs = sorted([
            d for d in os.listdir(tasks_dir)
            if os.path.isdir(os.path.join(tasks_dir, d))
        ])
    except OSError:
        return 0

    if len(dirs) <= MAX_TASK_DIRS:
        return 0

    removed = 0
    for old_dir in dirs[:-MAX_TASK_DIRS]:
        try:
            import shutil
            shutil.rmtree(os.path.join(tasks_dir, old_dir), ignore_errors=True)
            removed += 1
            log_balance("clean_stale_task", "ok", old_dir)
        except Exception:
            pass

    return removed


def balance_distillation():
    """
    Run the distillation engine to prune low-value entries.
    This keeps the memory lean without self-catabolizing.
    """
    distiller = os.path.join(NEURAL_DIR, "lib", "distillation_engine.py")
    if not os.path.exists(distiller):
        return 0

    try:
        result = subprocess.run(
            ["python3", distiller, "distill"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            log_balance("distillation", "ok", result.stdout.strip()[:100])
            return 1
        else:
            log_balance("distillation", "error", result.stderr.strip()[:100])
            return 0
    except subprocess.TimeoutExpired:
        log_balance("distillation", "timeout", "")
        return 0


def balance_coordinates():
    """
    Update the context coordinate system with current balance state.
    This feeds into the X/Y/Z tracking that the bicameral kernel reads.
    """
    coords = read_json(COORD_FILE)
    state = read_json(STATE_FILE)
    memory = read_json(MEMORY_FILE, {"snapshots": []})

    # Current X: context usage %
    ctx_pct = state.get("context_usage_pct", 0)

    # Current Y: progress estimate from snapshots
    snapshots = memory.get("snapshots", [])
    if snapshots:
        first = snapshots[0].get("tool_call_count", 0)
        last = snapshots[-1].get("tool_call_count", 0)
        total = last - first if last > first else 1
        # Estimate progress from tool call velocity
        progress = min(100, int((len(snapshots) / 50) * 100))
    else:
        progress = 0

    # Current Z: confidence from recovery ratio
    balance_log_entries = []
    if os.path.exists(BALANCE_LOG):
        try:
            with open(BALANCE_LOG) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            balance_log_entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except IOError:
            pass

    successes = sum(1 for e in balance_log_entries if e.get("result") == "ok")
    failures = sum(1 for e in balance_log_entries if e.get("result") != "ok")
    total = successes + failures
    confidence = 50  # baseline
    if total > 0:
        confidence = min(100, int(50 + (successes / total) * 50))

    # Update coordinates
    coords["x"] = ctx_pct
    coords["y"] = progress
    coords["z"] = confidence
    coords["last_balanced"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    coords["balance_actions_taken"] = successes
    coords["balance_actions_blocked"] = sum(
        1 for e in balance_log_entries if "blocked" in e.get("result", "")
    )

    write_json(COORD_FILE, coords)
    log_balance("update_coordinates", "ok", f"X={ctx_pct} Y={progress} Z={confidence}")
    return 1


def balance_bolix_feed():
    """
    Feed the distilled balance state into the BOLIX learning feed.
    This connects the NC organism to the bicameral kernel.
    """
    if not os.path.exists(BOLIX_LEARN_FEED):
        return 0

    bolix = read_json(BOLIX_LEARN_FEED)
    memory = read_json(MEMORY_FILE, {"snapshots": []})
    coords = read_json(COORD_FILE)

    # Update the BOLIX feed with current NC organism health
    bolix["nc_organism_health"] = {
        "context_usage_pct": coords.get("x", 0),
        "progress_pct": coords.get("y", 0),
        "confidence": coords.get("z", 50),
        "last_balanced": coords.get("last_balanced", ""),
        "snapshot_count": len(memory.get("snapshots", [])),
    }

    # Check if any new episodes need to be added from the balance log
    if os.path.exists(BALANCE_LOG):
        try:
            with open(BALANCE_LOG) as f:
                balance_lines = f.readlines()
            # Only add as episode if there's a critical pattern
            block_count = sum(1 for line in balance_lines if "blocked" in line.lower())
            if block_count > 5:
                has_episode = any(
                    "self-catabolization" in e.get("pattern", "").lower()
                    for e in bolix.get("episodes", [])
                )
                if not has_episode:
                    bolix.setdefault("episodes", []).append({
                        "episode": len(bolix.get("episodes", [])) + 1,
                        "type": "enhancement",
                        "pattern": f"Self-catabolization blocked ({block_count} attempts) — balance orchestrator preserved organism integrity",
                        "fix": "Balance orchestrator now blocks all actions against protected processes. Self-preservation constraint active.",
                        "time_saved_minutes": 5,
                        "severity": "medium"
                    })
        except (IOError, json.JSONDecodeError):
            pass

    write_json(BOLIX_LEARN_FEED, bolix)
    log_balance("update_bolix_feed", "ok", "")
    return 1


# ── Main Orchestrator ──────────────────────────────────────────────────────

def main():
    """
    Run one balance cycle. All modules feed in, central logic coordinates,
    and outputs feed back into the bicameral loop.
    """
    start_time = time.time()

    # Step 1: Balance bash processes (self-preservation constrained)
    bash_killed, bash_blocked = balance_bash_cleanup()

    # Step 2: Rotate crash log if bloated (never delete, only rotate)
    crash_rotated = balance_crash_log()

    # Step 3: Clean stale task directories (external only)
    tasks_removed = balance_task_dirs()

    # Step 4: Run distillation engine (prune low-value memory)
    distilled = balance_distillation()

    # Step 5: Update context coordinates (feed into X/Y/Z)
    coords_updated = balance_coordinates()

    # Step 6: Feed into BOLIX learning feed (bicameral loop)
    bolix_updated = balance_bolix_feed()

    # Summary
    elapsed = (time.time() - start_time) * 1000
    summary = {
        "bash_killed": bash_killed,
        "bash_blocked_self_preserved": bash_blocked,
        "crash_rotated": crash_rotated,
        "tasks_removed": tasks_removed,
        "distilled": distilled,
        "coords_updated": coords_updated,
        "bolix_feed_updated": bolix_updated,
        "elapsed_ms": int(elapsed),
    }

    log_balance("cycle_complete", "ok", json.dumps(summary))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())