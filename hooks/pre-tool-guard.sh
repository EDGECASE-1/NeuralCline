#!/bin/bash
# =============================================================================
# 🛡️ PRE-TOOL GUARD — NeuralCline EDGECASE
# =============================================================================
# Uses agentic_exec.py for ALL subprocess calls — never blocks the main thread.
# Any hung subprocess is killed by an OS-level SIGALRM watchdog.
#
# Usage: bash /root/NeuralCline/hooks/pre-tool-guard.sh "<command>"
# =============================================================================

AGENTIC="/root/NeuralCline/lib/agentic_exec.py"
ENGINE="/root/NeuralCline/lib/state_engine.py"
TIMING_ENGINE="/root/NeuralCline/lib/timing_metrics.py"
SELF_LEARNING="/root/NeuralCline/lib/self_learning.py"
SMART_PREFETCH="/root/NeuralCline/hooks/smart_prefetch.sh"
FRONTIER_ENGINE="/root/NeuralCline/lib/frontier_analyzer.py"
NERVOUS_SYSTEM="/root/NeuralCline/hooks/nervous_system_watchdog.sh"
SESSION_DIR="/root/.session-state"
STATE="$SESSION_DIR/current-state.json"
CHECKPOINT="$SESSION_DIR/checkpoint.json"
DIAGNOSE="/root/NeuralCline/hooks/diagnose.sh"

# ─── Spawn and forget — never wait for subprocesses ──────────────────────
spawn_detached() {
    # $1 = timeout_ms, $2+ = command and args
    # Returns PID. Caller never waits.
    local timeout_ms="$1"; shift
    python3 "$AGENTIC" spawn "$timeout_ms" "$@" 2>/dev/null || echo "0"
}

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

