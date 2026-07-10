#!/bin/bash
# =============================================================================
# 🎯 SESSION HANDOFF GENERATOR — NeuralCline EDGECASE
# =============================================================================
# Uses state_engine.py for all operations — no inline python3 -c.
#
# Usage: bash /root/NeuralCline/hooks/generate-handoff.sh
# Output: /root/.session-state/checkpoint.json
# =============================================================================

ENGINE="/root/NeuralCline/lib/state_engine.py"

main() {
    echo "NeuralCline :: Generating session handoff..."
    timeout 15 python3 "$ENGINE" generate_checkpoint 2>&1
    echo "Done. Checkpoint saved to /root/.session-state/checkpoint.json"
    echo "To restore this session, run: source /root/rehydration.md"
}

main "$@"