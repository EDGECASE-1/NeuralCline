#!/bin/bash
# =============================================================================
# 🔄 REHYDRATION ENGINE — Session Context Restoration
# =============================================================================
# Source this script to restore full session context from the last checkpoint.
#   source /root/rehydration.md
#
# This reads:  checkpoint.json, failure-points.json, crash-log.ndjson
# Outputs:     A complete context summary for the new session
# =============================================================================

SESSION_DIR="/root/.session-state"
CHECKPOINT="$SESSION_DIR/checkpoint.json"
STATE="$SESSION_DIR/current-state.json"
FAILURE_POINTS="$SESSION_DIR/failure-points.json"
CRASH_LOG="$SESSION_DIR/crash-log.ndjson"
MASTER_PROFILE="/root/master_profile.md"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     🔄 NEURAL SESSION REHYDRATION ENGINE                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# --- 1. Check for checkpoint ---
if [ -f "$CHECKPOINT" ]; then
    echo "✅ CHECKPOINT FOUND"
    echo ""
    echo "─── Last Session Summary ───"
    python3 -c "
import json
with open('$CHECKPOINT') as f:
    cp = json.load(f)
print(f\"  Session ID:      {cp.get('session_id', 'unknown')}\")
print(f\"  Last active:     {cp.get('timestamp', 'unknown')}\")
print(f\"  Tool calls:      {cp.get('total_tool_calls', 0)}\")
print(f\"  Success rate:    {cp.get('success_rate', 'N/A')}%\")
print(f\"  Context usage:   {cp.get('context_usage_pct', '?')}%\")
print(f\"  Last command:    {cp.get('last_command', 'none')[:80]}\")
print()
print('─── Active Goals ───')
goals = cp.get('active_goals', [])
if goals:
    for g in goals:
        print(f\"  • {g}\")
else:
    print('  (none recorded)')
print()
print('─── Next Steps ───')
next_steps = cp.get('next_steps', [])
if next_steps:
    for ns in next_steps:
        print(f\"  • {ns}\")
else:
    print('  (none recorded)')
"
else
    echo "⚠️  No checkpoint found. This appears to be a fresh session."
fi

# --- 2. Crash history summary ---
if [ -f "$FAILURE_POINTS" ]; then
    echo ""
    echo "─── Historical Failure Points ───"
    python3 -c "
import json
with open('$FAILURE_POINTS') as f:
    fps = json.load(f)
points = fps.get('failure_points', [])
if points:
    # Sort by weight descending
    points.sort(key=lambda p: p.get('weight', 0), reverse=True)
    for i, p in enumerate(points[:5]):
        pattern = p.get('pattern', 'unknown')[:60]
        weight = p.get('weight', 0)
        count = p.get('count', 0)
        print(f\"  #{i+1} [{weight:.0f}] {pattern} (x{count})\")
    if len(points) > 5:
        print(f\"  ... and {len(points)-5} more failure patterns\")
else:
    print('  No failure patterns recorded yet.')
"
fi

# --- 3. Recent crash log entries (last 3) ---
if [ -f "$CRASH_LOG" ]; then
    echo ""
    echo "─── Last 3 Crash Log Entries ───"
    python3 -c "
import json
entries = []
with open('$CRASH_LOG') as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except:
                pass
recent = entries[-3:]
for e in recent:
    ts = e.get('timestamp', '?')
    cmd = e.get('command', '?')[:60]
    prox = e.get('crash_proximity_score', '?')
    code = e.get('exit_code', '?')
    print(f\"  [{ts}] exit={code} proximity={prox}% cmd={cmd}\")
"
fi

# --- 4. Current context metrics ---
if [ -f "$STATE" ]; then
    echo ""
    echo "─── Current Session Metrics ───"
    python3 -c "
import json
with open('$STATE') as f:
    s = json.load(f)
print(f\"  Context window:  {s.get('current_context_tokens', 0)} / {s.get('max_context_tokens', 1048576)} tokens\")
print(f\"  Context usage:   {s.get('context_usage_pct', 0)}%\")
print(f\"  Tool call count: {s.get('tool_call_count', 0)}\")
print(f\"  Session starts:  {s.get('session_start_count', 0)}\")
print(f\"  Total sessions:  {s.get('total_session_count', 0)}\")
"
fi

echo ""
echo "─── Rehydration Complete ───"
echo "Read /root/master_profile.md for workspace context."
echo "Type 'source /root/rehydration.md' to run this again."
echo ""