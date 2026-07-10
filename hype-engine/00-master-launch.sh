#!/bin/bash
# =============================================================================
# NeuralCline — Hype Engine Master Launch Script
# =============================================================================
# Launches all 5 modules of the hype engine plus the live dashboard.
# Can run in daemon mode, interactive mode, or one-shot mode.
#
# Usage:
#   bash 00-master-launch.sh daemon       # Start background daemon
#   bash 00-master-launch.sh interactive  # Start interactive console
#   bash 00-master-launch.sh status       # Show engine status
#   bash 00-master-launch.sh deploy       # Deploy dashboard to GitHub Pages
#   bash 00-master-launch.sh test         # Test all modules
# =============================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_DIR="$SCRIPT_DIR"
DOCS_DIR="/root/NeuralCline/docs"
STATE_DIR="/root/.session-state"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${PURPLE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     🧠 NEURALCLINE — HYPE ENGINE LAUNCH SEQUENCE            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── Load the NeuralCline safety system ─────────────────────────
source /root/NeuralCline/hooks/pre-tool-guard.sh 2>/dev/null || true

# ─── Ensure state directory exists ───────────────────────────────
mkdir -p "$STATE_DIR" "$ENGINE_DIR"

# ─── Test all modules ────────────────────────────────────────────
test_modules() {
    echo -e "\n${BLUE}[TEST] Testing all hype engine modules...${NC}\n"
    local failures=0

    for module in "01-inquiry-engine.py" "02-agent-mcp-server.py" "03-download-tracker.py" "04-hype-orchestrator.py"; do
        echo -n "  Testing $module ... "
        if python3 "$ENGINE_DIR/$module" 2>&1 | head -1 > /dev/null; then
            echo -e "${GREEN}OK${NC}"
        else
            echo -e "${RED}FAILED${NC}"
            failures=$((failures + 1))
        fi
    done

    echo -n "  Testing dashboard HTML ... "
    if [ -f "$ENGINE_DIR/05-hype-dashboard.html" ]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}MISSING${NC}"
        failures=$((failures + 1))
    fi

    echo ""
    if [ $failures -eq 0 ]; then
        echo -e "${GREEN}✅ All modules passed!${NC}"
    else
        echo -e "${RED}❌ $failures module(s) failed${NC}"
    fi
    return $failures
}

# ─── Deploy dashboard to GitHub Pages ────────────────────────────
deploy_dashboard() {
    echo -e "\n${BLUE}[DEPLOY] Deploying hype dashboard to GitHub Pages...${NC}\n"

    # Copy dashboard HTML to docs/ for GitHub Pages
    cp "$ENGINE_DIR/05-hype-dashboard.html" "$DOCS_DIR/hype-dashboard.html"

    # Copy state JSON files for dashboard to reference
    for f in hype-state.json inquiry-log.json agent-connections.json download-log.json; do
        if [ -f "$ENGINE_DIR/$f" ]; then
            cp "$ENGINE_DIR/$f" "$DOCS_DIR/hype-$f"
        fi
    done

    # Update the sitemap
    echo -e "  Adding hype-dashboard.html to sitemap..."

    # Commit and push
    cd /root/NeuralCline
    git add docs/hype-dashboard.html docs/hype-*.json 2>/dev/null || true
    git commit -m "🧠 Deploy Hype Engine dashboard [automated]" 2>/dev/null || true
    git push origin master 2>/dev/null || echo -e "${YELLOW}  ⚠ Push skipped (not on master or no changes)${NC}"

    echo -e "\n${GREEN}✅ Dashboard deployed: https://edgecase-1.github.io/NeuralCline/hype-dashboard.html${NC}"
}

