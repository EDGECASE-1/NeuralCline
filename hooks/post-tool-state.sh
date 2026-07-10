#!/bin/bash
# =============================================================================
# 📝 POST-TOOL STATE — NeuralCline EDGECASE
# =============================================================================
# Uses state_engine.py for ALL JSON operations — no inline python3 -c.
# This prevents the shell integration timeout crash.
#
# Usage: bash /root/NeuralCline/hooks/post-tool-state.sh <command> <exit_code> <output_size> <proximity> [file_scope] [error_msg]
# =============================================================================

ENGINE="/root/NeuralCline/lib/state_engine.py"
SESSION_DIR="/root/.session-state"

main() {
    local command="${1:-}"
    local exit_code="${2:-0}"
    local output_size="${3:-0}"
    local proximity="${4:-0}"
    local file_scope="${5:-}"
    local error_msg="${6:-}"

    # All operations through state_engine.py — no inline python3 -c anywhere
    timeout 15 python3 "$ENGINE" update_state \
        "$command" "$exit_code" "$output_size" "$proximity" "$file_scope" 2>&1

    timeout 15 python3 "$ENGINE" write_crash_log \
        "$command" "$exit_code" "$output_size" "$proximity" "$file_scope" "$error_msg" 2>&1

    timeout 30 python3 "$ENGINE" update_failure_points 2>&1

    timeout 10 python3 "$ENGINE" generate_checkpoint 2>&1
}

main "$@"