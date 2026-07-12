#!/usr/bin/env python3
"""
Context Coordinate System — Session Progress & Confidence Tracking
====================================================================
Purpose: Maps session progress, degradation points, and recovery confidence
into a coordinate space that the organism uses to autonomously continue
without user intervention.

The system tracks:
  - SESSION GOAL: The main intent of the current session
  - PROGRESS VECTOR: What % complete, what remains
  - DEGRADATION POINTS: Hangs/crashes mapped to context fraction
  - CONFIDENCE SCORE: Reward-based confidence from successful recoveries
  - RECURSIVE CONTINUATION: Standard recovery is automatic; novel issues flagged

Coordinate System:
  X-axis: Context usage (0-100% of 1M window)
  Y-axis: Goal completion (0-100% toward session objective)
  Z-axis: Confidence (0-100, accrued from successful recoveries)

Usage: python3 /root/NeuralCline/lib/context_coordinates.py <command> [args...]
"""

import json
import os
import sys
import re
from datetime import datetime, timezone

SESSION_DIR = "/root/.session-state"
COORD_FILE = os.path.join(SESSION_DIR, "context-coordinates.json")
MEMORY_FILE = os.path.join(SESSION_DIR, "session-memory.json")
STATE_FILE = os.path.join(SESSION_DIR, "current-state.json")
FAILURE_POINTS = os.path.join(SESSION_DIR, "failure-points.json")
CRASH_LOG = os.path.join(SESSION_DIR, "crash-log.ndjson")
CHECKPOINT_FILE = os.path.join(SESSION_DIR, "checkpoint.json")

MAX_CTX = 1048576  # 1M token context window


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


def cmd_init(args):
    """Initialize the context coordinate system for a new session goal.

    Usage: context_coordinates.py init "<session goal description>"
    """
    goal = " ".join(args) if args else "BOLIX UEFI bootloader development and debugging"
    
    coords = {
        "session_goal": goal,
        "goal_started": timestamp(),
        "goal_completion_pct": 0,
        "context_x": 0,
        "progress_y": 0,
        "confidence_z": 50,  # Start at neutral confidence
        "degradation_points": [],
        "recoveries": [],
        "novel_issues": [],
        "known_recoveries": 0,
        "total_degradations": 0,
        "consecutive_successes": 0,
        "last_known_state": "",
        "current_phase": "init",
        "phase_history": [],
        "reward_score": 0,
    }
    write_json(COORD_FILE, coords)
    print(f"COORD_INIT=1")
    print(f"COORD_GOAL={goal}")
    print(f"COORD_CONFIDENCE=50")


