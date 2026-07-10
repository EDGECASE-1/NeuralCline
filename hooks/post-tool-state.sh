#!/bin/bash
# =============================================================================
# 📝 POST-TOOL STATE — NeuralCline EDGECASE
# =============================================================================
# Uses state_engine.py and timing_metrics.py for ALL JSON operations — no
# inline python3 -c. This prevents the shell integration timeout crash.
#
# Usage: bash /root/NeuralCline/hooks/post-tool-state.sh <command> <exit_code> <output_size> <proximity> <duration_ms> [file_scope] [error_msg]
# =============================================================================

ENGINE="/root/NeuralCline/lib/state_engine.py"
TIMING_ENGINE="/root/NeuralCline/lib/timing_metrics.py"
SELF_LEARNING="/root/NeuralCline/lib/self_learning.py"
SESSION_DIR="/root/.session-state"

# ⏱️ Record execution timing to the timing metrics engine (NEW)
record_timing() {
    local command="${1:-}"
    local exit_code="${2:-0}"
    local output_size="${3:-0}"
    local duration_ms="${4:-0}"

    # Record execution duration to build the EEF model
    # This feeds the rolling average, pattern history, and timeout proximity
    if [ -n "$command" ] && [ "$duration_ms" -gt 0 ] 2>/dev/null; then
        timeout 10 python3 "$TIMING_ENGINE" record_execution \
            "$command" "$duration_ms" "$exit_code" "$output_size" 2>&1
    fi
}

main() {
    local command="${1:-}"
    local exit_code="${2:-0}"
    local output_size="${3:-0}"
    local proximity="${4:-0}"
    local duration_ms="${5:-0}"       # NEW: execution duration in milliseconds
    local file_scope="${6:-}"
    local error_msg="${7:-}"

    # ⏱️ Step 0: Record execution timing FIRST (before state update)
    # This feeds the Execution Emulation Factor (EEF) model
    record_timing "$command" "$exit_code" "$output_size" "$duration_ms"

    # 🧬 Step 0.5: Self-learning organism snapshot (NEW)
    # Records a memory snapshot of all parameters for future foresight
    timeout 10 python3 "$SELF_LEARNING" snapshot >/dev/null 2>&1

    # All operations through state_engine.py — no inline python3 -c anywhere
    timeout 15 python3 "$ENGINE" update_state \
        "$command" "$exit_code" "$output_size" "$proximity" "$file_scope" 2>&1

    timeout 15 python3 "$ENGINE" write_crash_log \
        "$command" "$exit_code" "$output_size" "$proximity" "$file_scope" "$error_msg" 2>&1

    timeout 30 python3 "$ENGINE" update_failure_points 2>&1

    timeout 10 python3 "$ENGINE" generate_checkpoint 2>&1
}

main "$@"
