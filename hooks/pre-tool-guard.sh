#!/bin/bash
# =============================================================================
# 🛡️ PRE-TOOL GUARD — NeuralCline EDGECASE
# =============================================================================
# Uses state_engine.py and timing_metrics.py instead of inline python3 -c to
# avoid shell integration timeout crashes.
#
# Features:
#   - Stale state detection (hang diagnosis)
#   - Crash proximity scoring (historical failure patterns + context usage)
#   ⏱️ Timing proximity scoring (Execution Emulation Factor + timeout prediction)
#   - Auto-checkpoint generation at danger thresholds
#
# Usage: bash /root/NeuralCline/hooks/pre-tool-guard.sh "<command>"
# =============================================================================

ENGINE="/root/NeuralCline/lib/state_engine.py"
TIMING_ENGINE="/root/NeuralCline/lib/timing_metrics.py"
SELF_LEARNING="/root/NeuralCline/lib/self_learning.py"
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

# ⏱️ Timing proximity prediction + hang buffer routing
HANG_BUFFER="$NEURAL_DIR/hooks/hang-buffer.sh"
check_timing_proximity() {
    local command="${1:-}"
    [ -z "$command" ] && return 0

    local result
    result=$(timeout 10 python3 "$TIMING_ENGINE" predict_timeout "$command" 2>&1)
    local timeout_prox=$(echo "$result" | grep "^TIMEOUT_PROXIMITY=" | cut -d= -f2)
    local severity=$(echo "$result" | grep "^SEVERITY=" | cut -d= -f2)
    local estimated_ms=$(echo "$result" | grep "^ESTIMATED_MS=" | cut -d= -f2)
    local estimated_sec=$(echo "$result" | grep "^ESTIMATED_SEC=" | cut -d= -f2)
    local eef=$(echo "$result" | grep "^EEF=" | cut -d= -f2)
    local action=$(echo "$result" | grep "^ACTION=" | cut -d= -f2)
    local pattern_known=$(echo "$result" | grep "^PATTERN_KNOWN=" | cut -d= -f2)
    local ctx=$(echo "$result" | grep "^CONTEXT_USAGE=" | cut -d= -f2)

    echo "TIMEOUT_PROXIMITY=$timeout_prox"
    echo "TIMING_SEVERITY=$severity"
    echo "EEF=$eef"
    echo "ESTIMATED_SEC=$estimated_sec"
    echo "TIMING_ACTION=$action"
    echo "PATTERN_KNOWN=$pattern_known"

    # Apply timing-based actions
    if [ "$timeout_prox" -ge 80 ] 2>/dev/null && [ "$severity" = "DANGER" ]; then
        echo "⏱️  TIMING DANGER: Timeout proximity is $timeout_prox/100"
        echo "   EEF=$eef | Estimated: ${estimated_sec}s vs threshold 60s"
        echo "   $action"
        echo "   Auto-saving checkpoint before execution..."
        timeout 10 python3 "$ENGINE" generate_checkpoint >/dev/null 2>&1
        return 1
    elif [ "$timeout_prox" -ge 60 ] 2>/dev/null; then
        echo "⏱️  TIMING WARNING: Timeout proximity is $timeout_prox/100"
        echo "   EEF=$eef | Estimated: ${estimated_sec}s"
        echo "   $action"
        echo "   Auto-saving checkpoint..."
        timeout 10 python3 "$ENGINE" generate_checkpoint >/dev/null 2>&1
        # Fork to hang buffer so Cline doesn't lock up
        if [ -n "$command" ] && [ -x "$HANG_BUFFER" ]; then
            echo "⏱️  ROUTING TO HANG BUFFER: Forking command to detached subprocess"
            local buffer_result
            buffer_result=$(bash "$HANG_BUFFER" exec "$command" 2>&1)
            local buffer_id=$(echo "$buffer_result" | grep "^BUFFER_ID=" | cut -d= -f2)
            local bg_pid=$(echo "$buffer_result" | grep "^PID=" | cut -d= -f2)
            echo "   Buffer ID: $buffer_id (PID: $bg_pid)"
            echo "   Check: bash $HANG_BUFFER status $buffer_id"
            echo "   Result: bash $HANG_BUFFER result $buffer_id"
            # Export for post-tool-state.sh to reference
            export __NEURAL_BUFFER_ID="$buffer_id"
            export __NEURAL_BUFFER_PID="$bg_pid"
        fi
    elif [ "$timeout_prox" -ge 40 ] 2>/dev/null; then
        echo "⏱️  TIMING INFO: Timeout proximity is $timeout_prox/100"
        echo "   $action"
    else
        echo "⏱️  TIMING SAFE: Timeout proximity is ${timeout_prox:-0}/100"
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

    # ⏱️ Step 1.5: Check timing proximity (NEW — before crash proximity)
    # This runs first because timeout prediction is the most critical early warning
    if ! check_timing_proximity "$command"; then
        # Timing danger — block execution, generate checkpoint, log to crash log
        timeout 10 python3 "$ENGINE" write_crash_log \
            "$command" "-1" "0" "90" "" "TIMING_DANGER: Timeout proximity >= 80" >/dev/null 2>&1
        echo "🛑 TIMING BLOCK: Command blocked by timing guard. EEF is too high."
        echo "   Fragment this operation into smaller steps and retry."
        echo "   Run: python3 /root/NeuralCline/lib/timing_metrics.py read_timing"
        return 1
    fi

    # 🧬 Step 1.75: Self-learning organism heal + snapshot (NEW)
    # Runs foresee + self-heal before every command to maintain predictive memory
    local heal_result
    heal_result=$(timeout 10 python3 "$SELF_LEARNING" heal "$command" 2>&1)
    local heal_recs=$(echo "$heal_result" | grep "^HEALING_RECOMMENDATIONS=" | cut -d= -f2)
    local org_gen=$(echo "$heal_result" | grep "^ORGANISM_GENERATION=" | cut -d= -f2)
    local patterns=$(echo "$heal_result" | grep "^LEARNED_PATTERNS=" | cut -d= -f2)

    echo "ORGANISM_GENERATION=${org_gen:-1}"
    echo "LEARNED_PATTERNS=${patterns:-0}"
    echo "HEALING_RECOMMENDATIONS=${heal_recs:-0}"

    # Print any high-risk recommendations
    if [ "${heal_recs:-0}" -gt 0 ] 2>/dev/null; then
        echo "🧬  SELF-LEARNING ORGANISM: ${heal_recs} recommendation(s) active"
        local i=1
        while [ "$i" -le "${heal_recs}" ] 2>/dev/null; do
            local rec_message=$(echo "$heal_result" | grep "^REC_${i}_MESSAGE=" | cut -d= -f2-)
            local rec_action=$(echo "$heal_result" | grep "^REC_${i}_ACTION=" | cut -d= -f2-)
            local rec_risk=$(echo "$heal_result" | grep "^REC_${i}_RISK=" | cut -d= -f2)
            if [ -n "$rec_message" ] && [ "$rec_risk" -ge 80 ] 2>/dev/null; then
                echo "   🔴 [${rec_risk}/100] ${rec_message}"
                echo "   → ${rec_action}"
            elif [ -n "$rec_message" ] && [ "$rec_risk" -ge 60 ] 2>/dev/null; then
                echo "   🟡 [${rec_risk}/100] ${rec_message}"
            fi
            i=$((i + 1))
        done
    fi

    # ── Step 2: Compute crash proximity via state_engine.py ──
    local result
    result=$(timeout 10 python3 "$ENGINE" compute_proximity "$command" 2>&1)
    local proximity=$(echo "$result" | grep "^CRASH_PROXIMITY=" | cut -d= -f2)
    local pattern=$(echo "$result" | grep "^MATCHED_PATTERN=" | cut -d= -f2)
    local ctx=$(echo "$result" | grep "^CONTEXT_USAGE=" | cut -d= -f2)
    local eef=$(echo "$result" | grep "^EEF=" | cut -d= -f2)
    local timeout_prox=$(echo "$result" | grep "^TIMEOUT_PROXIMITY=" | cut -d= -f2)

    # Fallback: if CRASH_PROXIMITY not found, try the old PROXIMITY key
    if [ -z "$proximity" ]; then
        proximity=$(echo "$result" | grep "^PROXIMITY=" | cut -d= -f2)
    fi

    echo "CRASH_PROXIMITY=$proximity"
    echo "MATCHED_PATTERN=$pattern"
    echo "CONTEXT_USAGE=$ctx"
    echo "EEF=${eef:-N/A}"
    echo "TIMEOUT_PROXIMITY=${timeout_prox:-N/A}"

    if [ "$proximity" -gt 80 ] 2>/dev/null; then
        echo "⚠️  CRASH DANGER: Crash proximity score is $proximity (threshold: 80)"
        echo "   Matched failure pattern: $pattern"
        [ -n "$eef" ] && echo "   EEF=$eef | Timeout proximity=${timeout_prox:-?}/100"
        echo "   Auto-saving checkpoint..."
        timeout 10 python3 "$ENGINE" generate_checkpoint >/dev/null 2>&1
    elif [ "$proximity" -gt 60 ] 2>/dev/null; then
        echo "⚠️  CRASH WARNING: Crash proximity score is $proximity (threshold: 60)"
        echo "   Matched failure pattern: $pattern"
        [ -n "$eef" ] && echo "   EEF=$eef | Timeout proximity=${timeout_prox:-?}/100"
        echo "   Auto-saving checkpoint..."
        timeout 10 python3 "$ENGINE" generate_checkpoint >/dev/null 2>&1
    elif [ "$proximity" -gt 30 ] 2>/dev/null; then
        echo "ℹ️  CRASH CAUTION: Crash proximity score is $proximity"
        echo "   Consider paginating output or truncating."
    else
        echo "✅ CRASH SAFE: Crash proximity score is ${proximity:-0}"
    fi
}

main "$@"
