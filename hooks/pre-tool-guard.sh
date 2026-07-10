#!/bin/bash
# =============================================================================
# 🛡️ PRE-TOOL GUARD — NeuralCline EDGECASE
# =============================================================================
# Uses state_engine.py instead of inline python3 -c to avoid shell
# integration timeout crashes.
#
# Usage: bash /root/NeuralCline/hooks/pre-tool-guard.sh "<command>"
# =============================================================================

ENGINE="/root/NeuralCline/lib/state_engine.py"
SESSION_DIR="/root/.session-state"
STATE="$SESSION_DIR/current-state.json"
CHECKPOINT="$SESSION_DIR/checkpoint.json"
DIAGNOSE="/root/NeuralCline/hooks/diagnose.sh"

# ─── Stale state detection (hang diagnosis) ──────────────────────────────
check_stale_state() {
    # If state file is missing, nothing to check
    [ ! -f "$STATE" ] && return 0

    local last_str
    last_str=$(grep -o '"last_updated"[[:space:]]*:[[:space:]]*"[^"]*"' "$STATE" | cut -d'"' -f4)
    [ -z "$last_str" ] && return 0

    local now_epoch
    now_epoch=$(date +%s)
    local last_epoch
    last_epoch=$(python3 -c "
from datetime import datetime, timezone
try:
    dt = datetime.fromisoformat('$last_str'.replace('Z', '+00:00'))
    print(int(dt.timestamp()))
except:
    print(0)
" 2>/dev/null)

    [ "$last_epoch" -eq 0 ] && return 0

    local gap=$(( now_epoch - last_epoch ))
    local gap_min=$(( gap / 60 ))

    if [ "$gap_min" -gt 15 ]; then
        local tool_count
        tool_count=$(grep -o '"tool_call_count"[[:space:]]*:[[:space:]]*[0-9]*' "$STATE" | grep -o '[0-9]*$')
        echo "🛑 HANG_DETECTED: State stale for ${gap_min}min (${tool_count} tool calls)"
        echo "   Running full diagnostic..."
        timeout 15 bash "$DIAGNOSE" --quiet 2>&1 || true
        echo "   Recovery: source /root/rehydration.md"
        return 1
    fi
    return 0
}

main() {
    local command="${1:-}"

    # ── Step 1: Check for stale state (possible hang) ──
    if ! check_stale_state; then
        # Don't block the tool if hang detected — just warn and continue
        # The diagnostic is already logged to crash-log.ndjson
        :
    fi

    # ── Step 2: Compute proximity via state_engine.py (safe, no inline python3 -c) ──
    local result
    result=$(timeout 10 python3 "$ENGINE" compute_proximity "$command" 2>&1)
    local proximity=$(echo "$result" | grep "^PROXIMITY=" | cut -d= -f2)
    local pattern=$(echo "$result" | grep "^MATCHED_PATTERN=" | cut -d= -f2)
    local ctx=$(echo "$result" | grep "^CONTEXT_USAGE=" | cut -d= -f2)

    echo "PROXIMITY=$proximity"
    echo "MATCHED_PATTERN=$pattern"
    echo "CONTEXT_USAGE=$ctx"

    if [ "$proximity" -gt 80 ] 2>/dev/null; then
        echo "⚠️  DANGER: Crash proximity score is $proximity (threshold: 80)"
        echo "   Matched failure pattern: $pattern"
        echo "   Auto-saving checkpoint..."
        timeout 10 python3 "$ENGINE" generate_checkpoint >/dev/null 2>&1
    elif [ "$proximity" -gt 60 ] 2>/dev/null; then
        echo "⚠️  WARNING: Crash proximity score is $proximity (threshold: 60)"
        echo "   Matched failure pattern: $pattern"
        echo "   Auto-saving checkpoint..."
        timeout 10 python3 "$ENGINE" generate_checkpoint >/dev/null 2>&1
    elif [ "$proximity" -gt 30 ] 2>/dev/null; then
        echo "ℹ️  CAUTION: Crash proximity score is $proximity"
        echo "   Consider paginating output or truncating."
    else
        echo "✅ SAFE: Crash proximity score is ${proximity:-0}"
    fi
}

main "$@"