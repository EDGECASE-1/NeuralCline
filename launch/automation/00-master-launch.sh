#!/bin/bash
# =============================================================================
# NeuralCline — MASTER LAUNCH ENGINE
# =============================================================================
# Complete one-command launch: runs all injection scripts in sequence.
# Covers GitHub-native + external platform surfaces.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="/root/NeuralCline/launch/automation"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     🚀 NEURALCLINE MASTER LAUNCH ENGINE                    ║"
echo "║     Complete pipeline — all injection vectors              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# =============================================================================
# PHASE 1: GitHub-Native Injection
# =============================================================================
echo "═════════════════════════════════════════════════════════════════"
echo "  PHASE 1: GitHub-Native Injection"
echo "═════════════════════════════════════════════════════════════════"
echo ""

# 1a. Create GitHub Discussion
echo "▶️ 1a. GitHub Discussion..."
bash "$SCRIPT_DIR/01-create-discussion.sh" 2>&1 || echo "   ⚠️ Skipped (may already exist)"

# 1b. Launch Orchestrator (Issues + Pages + Announcements)
echo "▶️ 1b. GitHub Issues + Pages..."
bash "$SCRIPT_DIR/02-launch-orchestrator.sh" 2>&1 || echo "   ⚠️ Skipped (may already exist)"

# 1c. External platform content (Issues with copy-paste content)
echo "▶️ 1c. External Platform Content Issues..."
bash "$SCRIPT_DIR/03-external-launch.sh" 2>&1 || echo "   ⚠️ Skipped (may already exist)"

# 1d. Gist Injection (3 public gists)
echo "▶️ 1d. Gist Injection (Reddit/HN whitelisted URLs)..."
bash "$SCRIPT_DIR/05-gist-injection.sh" 2>&1 || echo "   ⚠️ Skipped (may already exist)"

# 1e. Release + Topics + Project Board
echo "▶️ 1e. Release + Topics + Project Board..."
bash "$SCRIPT_DIR/06-release-injection.sh" 2>&1 || echo "   ⚠️ Skipped (may already exist)"

echo ""

# =============================================================================
# PHASE 2: External Platform Injection
# =============================================================================
echo "═════════════════════════════════════════════════════════════════"
echo "  PHASE 2: External Platform Injection"
echo "═════════════════════════════════════════════════════════════════"
echo ""

# 2a. Dev.to Syndication
echo "▶️ 2a. Dev.to Syndication..."
bash "$SCRIPT_DIR/07-devto-syndicate.sh" 2>&1 || echo "   ⚠️ Skipped (DEVTO_API_KEY not set)"

echo ""

# =============================================================================
# PHASE 3: Metrics + Verification
# =============================================================================
echo "═════════════════════════════════════════════════════════════════"
echo "  PHASE 3: Metrics Dashboard"
echo "═════════════════════════════════════════════════════════════════"
echo ""

# 3a. Check metrics
bash "$SCRIPT_DIR/04-check-metrics.sh" 2>&1 || true

echo ""

# =============================================================================
# SUMMARY
# =============================================================================
echo "═════════════════════════════════════════════════════════════════"
echo "  MASTER LAUNCH COMPLETE"
echo "═════════════════════════════════════════════════════════════════"
echo ""
echo "📌 All injection points:"
echo ""
echo "  GitHub-Native (via gh CLI):"
echo "  ├── Discussion:   https://github.com/EDGECASE-1/NeuralCline/discussions/2"
echo "  ├── Pages:        https://edgecase-1.github.io/NeuralCline/"
echo "  ├── Issues:       https://github.com/EDGECASE-1/NeuralCline/issues"
echo "  ├── Release:      https://github.com/EDGECASE-1/NeuralCline/releases/tag/v1.0.1"
echo "  ├── Gist (Launch): cat /root/.session-state/last-gist-url.txt"
echo "  ├── Gist (Install): cat /root/.session-state/last-install-gist-url.txt"
echo "  └── Topics:       agentic-ai, ai-agents, cline, crash-recovery, ..."
echo ""
echo "  External (via API):"
echo "  ├── Dev.to:       cat /root/.session-state/last-devto-url.txt"
echo "  └── Reddit/HN/PH: Copy content from Issues #6, #7, #8"
echo ""
echo "  Automated (via GitHub Actions):"
echo "  └── .github/workflows/syndication.yml — runs every 6h"
echo ""
echo "  Strategic visibility:"
echo "  ├── INJECTION_MAP.md — Full API surface + agency feeds"
echo "  └── Critical path: Stars → GitHub Trending → HN → TechCrunch → Agency radar"
echo ""
echo "📌 To check metrics anytime:"
echo "  bash /root/NeuralCline/launch/automation/04-check-metrics.sh"
echo ""
echo "📌 To post to Dev.to (once API key obtained):"
echo "  export DEVTO_API_KEY='your_key'"
echo "  bash /root/NeuralCline/launch/automation/07-devto-syndicate.sh"