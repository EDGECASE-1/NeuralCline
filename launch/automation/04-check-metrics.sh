#!/bin/bash
# =============================================================================
# NeuralCline Launch Metrics Checker
# =============================================================================
# Real-time dashboard for launch performance across all channels.
# =============================================================================

set -euo pipefail

REPO="EDGECASE-1/NeuralCline"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     📊 NEURALCLINE LAUNCH METRICS DASHBOARD                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# GitHub Stars
echo "★ GitHub Stats:"
STARS=$(gh api repos/$REPO | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['stargazers_count'])")
FORKS=$(gh api repos/$REPO | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['forks_count'])")
WATCHERS=$(gh api repos/$REPO | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['subscribers_count'])")
echo "   Stars:    $STARS"
echo "   Forks:    $FORKS"
echo "   Watchers: $WATCHERS"
echo ""

# Discussion Comments
echo "💬 Discussion Activity:"
gh api graphql -f query="query { repository(owner:\"EDGECASE-1\", name:\"NeuralCline\") { discussion(number:2) { comments { totalCount } } } }" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   Comments: {d[\"data\"][\"repository\"][\"discussion\"][\"comments\"][\"totalCount\"]}')" 2>/dev/null || echo "   Comments: ?"

# Issue Count
echo "📋 Open Issues:"
gh issue list --repo $REPO --state open --json number,title --limit 10 2>/dev/null | python3 -c "
import sys,json
issues = json.load(sys.stdin)
for i in issues:
    print(f'   #{i[\"number\"]}: {i[\"title\"][:60]}')
print(f'   Total: {len(issues)} open')
" 2>/dev/null || echo "   (No issues)"

echo ""

# Install Script Stats
echo "📦 Install Activity:"
if [ -f /root/.session-state/crash-log.ndjson ]; then
    LINES=$(wc -l < /root/.session-state/crash-log.ndjson)
    echo "   Crash log entries: $LINES"
else
    echo "   No install data yet"
fi

echo ""

# Timing Metrics
echo "⏱️ Timing Metrics:"
python3 /root/NeuralCline/lib/timing_metrics.py read_timing 2>/dev/null || echo "   Not available"

echo ""

# Organism Health
echo "🧬 Self-Learning Organism:"
python3 /root/NeuralCline/lib/self_learning.py report 2>/dev/null | head -10 || echo "   Not available"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Run 'bash /root/NeuralCline/launch/automation/04-check-metrics.sh'  ║"
echo "║     any time to refresh this dashboard.                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"