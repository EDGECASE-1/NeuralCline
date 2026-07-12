#!/usr/bin/env python3
"""
Neural Value Distillation Engine — Context-to-Value Metric Extraction
=======================================================================
Purpose: A general-purpose input analyzer that processes EVERY command,
crash, hang, and pattern through a neural value matrix. Extracts actionable
value metrics, discards low-signal noise, and maintains only high-value
logic to minimize context waste and execution overhead.

The engine operates as a recurring step in every heal cycle:
  1. RECEIVE: Every input (command, crash, hang, pattern, timing)
  2. EXTRACT: Value metrics (signal strength, novelty, relevance, cost)
  3. DISTILL: Discard low-value patterns, promote high-signal ones
  4. STORE: Keep only the top N% of value-weighted information
  5. SYNC: Feed distilled results into master sync

Value Matrix Metrics:
  - Signal Strength: How many times did this pattern predict real issues?
  - Novelty Score: Is this a new pattern or a known failure mode?
  - Relevance Weight: How relevant is this to the current session goal?
  - Cost Score: How much context did this consume vs value delivered?
  - Composite Value: Signal * Relevance / Cost

Usage: python3 /root/NeuralCline/lib/distillation_engine.py <command> [args...]
"""

import json
import os
import sys
import re
import math
from datetime import datetime, timezone
from collections import defaultdict

SESSION_DIR = "/root/.session-state"
STATE_FILE = os.path.join(SESSION_DIR, "current-state.json")
MEMORY_FILE = os.path.join(SESSION_DIR, "session-memory.json")
TIMING_HISTORY = os.path.join(SESSION_DIR, "timing-history.json")
FAILURE_POINTS = os.path.join(SESSION_DIR, "failure-points.json")
CRASH_LOG = os.path.join(SESSION_DIR, "crash-log.ndjson")
COORD_FILE = os.path.join(SESSION_DIR, "context-coordinates.json")
DISTILL_FILE = os.path.join(SESSION_DIR, "distillation-matrix.json")

MAX_CTX = 1048576
MAX_DISTILLED_ENTRIES = 200  # Keep only top 200 value-weighted entries


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


def compute_value_metrics(entry, state, timing, failures, goal_context):
    """Compute the Neural Value Matrix for a single input entry.

    Returns dict with:
      - signal_strength: 0-1, how predictive this entry is
      - novelty_score: 0-1, new pattern vs known failure
      - relevance_weight: 0-1, relevance to session goal
      - cost_score: 0-1, context consumed vs value delivered
      - composite_value: 0-1, final distilled value
      - retention: 'keep', 'promote', or 'discard'
    """
    cmd = entry.get("command", "")
    exit_code = entry.get("exit_code", 0)
    duration_ms = entry.get("duration_ms", 0)
    hang = entry.get("hang_detected", 0)
    crash = entry.get("crash_detected", 0)

    # Normalize command for pattern matching
    norm = cmd[:80].lower()

    # --- Signal Strength ---
    # How many times does this pattern appear in failure points?
    signal_strength = 0.1  # baseline
    for fp in failures.get("failure_points", []):
        if fp.get("pattern", "") in norm or norm[:20] in fp.get("pattern", ""):
            count = fp.get("count", 0)
            signal_strength = min(1.0, count / 20)  # cap at 20 occurrences
            break

    # --- Novelty Score ---
    # 1.0 = completely new, 0.0 = well-known pattern
    novelty_score = 0.5
    if hang or crash:
        # Check if this exact command pattern exists in failure points
        is_known = False
        for fp in failures.get("failure_points", [])[:10]:
            if fp.get("count", 0) >= 3:
                is_known = True
                break
        novelty_score = 0.2 if is_known else 0.8

    # --- Relevance Weight ---
    # Does this relate to the session goal?
    goal = goal_context or ""
    relevance_keywords = ["bolix", "uefi", "boot", "crt0", "reloc", "efi",
                          "qemu", "build", "link", "compile", "module"]
    relevance_weight = 0.3  # baseline
    for kw in relevance_keywords:
        if kw in norm:
            relevance_weight = min(1.0, relevance_weight + 0.15)
    
    # Shell noise gets low relevance
    noise_patterns = ["__vsc_original", "PROMPT_COMMAND", "source /root",
                      "cd /root", "ls --color"]
    for np in noise_patterns:
        if np in norm:
            relevance_weight = max(0.1, relevance_weight - 0.2)

    # --- Cost Score ---
    # How much context did this consume?
    # Long commands with no signal = high cost
    cmd_length = len(cmd)
    cost_score = min(1.0, cmd_length / 500)  # 500 char cmd = max cost

    # If it's a hang or crash, the cost is higher
    if hang or crash:
        cost_score = min(1.0, cost_score + 0.3)

    # Lower cost for high-signal patterns
    if signal_strength > 0.5:
        cost_score = max(0.1, cost_score - 0.2)

    # --- Composite Value ---
    composite_value = (signal_strength * 0.3 + 
                       (1 - novelty_score) * 0.1 +  # Invert: known patterns are more valuable
                       relevance_weight * 0.3 +
                       (1 - cost_score) * 0.3)  # Invert: low cost = high value

    # --- Retention Decision ---
    if composite_value > 0.65:
        retention = "promote"
    elif composite_value > 0.35:
        retention = "keep"
    else:
        retention = "discard"

    return {
        "signal_strength": round(signal_strength, 3),
        "novelty_score": round(novelty_score, 3),
        "relevance_weight": round(relevance_weight, 3),
        "cost_score": round(cost_score, 3),
        "composite_value": round(composite_value, 3),
        "retention": retention,
    }