def cmd_update(args):
    """Update the coordinate system with current session state.

    Reads current state, failure points, and crash log to compute
    the current position in coordinate space.

    Usage: context_coordinates.py update "<current phase>" "<progress note>"
    """
    coords = read_json(COORD_FILE, {})
    if not coords.get("session_goal"):
        cmd_init(["BOLIX UEFI bootloader development and debugging"])
        coords = read_json(COORD_FILE, {})

    phase = args[0] if args else coords.get("current_phase", "unknown")
    progress_note = args[1] if len(args) > 1 else ""

    state = read_json(STATE_FILE, {})
    failures = read_json(FAILURE_POINTS, {})
    memory = read_json(MEMORY_FILE, {})

    # X-axis: Context usage fraction
    current_ctx = state.get("current_context_tokens", 0)
    ctx_frac = min(1.0, current_ctx / MAX_CTX) if MAX_CTX > 0 else 0
    ctx_pct = round(ctx_frac * 100, 1)

    # Count degradation events (hangs + crashes) in this session
    crash_events = 0
    hang_events = 0
    try:
        if os.path.exists(CRASH_LOG):
            with open(CRASH_LOG) as f:
                for line in f:
                    if "hang_detected" in line:
                        hang_events += 1
                    if "crash_detected" in line:
                        crash_events += 1
    except IOError:
        pass
    total_degradations = hang_events + crash_events

    # Y-axis: Goal completion estimate
    # Based on: phases completed, failure patterns resolved, context efficiency
    phase_history = coords.get("phase_history", [])
    phases_completed = len([p for p in phase_history if p.get("status") == "complete"])
    total_phases = max(len(phase_history), 1)
    
    # Factor in failure pattern resolution
    fps = failures.get("failure_points", [])
    resolved_patterns = sum(1 for fp in fps if fp.get("count", 0) < 3)
    total_patterns = max(len(fps), 1)
    pattern_resolution_rate = resolved_patterns / total_patterns if total_patterns > 0 else 0.5

    # Factor in context efficiency (lower ctx_frac with more progress = better)
    ctx_efficiency = max(0, 1.0 - (ctx_frac * 0.5)) if ctx_frac > 0 else 0.5

    # Composite progress score
    progress_y = round((
        (phases_completed / total_phases) * 0.4 +
        pattern_resolution_rate * 0.3 +
        ctx_efficiency * 0.3
    ) * 100, 1)

    # Z-axis: Confidence score
    # Starts at 50, increases with successful recoveries, decreases with novel issues
    known_recoveries = coords.get("known_recoveries", 0)
    novel_issues_count = len(coords.get("novel_issues", []))
    consecutive_successes = coords.get("consecutive_successes", 0)
    
    # Base confidence from recovery ratio
    recovery_ratio = known_recoveries / max(total_degradations, 1)
    confidence_z = round(50 + (recovery_ratio * 30) + min(consecutive_successes * 2, 20) - (novel_issues_count * 5), 1)
    confidence_z = max(0, min(100, confidence_z))

    # Record degradation point if new
    last_degradations = coords.get("total_degradations", 0)
    if total_degradations > last_degradations:
        new_count = total_degradations - last_degradations
        coords.setdefault("degradation_points", []).append({
            "timestamp": timestamp(),
            "context_pct": ctx_pct,
            "progress_y": progress_y,
            "confidence_z": confidence_z,
            "new_events": new_count,
            "phase": phase,
        })
        # Check if this is a known pattern (novel vs known)
        last_crash = ""
        try:
            if os.path.exists(CRASH_LOG):
                with open(CRASH_LOG) as f:
                    for line in f:
                        if line.strip():
                            last_crash = line
        except IOError:
            pass
        
        # Check if this crash pattern exists in failure points
        is_novel = True
        for fp in fps[:5]:
            if fp.get("count", 0) >= 3:
                is_novel = False
                break
        
        if is_novel and new_count <= 1:
            coords.setdefault("novel_issues", []).append({
                "timestamp": timestamp(),
                "context_pct": ctx_pct,
                "phase": phase,
            })
            novel_issues_count += 1
        else:
            known_recoveries += 1
            consecutive_successes += 1

    # Record recovery if confidence stabilized after degradation
    if confidence_z >= coords.get("confidence_z", 50) and total_degradations > 0:
        coords.setdefault("recoveries", []).append({
            "timestamp": timestamp(),
            "context_pct": ctx_pct,
            "confidence_before": coords.get("confidence_z", 50),
            "confidence_after": confidence_z,
            "phase": phase,
        })

    # Update phase history
    if phase != coords.get("current_phase"):
        coords.setdefault("phase_history", []).append({
            "phase": coords.get("current_phase", ""),
            "ended": timestamp(),
            "progress_at_end": progress_y,
            "status": "complete" if confidence_z > 40 else "degraded",
        })
        coords["current_phase"] = phase
        coords.setdefault("phase_history", []).append({
            "phase": phase,
            "started": timestamp(),
            "progress_at_start": progress_y,
            "status": "active",
        })

    # Reward score: accumulated from successful continuations
    reward_score = coords.get("reward_score", 0)
    if consecutive_successes > 0:
        reward_score += 1 * consecutive_successes  # More reward for streaks
    if confidence_z > 70:
        reward_score += 5  # High confidence bonus
    if progress_y > 80:
        reward_score += 10  # Near-completion bonus

    # Update coordinate state
    coords.update({
        "context_x": ctx_pct,
        "progress_y": progress_y,
        "confidence_z": confidence_z,
        "total_degradations": total_degradations,
        "known_recoveries": known_recoveries,
        "novel_issues_count": novel_issues_count,
        "consecutive_successes": consecutive_successes,
        "last_known_state": f"Phase: {phase}, Progress: {progress_y}%, Confidence: {confidence_z}",
        "reward_score": reward_score,
        "last_updated": timestamp(),
    })

    # Trim historical lists to last 100 entries
    for key in ["degradation_points", "recoveries", "novel_issues", "phase_history"]:
            coords[key] = coords[key][-100:]

    write_json(COORD_FILE, coords)

    # Output parseable results
    print(f"COORD_CTX_X={ctx_pct}")
    print(f"COORD_PROGRESS_Y={progress_y}")
    print(f"COORD_CONFIDENCE_Z={confidence_z}")
    print(f"COORD_REWARD={reward_score}")
    print(f"COORD_PHASE={phase}")
    print(f"COORD_DEGRADATIONS={total_degradations}")
    print(f"COORD_RECOVERIES={known_recoveries}")
    print(f"COORD_NOVEL_ISSUES={len(coords.get('novel_issues', []))}")
    print(f"COORD_CONSECUTIVE_SUCCESSES={consecutive_successes}")
    print(f"COORD_LAST_STATE={coords['last_known_state']}")

    # Autonomous continuation decision
    if confidence_z >= 60 and consecutive_successes >= 3:
        print(f"COORD_ACTION=continue")
        print(f"COORD_ACTION_REASON=High confidence ({confidence_z}) with {consecutive_successes} consecutive successes")
    elif confidence_z >= 40:
        print(f"COORD_ACTION=continue_cautious")
        print(f"COORD_ACTION_REASON=Moderate confidence ({confidence_z}) — proceed with monitoring")
    elif novel_issues_count > 2:
        print(f"COORD_ACTION=flag_novel")
        print(f"COORD_ACTION_REASON={novel_issues_count} novel issues detected — may need user guidance")
    else:
        print(f"COORD_ACTION=recover")
        print(f"COORD_ACTION_REASON=Low confidence ({confidence_z}) — running recovery protocols")

    return coords


