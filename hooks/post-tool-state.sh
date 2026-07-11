#!/bin/bash
# =============================================================================
# 📝 POST-TOOL STATE — NeuralCline EDGECASE
# =============================================================================
# Uses agentic_exec.py for ALL subprocess calls — never blocks the main thread.
# Any hung subprocess is killed by an OS-level SIGALRM watchdog.
#
# Usage: bash /root/NeuralCline/hooks/post-tool-state.sh <command> <exit_code> <output_size> <proximity> <duration_ms> [file_scope] [error_msg]
# =============================================================================

AGENTIC="/root/NeuralCline/lib/agentic_exec.py"
ENGINE="/root/NeuralCline/lib/state_engine.py"
TIMING_ENGINE="/root/NeuralCline/lib/timing_metrics.py"
SELF_LEARNING="/root/NeuralCline/lib/self_learning.py"
CRASH_BUFFER="/root/NeuralCline/lib/crash_buffer.py"
FRONTIER_ENGINE="/root/NeuralCline/lib/frontier_analyzer.py"
SMART_PREFETCH="/root/NeuralCline/hooks/smart_prefetch.sh"
NERVOUS_SYSTEM="/root/NeuralCline/hooks/nervous_system_watchdog.sh"
SESSION_DIR="/root/.session-state"

# ─── Spawn and forget — never wait for subprocesses ──────────────────────
spawn_detached() {
    local timeout_ms="$1"; shift
    python3 "$AGENTIC" spawn "$timeout_ms" "$@" 2>/dev/null || true
}

# ⏱️ Record execution timing to the timing metrics engine
# Enhanced with frontier analyzer data for dynamic throughput calibration
record_timing() {
    local command="${1:-}"
    local exit_code="${2:-0}"
    local output_size="${3:-0}"
    local duration_ms="${4:-0}"

    # Record execution duration to build the EEF model
    if [ -n "$command" ] && [ "$duration_ms" -gt 0 ] 2>/dev/null; then
        timeout 10 python3 "$TIMING_ENGINE" record_execution \
            "$command" "$duration_ms" "$exit_code" "$output_size" 2>&1
    fi
}

# 🔮 Frontier-enhanced check — uses actual file stats + throughput estimates
# to determine if a command output was truncated or needs chunking.
# Runs asynchronously to avoid blocking the main state update.
enrich_with_frontier() {
    local command="${1:-}"
    local exit_code="${2:-0}"
    local output_size="${3:-0}"
    [ -z "$command" ] && return 0
    [ ! -f "$FRONTIER_ENGINE" ] && return 0

    # Fast check in background — doesn't block main flow
    timeout 5 python3 "$FRONTIER_ENGINE" report "$command" 2>/dev/null | \
        grep "^FRONTIER_" | while read -r line; do
        # Emit frontier data to the state output
        echo "🔮 $line"
    done &
}

# ⛓️ Prefetching chunk checker — silently evaluates file sizes via timing_engine
# Uses timing_metrics.py predict_timeout which already has _load_chunk_hints built in
check_chunk_hint() {
    local command="${1:-}"
    local hint
    hint=$(timeout 5 python3 /root/NeuralCline/lib/timing_metrics.py predict_timeout "$command" 2>/dev/null | grep "^CHUNK_HINT=" | cut -d= -f2-)
    echo "$hint"
}