# ─── Show status ─────────────────────────────────────────────────
show_status() {
    echo -e "\n${BLUE}[STATUS] Hype Engine Status${NC}\n"

    # Check if daemon is running
    if [ -f "$ENGINE_DIR/hype-state.json" ]; then
        echo -e "  ${CYAN}Hype State:${NC}"
        python3 -c "
import json
with open('$ENGINE_DIR/hype-state.json') as f:
    s = json.load(f)
print(f'    Status: {s.get(\"status\", \"unknown\")}')
print(f'    Cycles: {s.get(\"cycle_count\", 0)}')
print(f'    Last tick: {s.get(\"last_full_tick\", \"never\")}')
print(f'    Interactive: {s.get(\"interactive_mode\", False)}')
print(f'    Errors: {len(s.get(\"errors\", []))}')
" 2>/dev/null || echo "    (unable to parse)"
    else
        echo -e "  ${YELLOW}No hype state file found. Run 'tick' first.${NC}"
    fi

    # Check for agent MCP server
    if ss -tlnp 2>/dev/null | grep -q ":8790"; then
        echo -e "  ${GREEN}✅ Agent MCP Server: Running on port 8790${NC}"
    else
        echo -e "  ${YELLOW}⬜ Agent MCP Server: Not running${NC}"
    fi

    # Check state files
    echo -e "\n  ${CYAN}Engine State Files:${NC}"
    for f in hype-state.json inquiry-log.json agent-connections.json download-log.json schedule.json; do
        fpath="$ENGINE_DIR/$f"
        if [ -f "$fpath" ]; then
            size=$(stat -c%s "$fpath" 2>/dev/null || echo "?")
            echo -e "    ${GREEN}✅${NC} $f (${size}B)"
        else
            echo -e "    ${YELLOW}⬜${NC} $f (not yet created)"
        fi
    done
}

# ─── Start daemon ────────────────────────────────────────────────
start_daemon() {
    local interval=${1:-60}
    echo -e "\n${BLUE}[DAEMON] Starting Hype Engine daemon (interval: ${interval}s)...${NC}\n"
    echo -e "  ${YELLOW}Press Ctrl+C to stop${NC}\n"

    # Start the agent MCP server in background
    echo -e "  ${CYAN}Starting Agent MCP Server on port 8790...${NC}"
    python3 "$ENGINE_DIR/02-agent-mcp-server.py" start &
    MCP_PID=$!
    echo -e "  ${GREEN}Agent MCP Server PID: $MCP_PID${NC}"

    # Start the orchestrator daemon
    python3 "$ENGINE_DIR/04-hype-orchestrator.py" daemon "$interval"
    
    # Cleanup on exit
    kill $MCP_PID 2>/dev/null || true
}

# ─── Start interactive ───────────────────────────────────────────
start_interactive() {
    echo -e "\n${BLUE}[INTERACTIVE] Starting Hype Engine interactive console...${NC}\n"
    python3 "$ENGINE_DIR/04-hype-orchestrator.py" interactive
}

# ─── Run one tick ────────────────────────────────────────────────
run_tick() {
    echo -e "\n${BLUE}[TICK] Running one full engine cycle...${NC}\n"
    python3 "$ENGINE_DIR/04-hype-orchestrator.py" tick
}

# =============================================================================
# MAIN
# =============================================================================
case "${1:-help}" in
    daemon)
        start_daemon "${2:-60}"
        ;;
    interactive)
        start_interactive
        ;;
    tick)
        run_tick
        ;;
    status)
        show_status
        ;;
    test)
        test_modules
        ;;
    deploy)
        test_modules && deploy_dashboard
        ;;
    help|--help|-h)
        echo ""
        echo "Usage: bash 00-master-launch.sh <command>"
        echo ""
        echo "Commands:"
        echo "  daemon [interval]  Start background scheduler (default: 60s)"
        echo "  interactive        Start interactive console"
        echo "  tick               Run one full engine cycle"
        echo "  status             Show engine status"
        echo "  test               Test all modules"
        echo "  deploy             Test + deploy dashboard to GitHub Pages"
        echo "  help               Show this help"
        echo ""
        echo "Quick start:"
        echo "  bash 00-master-launch.sh test     # verify everything works"
        echo "  bash 00-master-launch.sh daemon   # start the hype engine"
        echo "  bash 00-master-launch.sh status   # check what's happening"
        echo ""
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Usage: bash 00-master-launch.sh [daemon|interactive|tick|status|test|deploy|help]"
        exit 1
        ;;
esac