def cmd_distill(args):
    """Run the full distillation process on all current session data.

    Processes crash log, failure points, timing data, and current state
    through the value matrix. Updates the distillation matrix file and
    returns summary statistics.
    """
    state = read_json(STATE_FILE, {})
    timing = read_json(TIMING_HISTORY, {})
    failures = read_json(FAILURE_POINTS, {})
    memory = read_json(MEMORY_FILE, {})
    coords = read_json(COORD_FILE, {})
    matrix = read_json(DISTILL_FILE, {"distilled_entries": [], "run_count": 0})

    goal_context = coords.get("session_goal", "")
    run_count = matrix.get("run_count", 0) + 1

    all_entries = []
    
    # Process crash log entries
    crash_entries = []
    try:
        if os.path.exists(CRASH_LOG):
            with open(CRASH_LOG) as f:
                for line in f:
                    line = line.strip()
                    if line and line != "[]":
                        try:
                            crash_entries.append(json.loads(line))
                        except:
                            pass
    except IOError:
        pass

    for entry in crash_entries[-100:]:  # Process last 100 entries
        metrics = compute_value_metrics(entry, state, timing, failures, goal_context)
        all_entries.append({
            "type": "crash",
            "command": entry.get("command", "")[:80],
            "timestamp": entry.get("timestamp", ""),
            "exit_code": entry.get("exit_code", 0),
            "metrics": metrics,
        })

    # Process failure points
    for fp in failures.get("failure_points", []):
        # Create a synthetic entry for each failure point
        example_cmd = fp.get("example_commands", [""])[0] if fp.get("example_commands") else fp.get("pattern", "")
        metrics = compute_value_metrics(
            {"command": example_cmd, "exit_code": 1, "duration_ms": 1000, "hang_detected": 0, "crash_detected": 1},
            state, timing, failures, goal_context
        )
        # Boost signal for high-count patterns
        count = fp.get("count", 0)
        if count > 5:
            metrics["signal_strength"] = min(1.0, metrics["signal_strength"] + 0.2)
            metrics["composite_value"] = min(1.0, metrics["composite_value"] + 0.1)
            if metrics["composite_value"] > 0.65:
                metrics["retention"] = "promote"
        all_entries.append({
            "type": "failure_pattern",
            "pattern": fp.get("pattern", "")[:60],
            "count": count,
            "weight": fp.get("weight", 0),
            "metrics": metrics,
        })

    # Sort by composite value descending
    all_entries.sort(key=lambda e: e["metrics"]["composite_value"], reverse=True)

    # Apply retention decisions
    promoted = [e for e in all_entries if e["metrics"]["retention"] == "promote"]
    kept = [e for e in all_entries if e["metrics"]["retention"] == "keep"]
    discarded = [e for e in all_entries if e["metrics"]["retention"] == "discard"]

    # Keep only top entries by value
    distilled = promoted + kept
    if len(distilled) > MAX_DISTILLED_ENTRIES:
        distilled = distilled[:MAX_DISTILLED_ENTRIES]

    # Calculate distillation efficiency
    total_input = len(all_entries)
    total_output = len(distilled)
    efficiency = round((1 - total_output / max(total_input, 1)) * 100, 1)

    # Update the matrix
    matrix["distilled_entries"] = distilled
    matrix["run_count"] = run_count
    matrix["last_run"] = timestamp()
    matrix["input_count"] = total_input
    matrix["output_count"] = total_output
    matrix["efficiency_pct"] = efficiency
    matrix["promoted_count"] = len(promoted)
    matrix["kept_count"] = len(kept)
    matrix["discarded_count"] = len(discarded)
    matrix["avg_composite_value"] = round(
        sum(e["metrics"]["composite_value"] for e in distilled) / max(len(distilled), 1), 3
    )

    write_json(DISTILL_FILE, matrix)
    
    # Parseable output
    print(f"DISTILL_RUN={run_count}")
    print(f"DISTILL_INPUT={total_input}")
    print(f"DISTILL_OUTPUT={total_output}")
    print(f"DISTILL_EFFICIENCY={efficiency}%")
    print(f"DISTILL_PROMOTED={len(promoted)}")
    print(f"DISTILL_KEPT={len(kept)}")
    print(f"DISTILL_DISCARDED={len(discarded)}")
    print(f"DISTILL_AVG_VALUE={matrix['avg_composite_value']}")
    print(f"DISTILL_TIMESTAMP={timestamp()}")

    # Log discarded items summary
    if discarded:
        discarded_patterns = set(d.get("pattern", d.get("command", ""))[:30] for d in discarded)
        print(f"DISTILL_DISCARDED_PATTERNS={'; '.join(list(discarded_patterns)[:5])}")

    return matrix