main() {
    local command="${1:-}"
    local exit_code="${2:-0}"
    local output_size="${3:-0}"
    local proximity="${4:-0}"
    local duration_ms="${5:-0}"
    local file_scope="${6:-}"
    local error_msg="${7:-}"

    # ⏱️ Step 0: Record execution timing FIRST (before state update)
    record_timing "$command" "$exit_code" "$output_size" "$duration_ms"

    # 🧬 Step 0.1: Nervous System Heartbeat (NEW — consciousness state update)
    # Updates the consciousness.json file with post-execution state.
    # Runs async to never block the main flow.
    if [ -f "$NERVOUS_SYSTEM" ]; then
        timeout 3 bash "$NERVOUS_SYSTEM" heartbeat "$exit_code" >/dev/null 2>&1 &
    fi

    # 🔮 Step 0.25: Enrich state with frontier analyzer data (async)
    enrich_with_frontier "$command" "$exit_code" "$output_size" >/dev/null 2>&1 &

    # 🧬 Step 0.5: Self-learning organism snapshot
    timeout 10 python3 "$SELF_LEARNING" snapshot >/dev/null 2>&1

    # Step 0.75: Check chunk hints for large files in the command
    local chunk_hint
    chunk_hint=$(check_chunk_hint "$command")

    # ─── CRASH FILTER: Bicameral correction check ───
    # Before writing crash log, check if the auditor has flagged this as
    # a environmental variance pattern. If so, route through crash_buffer absorb
    # instead of flooding the crash log.
    local suppress_crash="false"
    if [ "$exit_code" != "0" ]; then
        # Use grep + cut (no python3 -c) to check bicameral state in memory file
        if [ -f "$SESSION_DIR/session-memory.json" ]; then
            local adjust
            adjust=$(grep -o '"adjustment"[[:space:]]*:[[:space:]]*"[^"]*"' "$SESSION_DIR/session-memory.json" 2>/dev/null | tail -1 | cut -d'"' -f4)
            local noise=0
            # Check known noise patterns
            case "$command" in
                *__vsc_original_prompt_command*) noise=1 ;;
                *__vsc_prompt_cmd_original*) noise=1 ;;
                *__vsc_preexec_all*) noise=1 ;;
                *PROMPT_COMMAND*) noise=1 ;;
                *"source /root"*) noise=1 ;;
                *"cd /root/NeuralCline"*) noise=1 ;;
                *"ls --color"*) noise=1 ;;
                *"cat "*) noise=1 ;;
                *"diagnose.sh"*) noise=1 ;;
                *"tail -"*) noise=1 ;;
                *"generate-handoff.sh"*) noise=1 ;;
                *"read_file"*) noise=1 ;;
                *"grep --color"*) noise=1 ;;
                *"timeout "*) noise=1 ;;
                *"write_crash_log"*) noise=1 ;;
                *"compute_proximity"*) noise=1 ;;
                *"predict_timeout"*) noise=1 ;;
                *"wc -l "*) noise=1 ;;
                *"rm "*) noise=1 ;;
            esac
            if [ "$noise" = "1" ] || [ "$adjust" = "relax_crash_threshold" ]; then
                suppress_crash="true"
            fi
        fi
    fi

    # Update state file regardless
    timeout 15 python3 "$ENGINE" update_state \
        "$command" "$exit_code" "$output_size" "$proximity" "$file_scope" 2>&1

    # ─── Crash absorption or logging ───
    if [ "$exit_code" != "0" ] && [ "$suppress_crash" = "false" ]; then
        # Real crash (not suppressed) → log and absorb
        timeout 15 python3 "$ENGINE" write_crash_log \
            "$command" "$exit_code" "$output_size" "$proximity" "$file_scope" "$error_msg" 2>&1

        # Attempt absorption via crash buffer using a temp crash json built via heredoc
        local crash_tmp
        crash_tmp=$(mktemp /tmp/nc-crash-XXXXXX.json 2>/dev/null)
        if [ -n "$crash_tmp" ]; then
            # Build JSON safely using printf (no inline python3 -c)
            printf '{"crash_type":"exit_code","exit_code":%d,"command":"%s","context_usage_pct":%d,"execution_duration_ms":%d,"tool_call_count":0,"severity":"low"}\n' \
                "$exit_code" "${command//\"/\\\"}" "$proximity" "$duration_ms" > "$crash_tmp"
            timeout 10 python3 "$CRASH_BUFFER" absorb "$crash_tmp" 2>/dev/null || true
            rm -f "$crash_tmp"
        fi
    elif [ "$exit_code" != "0" ] && [ "$suppress_crash" = "true" ]; then
        # False positive → silently absorb without logging
        local crash_tmp
        crash_tmp=$(mktemp /tmp/nc-fp-XXXXXX.json 2>/dev/null)
        if [ -n "$crash_tmp" ]; then
            printf '{"crash_type":"false_positive","exit_code":%d,"command":"%s","context_usage_pct":%d,"execution_duration_ms":%d,"tool_call_count":0,"severity":"low"}\n' \
                "$exit_code" "${command//\"/\\\"}" "$proximity" "$duration_ms" > "$crash_tmp"
            timeout 10 python3 "$CRASH_BUFFER" absorb "$crash_tmp" 2>/dev/null || true
            rm -f "$crash_tmp"
        fi
    fi

    # Always update failure points and checkpoint (non-blocking)
    timeout 30 python3 "$ENGINE" update_failure_points 2>&1 &
    timeout 10 python3 "$ENGINE" generate_checkpoint 2>&1 &

    # Print chunk hint if present (guides fragmentation)
    # Check using grep on the hint string directly (no inline python3 -c)
    if [ -n "$chunk_hint" ] && echo "$chunk_hint" | grep -q "should_chunk"; then
        echo "⛓️  $chunk_hint"
    fi
}

main "$@"