def cmd_status(args):
    """Print the current coordinate state as JSON."""
    coords = read_json(COORD_FILE, {})
    if not coords:
        print("No coordinate system initialized. Run 'init' first.")
        return
    
    # Compact output
    status = {
        "goal": coords.get("session_goal", "")[:60],
        "context_pct": coords.get("context_x", 0),
        "progress_pct": coords.get("progress_y", 0),
        "confidence": coords.get("confidence_z", 50),
        "reward": coords.get("reward_score", 0),
        "phase": coords.get("current_phase", "unknown"),
        "degradations": coords.get("total_degradations", 0),
        "recoveries": coords.get("known_recoveries", 0),
        "novel_issues": len(coords.get("novel_issues", [])),
        "consecutive_successes": coords.get("consecutive_successes", 0),
        "action": "continue" if coords.get("confidence_z", 0) >= 60 else "recover",
        "last_state": coords.get("last_known_state", ""),
    }
    print(json.dumps(status, indent=2))


def cmd_report(args):
    """Generate a full context coordinate report."""
    coords = read_json(COORD_FILE, {})
    if not coords:
        print("No coordinate system initialized.")
        return

    print("=" * 60)
    print("CONTEXT COORDINATE SYSTEM — SESSION REPORT")
    print("=" * 60)
    print(f"Goal: {coords.get('session_goal', 'N/A')}")
    print(f"Phase: {coords.get('current_phase', 'N/A')}")
    print(f"Started: {coords.get('goal_started', 'N/A')}")
    print()
    print("--- COORDINATES ---")
    print(f"  X (Context):  {coords.get('context_x', 0)}% of 1M window")
    print(f"  Y (Progress): {coords.get('progress_y', 0)}% toward goal")
    print(f"  Z (Confidence): {coords.get('confidence_z', 50)}/100")
    print(f"  Reward Score: {coords.get('reward_score', 0)}")
    print()
    print("--- DEGRADATION & RECOVERY ---")
    print(f"  Total degradations: {coords.get('total_degradations', 0)}")
    print(f"  Known recoveries:   {coords.get('known_recoveries', 0)}")
    print(f"  Novel issues:       {len(coords.get('novel_issues', []))}")
    print(f"  Consecutive successes: {coords.get('consecutive_successes', 0)}")
    print()
    print("--- AUTONOMOUS DECISION ---")
    conf = coords.get('confidence_z', 0)
    succ = coords.get('consecutive_successes', 0)
    if conf >= 60 and succ >= 3:
        print("  ✅ CONTINUE — High confidence, autonomous progression")
    elif conf >= 40:
        print("  ⚠️  CONTINUE CAUTIOUS — Moderate confidence, monitor")
    elif len(coords.get('novel_issues', [])) > 2:
        print("  🆕 FLAG NOVEL — New patterns detected, may need guidance")
    else:
        print("  🔄 RECOVER — Running recovery protocols")
    print()
    print("--- PHASE HISTORY ---")
    for ph in coords.get("phase_history", [])[-5:]:
        status_char = "✅" if ph.get("status") == "complete" else "⚠️"
        print(f"  {status_char} {ph.get('phase', '?')} — progress: {ph.get('progress_at_end', '?')}%")
    print()
    print("--- LAST KNOWN STATE ---")
    print(f"  {coords.get('last_known_state', 'N/A')}")


def cmd_help(args):
    print("Context Coordinate System — Commands:")
    print("  init <goal>       Initialize with session goal")
    print("  update <phase> [note]  Update coordinates with current state")
    print("  status            Print current coordinate state")
    print("  report            Generate full session report")
    print("  help              Show this help message")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd_help([])
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "init": cmd_init,
        "update": cmd_update,
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