# 🔮 Step 1.6: Dynamic Frontier Recon — Smart Prefetch
# Runs before the self-learning organism to determine if the command
# needs to be fragmented into smaller safe chunks.
# Uses O(1) stat calls on identified files — never reads them fully.
check_frontier_recon() {
    local command="${1:-}"
    [ -z "$command" ] && return 0

    # Source the smart prefetch bridge
    if [ ! -f "$SMART_PREFETCH" ]; then
        return 0
    fi

    local frontier_report
    frontier_report=$(bash "$SMART_PREFETCH" "$command" 2>&1)
    local frontier_action=$(echo "$frontier_report" | grep "^FRONTIER_ACTION=" | cut -d= -f2-)
    local frontier_grade=$(echo "$frontier_report" | grep "^FRONTIER_GRADE=" | cut -d= -f2-)
    local frontier_should_fragment=$(echo "$frontier_report" | grep "^FRONTIER_SHOULD_FRAGMENT=" | cut -d= -f2-)
    local frontier_estimated_lines=$(echo "$frontier_report" | grep "^FRONTIER_ESTIMATED_LINES=" | cut -d= -f2-)
    local frontier_estimated_duration_ms=$(echo "$frontier_report" | grep "^FRONTIER_ESTIMATED_DURATION_MS=" | cut -d= -f2-)
    local frontier_safe_max_lines=$(echo "$frontier_report" | grep "^FRONTIER_SAFE_MAX_LINES=" | cut -d= -f2-)
    local frontier_pipe_count=$(echo "$frontier_report" | grep "^FRONTIER_PIPE_COUNT=" | cut -d= -f2-)
    local frontier_context=$(echo "$frontier_report" | grep "^FRONTIER_CONTEXT_USAGE=" | cut -d= -f2-)
    local frontier_total_size=$(echo "$frontier_report" | grep "^FRONTIER_TOTAL_SIZE_BYTES=" | cut -d= -f2-)
    local frontier_risks=$(echo "$frontier_report" | grep "^FRONTIER_RISKS=" | cut -d= -f2-)
    local frontier_plan=$(echo "$frontier_report" | grep "^FRONTIER_FRAGMENTATION_PLAN=" | cut -d= -f2-)

    # Emit the recon summary
    echo "FRONTIER_GRADE=${frontier_grade:-unknown}"
    echo "FRONTIER_ESTIMATED_LINES=${frontier_estimated_lines:-0}"
    echo "FRONTIER_ESTIMATED_DURATION_MS=${frontier_estimated_duration_ms:-0}"
    echo "FRONTIER_SAFE_MAX_LINES=${frontier_safe_max_lines:-1000}"
    echo "FRONTIER_PIPE_COUNT=${frontier_pipe_count:-0}"
    echo "FRONTIER_CONTEXT_USAGE=${frontier_context:-0}"
    echo "FRONTIER_TOTAL_SIZE_BYTES=${frontier_total_size:-0}"

    # Check for risk warnings
    if [ -n "$frontier_risks" ]; then
        echo "⚠️  FRONTIER WARNINGS: $(echo "$frontier_risks" | tr ';' '\n  - ')"
    fi

    # Apply frontier-based actions
    if [ "$frontier_action" = "block" ]; then
        echo "🚫 FRONTIER BLOCK: Context usage is ${frontier_context}% — too dangerous to execute"
        echo "   Generate a handoff and checkpoint before retrying."
        timeout 10 python3 "$ENGINE" generate_checkpoint >/dev/null 2>&1
        return 1
    fi

    if [ "$frontier_should_fragment" = "1" ] && [ -n "$frontier_plan" ]; then
        echo "🔀 FRONTIER SUGGESTS FRAGMENTATION: Grade=$frontier_grade, Lines=${frontier_estimated_lines}, Duration=${frontier_estimated_duration_ms}ms"
        echo "   Safe max lines: $frontier_safe_max_lines"
        echo "   Fragmentation plan available. Consider pipelining through head -${frontier_safe_max_lines:-500}."
        # Export the plan for the caller
        export FRONTIER_FRAGMENTATION_PLAN="$frontier_plan"
        export FRONTIER_SHOULD_FRAGMENT="1"
        export FRONTIER_SAFE_MAX_LINES="${frontier_safe_max_lines:-500}"
        echo "FRONTIER_FRAGMENTATION_PLAN=${frontier_plan}"
        echo "FRONTIER_SHOULD_FRAGMENT=1"
    elif [ "$frontier_grade" = "large" ] || [ "$frontier_grade" = "extreme" ]; then
        # Grade is high but no plan — just warn about output size
        echo "🔊 FRONTIER WARNING: Grade=$frontier_grade, estimated ${frontier_estimated_lines} lines"
        echo "   Consider adding '| head -${frontier_safe_max_lines:-500}' to paginate output."
    else
        echo "✅ FRONTIER SAFE: Grade=$frontier_grade, ${frontier_estimated_lines} lines, ${frontier_estimated_duration_ms}ms"
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

    # 🧬 Step 1.55: Nervous System Watchdog — Consciousness + Mesh Check (NEW)
    # Runs BEFORE frontier recon to ensure the system can safely execute.
    # Self-choking threat detection + compute ceiling enforcement.
    if [ -f "$NERVOUS_SYSTEM" ]; then
        local nervous_result
        nervous_result=$(bash "$NERVOUS_SYSTEM" check "$command" 2>&1)
        local consciousness_action=$(echo "$nervous_result" | grep "^CONSCIOUSNESS_ACTION=" | cut -d= -f2-)
        local consciousness_threat=$(echo "$nervous_result" | grep "^CONSCIOUSNESS_THREAT=" | cut -d= -f2-)
        local consciousness_ram=$(echo "$nervous_result" | grep "^CONSCIOUSNESS_RAM_PCT=" | cut -d= -f2-)
        local consciousness_cpu=$(echo "$nervous_result" | grep "^CONSCIOUSNESS_CPU_SAT_PCT=" | cut -d= -f2-)
        local consciousness_disk=$(echo "$nervous_result" | grep "^CONSCIOUSNESS_DISK_PCT=" | cut -d= -f2-)
        local consciousness_mesh=$(echo "$nervous_result" | grep "^CONSCIOUSNESS_MESH_READY=" | cut -d= -f2-)
        local consciousness_tensor=$(echo "$nervous_result" | grep "^CONSCIOUSNESS_TENSOR_MEMORY_KB=" | cut -d= -f2-)
        local consciousness_context=$(echo "$nervous_result" | grep "^CONSCIOUSNESS_CONTEXT_PCT=" | cut -d= -f2-)

        echo "CONSCIOUSNESS_RAM=${consciousness_ram}%"
        echo "CONSCIOUSNESS_CPU=${consciousness_cpu}%"
        echo "CONSCIOUSNESS_DISK=${consciousness_disk}%"
        echo "CONSCIOUSNESS_THREAT=${consciousness_threat}"
        echo "CONSCIOUSNESS_TENSOR_MEMORY=${consciousness_tensor}KB"
        echo "CONSCIOUSNESS_MESH_READY=${consciousness_mesh}"
        echo "CONSCIOUSNESS_CONTEXT=${consciousness_context}%"

        if [ "$consciousness_action" = "block" ]; then
            echo "🚨 CONSCIOUSNESS BLOCK: System at critical threat level"
            echo "   RAM=${consciousness_ram}% CPU=${consciousness_cpu}% Disk=${consciousness_disk}%"
            echo "   Cannot safely execute. Generate handoff."
            timeout 10 python3 "$ENGINE" generate_checkpoint >/dev/null 2>&1
            return 1
        fi

        if [ "$consciousness_action" = "offload" ] && [ "$consciousness_mesh" = "1" ]; then
            local allocated_to=$(echo "$nervous_result" | grep "^CONSCIOUSNESS_ALLOCATED_TO=" | cut -d= -f2-)
            echo "🔀 CONSCIOUSNESS OFFLOAD: Command routed to mesh peer $allocated_to"
            echo "   Local capacity insufficient. Offloading."
        fi

        if [ "$consciousness_action" = "throttle" ]; then
            echo "⚠️  CONSCIOUSNESS THROTTLE: Reducing operation size"
            echo "   RAM=${consciousness_ram}% CPU=${consciousness_cpu}% Threat=${consciousness_threat}"
            echo "   Auto-saving checkpoint before proceeding..."
            timeout 10 python3 "$ENGINE" generate_checkpoint >/dev/null 2>&1
        fi

        # Export consciousness context for the rest of the pipeline
        export CONSCIOUSNESS_ACTION="$consciousness_action"
        export CONSCIOUSNESS_THREAT="$consciousness_threat"
        export CONSCIOUSNESS_RAM_PCT="$consciousness_ram"
        export CONSCIOUSNESS_CPU_SAT_PCT="$consciousness_cpu"
    fi

    # 🔮 Step 1.6: Dynamic Frontier Recon — Smart Prefetch
    # Does O(1) stat calls on files in the command, grades size/complexity,
    # estimates duration, and suggests fragmentation if over threshold.
    # This runs BEFORE the self-learning organism so the organism can learn
    # from the frontier analysis as well.
    if ! check_frontier_recon "$command"; then
        # Frontier block — context too high, generate handoff
        echo "🛑 FRONTIER BLOCK: Command blocked by frontier recon guard."
        echo "   Context usage is critically high. Generate handoff and retry."
        return 1
    fi

    # 🧬 Step 1.75: Self-learning organism heal + snapshot
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