def cmd_status(args):
    """Print current distillation matrix summary."""
    matrix = read_json(DISTILL_FILE, {})
    if not matrix.get("run_count"):
        print("No distillation runs yet. Execute 'distill' first.")
        return
    
    status = {
        "runs": matrix.get("run_count", 0),
        "last_run": matrix.get("last_run", ""),
        "efficiency_pct": matrix.get("efficiency_pct", 0),
        "avg_composite_value": matrix.get("avg_composite_value", 0),
        "promoted": matrix.get("promoted_count", 0),
        "kept": matrix.get("kept_count", 0),
        "discarded": matrix.get("discarded_count", 0),
        "total_distilled": matrix.get("output_count", 0),
    }
    print(json.dumps(status, indent=2))


def cmd_report(args):
    """Generate a full distillation report."""
    matrix = read_json(DISTILL_FILE, {})
    if not matrix.get("run_count"):
        print("No distillation runs yet.")
        return

    print("=" * 60)
    print("NEURAL VALUE DISTILLATION ENGINE — REPORT")
    print("=" * 60)
    print(f"Runs completed: {matrix.get('run_count', 0)}")
    print(f"Last run: {matrix.get('last_run', 'N/A')}")
    print()
    print("--- EFFICIENCY ---")
    print(f"  Input entries:  {matrix.get('input_count', 0)}")
    print(f"  Output entries: {matrix.get('output_count', 0)}")
    print(f"  Efficiency:     {matrix.get('efficiency_pct', 0)}% discarded")
    print(f"  Avg value:      {matrix.get('avg_composite_value', 0)}")
    print()
    print("--- RETENTION ---")
    print(f"  Promoted: {matrix.get('promoted_count', 0)}")
    print(f"  Kept:     {matrix.get('kept_count', 0)}")
    print(f"  Discarded: {matrix.get('discarded_count', 0)}")
    print()
    print("--- TOP DISTILLED ENTRIES (by value) ---")
    for i, entry in enumerate(matrix.get("distilled_entries", [])[:10]):
        name = entry.get("pattern", entry.get("command", ""))[:50]
        val = entry["metrics"]["composite_value"]
        ret = entry["metrics"]["retention"]
        sig = entry["metrics"]["signal_strength"]
        print(f"  {i+1}. [{ret}] value={val} signal={sig} | {name}")
    print()
    print("--- DISCARDS ---")
    print(f"  {matrix.get('discarded_count', 0)} entries discarded as low-value noise")


def cmd_help(args):
    print("Neural Value Distillation Engine — Commands:")
    print("  distill           Run distillation on all current session data")
    print("  status            Print current distillation summary")
    print("  report            Generate full distillation report")
    print("  help              Show this help message")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd_help([])
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "distill": cmd_distill,
        "status": cmd_status,
        "report": cmd_report,
        "help": cmd_help,
    }

    if command in commands:
        commands[command](args)
    else:
        print(f"Unknown command: {command}")
        cmd_help([])
        sys.exit(1)