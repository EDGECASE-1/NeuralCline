#!/usr/bin/env python3
"""
NeuralCline Crash Pattern Backtracker
======================================
Reads every hang and crash from crash-log.ndjson, normalizes the command
patterns, and feeds them into failure-points.json so the self-learning
organism naturally learns from every failure — no manual labelling needed.

This completes the auto-feedback loop:
  1. A command fails (hang or crash)
  2. shell-hooks.sh logs it to crash-log.ndjson
  3. crash_backtracker.py reads it and updates failure-points.json
  4. self_learning.py's heal() finds it in Analysis 2 (learned patterns)
  5. pre-tool-guard.sh reads the recommendations and adjusts proactively

Usage:
  python3 /root/NeuralCline/lib/crash_backtracker.py scan    # One-time scan
  python3 /root/NeuralCline/lib/crash_backtracker.py daemon  # Continuous (runs every 30s)
  python3 /root/NeuralCline/lib/crash_backtracker.py stats   # Show learned patterns
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from collections import defaultdict

SESSION_DIR = "/root/.session-state"
CRASH_LOG = os.path.join(SESSION_DIR, "crash-log.ndjson")
FAILURE_POINTS = os.path.join(SESSION_DIR, "failure-points.json")
TIMING_HISTORY = os.path.join(SESSION_DIR, "timing-history.json")
BACKTRACK_MARKER = os.path.join(SESSION_DIR, "backtracker-last-offset")


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


def normalize_pattern(cmd):
    """Normalize a command string into a generalized pattern."""
    if not cmd:
        return ""
    cmd = re.sub(r'--?\w+(?:=\S+)?', '', cmd)
    cmd = re.sub(r'/[^\s]+', '', cmd)
    cmd = re.sub(r'\d+', 'N', cmd)
    cmd = re.sub(r'\s+', ' ', cmd).strip()
    cmd = re.sub(r'(git\s+)(add|commit|push|pull|clone|status|log|branch|checkout|merge|rebase|reset|fetch|diff|stash|tag|init|remote)', r'git \2', cmd)
    cmd = re.sub(r'(apt(-get)?\s+)(install|update|upgrade|remove|purge|autoremove|clean)', r'apt \2', cmd)
    cmd = re.sub(r'(npm|pip|pip3|cargo|gem)\s+(install|update|upgrade|remove|list|run|build|test|publish)', r'\1 \2', cmd)
    return cmd[:60] or "empty"


def read_crash_log():
    """Read all entries from crash-log.ndjson."""
    entries = []
    if not os.path.exists(CRASH_LOG):
        return entries
    try:
        with open(CRASH_LOG) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except IOError:
        pass
    return entries


def get_last_offset():
    """Get the byte offset of the last processed entry."""
    if os.path.exists(BACKTRACK_MARKER):
        try:
            with open(BACKTRACK_MARKER) as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            pass
    return 0


def set_last_offset(offset):
    """Save the byte offset of the last processed entry."""
    try:
        with open(BACKTRACK_MARKER, 'w') as f:
            f.write(str(offset))
    except IOError:
        pass


def scan_new_failures():
    """Scan crash-log.ndjson for new entries and feed them into failure-points.json."""
    if not os.path.exists(CRASH_LOG):
        print("NO_CRASH_LOG")
        return

    last_offset = get_last_offset()
    file_size = os.path.getsize(CRASH_LOG)

    if file_size <= last_offset:
        print("NO_NEW_ENTRIES")
        return

    failures = read_json(FAILURE_POINTS, {"failure_points": []})
    failure_map = {}
    for fp in failures.get("failure_points", []):
        key = fp.get("pattern", "")
        failure_map[key] = fp

    # Read only new bytes
    new_count = 0
    hang_count = 0
    crash_count = 0

    try:
        with open(CRASH_LOG) as f:
            f.seek(last_offset)
            for line in f:
                line = line.strip()
                if not line or line == "[]":
                    continue
                try:
                    entry = json.loads(line)
                    # Skip JSON arrays (sometimes the first line is "[]")
                    if isinstance(entry, list):
                        continue
                except json.JSONDecodeError:
                    continue

                cmd = entry.get("command", "")
                exit_code = entry.get("exit_code", 0)
                hang_detected = entry.get("hang_detected", 0)
                crash_detected = entry.get("crash_detected", 0)
                duration_ms = entry.get("duration_ms", 0)

                # Skip if not a real failure (exit 0, no hang, no crash)
                if exit_code == 0 and not hang_detected and not crash_detected:
                    continue

                pattern = normalize_pattern(cmd)
                if not pattern:
                    continue

                if pattern in failure_map:
                    fp = failure_map[pattern]
                    fp["count"] += 1
                    fp["last_seen"] = timestamp()
                    fp["total_duration_ms"] = fp.get("total_duration_ms", 0) + duration_ms
                    fp["avg_duration_ms"] = fp["total_duration_ms"] // fp["count"]
                    if duration_ms > fp.get("max_duration_ms", 0):
                        fp["max_duration_ms"] = duration_ms
                    if exit_code != 0:
                        ec = fp.get("exit_codes", {})
                        ec[str(exit_code)] = ec.get(str(exit_code), 0) + 1
                        fp["exit_codes"] = ec
                else:
                    failure_map[pattern] = {
                        "pattern": pattern,
                        "example": cmd[:80],
                        "count": 1,
                        "first_seen": timestamp(),
                        "last_seen": timestamp(),
                        "total_duration_ms": duration_ms,
                        "avg_duration_ms": duration_ms,
                        "max_duration_ms": duration_ms,
                        "has_hangs": hang_detected == 1,
                        "has_crashes": crash_detected == 1,
                        "exit_codes": {str(exit_code): 1} if exit_code != 0 else {},
                        "complexity": 3 if hang_detected else 2,  # hangs are higher priority
                    }

                new_count += 1
                if hang_detected:
                    hang_count += 1
                if crash_detected:
                    crash_count += 1

    except IOError:
        pass

    # Write back failure points
    failures["failure_points"] = sorted(
        list(failure_map.values()),
        key=lambda x: x.get("count", 0),
        reverse=True
    )
    failures["last_updated"] = timestamp()
    failures["total_patterns"] = len(failure_map)
    failures["total_new"] = new_count
    write_json(FAILURE_POINTS, failures)

    # Update offset
    set_last_offset(file_size)

    # Also update timing history pattern stats (weighted learning)
    timing = read_json(TIMING_HISTORY, {})
    patterns = timing.get("command_patterns", {})
    for fp in failures["failure_points"]:
        pat = fp.get("pattern", "")
        count = fp.get("count", 0)
        if pat in patterns:
            patterns[pat]["complexity"] = max(patterns[pat].get("complexity", 1), fp.get("complexity", 2))
            patterns[pat]["failure_count"] = patterns[pat].get("failure_count", 0) + count
    timing["command_patterns"] = patterns
    timing["last_updated"] = timestamp()
    write_json(TIMING_HISTORY, timing)

    print(f"SCANNED={new_count}")
    print(f"HANGS={hang_count}")
    print(f"CRASHES={crash_count}")
    print(f"TOTAL_PATTERNS={len(failure_map)}")


def cmd_scan():
    """One-time scan of crash log."""
    scan_new_failures()


def cmd_daemon():
    """Continuous scanning every 30 seconds."""
    print("Backtracker daemon starting...")
    cycle = 0
    while True:
        try:
            result = scan_new_failures()
            cycle += 1
            sys.stderr.write(f"\r[Backtracker] Cycle {cycle} | {result}      ")
            sys.stderr.flush()
        except KeyboardInterrupt:
            print("\nBacktracker stopped.")
            break
        except Exception as e:
            sys.stderr.write(f"\r[Backtracker] Error: {e}       ")
        time.sleep(30)
    print("Backtracker daemon exited.")


def cmd_stats():
    """Show learned patterns from failure points."""
    failures = read_json(FAILURE_POINTS, {"failure_points": []})
    fplist = failures.get("failure_points", [])

    if not fplist:
        print("No failure patterns learned yet.")
        return

    print(f"═══ Learned Crash Patterns ({len(fplist)} total) ═══")
    print(f"{'#':>3} {'Count':>6} {'Type':>6} {'Complexity':>10} {'Pattern':>40}")
    print("-" * 70)

    for i, fp in enumerate(fplist[:20]):
        count = fp.get("count", 0)
        has_hangs = fp.get("has_hangs", False)
        has_crashes = fp.get("has_crashes", False)
        ctype = "H+B" if (has_hangs and has_crashes) else ("HANG" if has_hangs else "CRASH")
        complexity = fp.get("complexity", 1)
        pattern = fp.get("pattern", "")[:38]
        print(f"{i+1:>3} {count:>6} {ctype:>6} {complexity:>10} {pattern:>40}")

    print(f"\nTotal patterns tracked: {len(fplist)}")
    print(f"Total new last scan: {failures.get('total_new', 0)}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    if cmd == "scan":
        cmd_scan()
    elif cmd == "daemon":
        cmd_daemon()
    elif cmd == "stats":
        cmd_stats()
    else:
        print("Usage: python3 crash_backtracker.py [scan|daemon|stats]")
        sys.exit(1)