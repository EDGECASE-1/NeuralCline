#!/bin/bash
# =============================================================================
# 🧠 NeuralCline — One-Command Installer
#   Codename: EDGECASE
#   Version:  1.0.0
#
#   curl -fsSL https://raw.githubusercontent.com/null-parse/NeuralCline/main/install.sh | bash
# =============================================================================

set -e

# ─── Color helpers ────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${CYAN}${BOLD}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}${BOLD}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}${BOLD}[WARN]${NC}  $1"; }
err()   { echo -e "${RED}${BOLD}[ERROR]${NC} $1"; }

# ─── Header ───────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}     ${BOLD}🧠 NeuralCline — Neural Session Safety System${NC}        ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     ${BOLD}Codename: EDGECASE  v1.0.0${NC}                          ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Determine install root ──────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"  # We're already inside the repo

# If running via curl|bash, REPO_ROOT will be /root/NeuralCline
# If running via git clone, REPO_ROOT will be wherever the script is

NC_DIR="/root/NeuralCline"
SESSION_DIR="/root/.session-state"
CLINE_DIR="/root/Cline"
CLINE_HOOKS="$CLINE_DIR/Hooks"
CLINE_RULES="$CLINE_DIR/Rules"
CLINERULES_FILE="/root/.clinerules"
BASHRC_FILE="/root/.bashrc"
AUTOINIT_FILE="$SESSION_DIR/auto-init.sh"
MASTER_PROFILE="/root/master_profile.md"
REHYDRATION_FILE="/root/rehydration.md"

# Cline globalState.json — auto-detect
GLOBAL_STATE=""
CANDIDATES=(
    "/root/.local/share/code-server/User/globalStorage/saoudrizwan.claude-dev/globalState.json"
    "/root/.config/Code/User/globalStorage/saoudrizwan.claude-dev/globalState.json"
    "/root/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/globalState.json"
    "/root/.config/Code - OSS/User/globalStorage/saoudrizwan.claude-dev/globalState.json"
)
for c in "${CANDIDATES[@]}"; do
    if [ -f "$c" ]; then
        GLOBAL_STATE="$c"
        break
    fi
done

# ─── Step 1: Deploy NeuralCline files ─────────────────────────────────────
info "Step 1/6: Deploying NeuralCline files..."

mkdir -p "$NC_DIR/lib" "$NC_DIR/hooks" "$NC_DIR/rules" "$NC_DIR/docs" "$NC_DIR/session-state"

# We need to either copy from the repo (if running locally) or embed
if [ -f "$REPO_ROOT/lib/state_engine.py" ]; then
    if [ "$REPO_ROOT" = "$NC_DIR" ]; then
        # Already deployed to the target location — just verify permissions
        info "  Files already at $NC_DIR — fixing permissions..."
        chmod 644 "$NC_DIR/lib/state_engine.py"
        chmod 755 "$NC_DIR/hooks/"*.sh
        chmod 644 "$NC_DIR/rules/"*.md
        chmod 755 "$NC_DIR/rehydration.md" 2>/dev/null || true
        chmod 644 "$NC_DIR/master_profile.md" 2>/dev/null || true
        chmod 644 "$NC_DIR/docs/MANIFEST.md" 2>/dev/null || true
    else
        # Running from a different repo clone — copy everything
        info "  Detected local repository at $REPO_ROOT — copying files..."

        cp "$REPO_ROOT/lib/state_engine.py" "$NC_DIR/lib/state_engine.py"
        chmod 644 "$NC_DIR/lib/state_engine.py"

        for hook in pre-tool-guard.sh post-tool-state.sh generate-handoff.sh diagnose.sh; do
            cp "$REPO_ROOT/hooks/$hook" "$NC_DIR/hooks/$hook"
            chmod 755 "$NC_DIR/hooks/$hook"
        done

        for rule in session-safety.md recovery-protocols.md; do
            cp "$REPO_ROOT/rules/$rule" "$NC_DIR/rules/$rule"
            chmod 644 "$NC_DIR/rules/$rule"
        done

        if [ -f "$REPO_ROOT/rehydration.md" ]; then
            cp "$REPO_ROOT/rehydration.md" "$NC_DIR/rehydration.md"
            chmod 755 "$NC_DIR/rehydration.md"
        fi

        if [ -f "$REPO_ROOT/master_profile.md" ]; then
            cp "$REPO_ROOT/master_profile.md" "$NC_DIR/master_profile.md"
            chmod 644 "$NC_DIR/master_profile.md"
        fi

        if [ -f "$REPO_ROOT/docs/MANIFEST.md" ]; then
            cp "$REPO_ROOT/docs/MANIFEST.md" "$NC_DIR/docs/MANIFEST.md"
            chmod 644 "$NC_DIR/docs/MANIFEST.md"
        fi
    fi
else
    # Running via curl | bash — embed deployment is handled by the script itself
    # The files should already be laid down by whoever piped the script
    info "  Running from piped install — using current directory structure"
fi

ok "  NeuralCline files deployed to $NC_DIR"

# ─── Step 2: Create session-state directory ──────────────────────────────
info "Step 2/6: Creating session state directory..."

mkdir -p "$SESSION_DIR"
chmod 755 "$SESSION_DIR"

# Initialize current-state.json if it doesn't exist
if [ ! -f "$SESSION_DIR/current-state.json" ]; then
    echo '{"session_id":"","last_updated":"","last_command":"","last_exit_code":0,"last_output_size":0,"last_proximity":0,"tool_call_count":0,"context_usage_pct":0,"current_context_tokens":0,"max_context_tokens":1048576,"session_start_count":0,"total_session_count":0,"file_scope_list":[],"active_goals":[],"next_steps":[]}' \
        > "$SESSION_DIR/current-state.json"
    ok "  Initialized current-state.json"
fi

if [ ! -f "$SESSION_DIR/crash-log.ndjson" ]; then
    touch "$SESSION_DIR/crash-log.ndjson"
    ok "  Initialized crash-log.ndjson"
fi

if [ ! -f "$SESSION_DIR/failure-points.json" ]; then
    echo '{"failure_points":[],"last_updated":"","total_crash_events":0}' \
        > "$SESSION_DIR/failure-points.json"
    ok "  Initialized failure-points.json"
fi

chmod -R 644 "$SESSION_DIR"/*.json "$SESSION_DIR"/*.ndjson 2>/dev/null || true

# Generate initial checkpoint
if [ -f "$NC_DIR/lib/state_engine.py" ]; then
    timeout 10 python3 "$NC_DIR/lib/state_engine.py" generate_checkpoint >/dev/null 2>&1 || true
fi

ok "  Session state directory ready at $SESSION_DIR"

# ─── Step 3: Set up Cline integration symlinks ────────────────────────────
info "Step 3/6: Setting up Cline integration symlinks..."

mkdir -p "$CLINE_HOOKS" "$CLINE_RULES"

# Remove old targets if they exist
rm -f "$CLINE_HOOKS/pre-tool-guard.sh" 2>/dev/null || true
rm -f "$CLINE_HOOKS/post-tool-state.sh" 2>/dev/null || true
rm -f "$CLINE_HOOKS/generate-handoff.sh" 2>/dev/null || true
rm -f "$CLINE_HOOKS/diagnose.sh" 2>/dev/null || true
rm -f "$CLINE_RULES/session-safety.md" 2>/dev/null || true
rm -f "$CLINE_RULES/recovery-protocols.md" 2>/dev/null || true

# Create symlinks
ln -sf "$NC_DIR/hooks/pre-tool-guard.sh" "$CLINE_HOOKS/pre-tool-guard.sh"
ln -sf "$NC_DIR/hooks/post-tool-state.sh" "$CLINE_HOOKS/post-tool-state.sh"
ln -sf "$NC_DIR/hooks/generate-handoff.sh" "$CLINE_HOOKS/generate-handoff.sh"
ln -sf "$NC_DIR/hooks/diagnose.sh" "$CLINE_HOOKS/diagnose.sh"
ln -sf "$NC_DIR/rules/session-safety.md" "$CLINE_RULES/session-safety.md"
ln -sf "$NC_DIR/rules/recovery-protocols.md" "$CLINE_RULES/recovery-protocols.md"

ok "  Symlinks created:"
ok "    $CLINE_HOOKS/{pre-tool-guard,post-tool-state,generate-handoff,diagnose}.sh"
ok "    $CLINE_RULES/{session-safety,recovery-protocols}.md"

# ─── Step 4: Set up root-level entry points ──────────────────────────────
info "Step 4/6: Setting up entry points..."

# ── rehydration.md (at /root/rehydration.md) ──
if [ -f "$NC_DIR/rehydration.md" ]; then
    cp "$NC_DIR/rehydration.md" "$REHYDRATION_FILE"
    chmod 755 "$REHYDRATION_FILE"
    ok "  Installed rehydration engine at $REHYDRATION_FILE"
fi

# ── master_profile.md (at /root/master_profile.md) ──
if [ -f "$NC_DIR/master_profile.md" ]; then
    cp "$NC_DIR/master_profile.md" "$MASTER_PROFILE"
    chmod 644 "$MASTER_PROFILE"
    ok "  Installed master profile at $MASTER_PROFILE"
fi

# ── auto-init.sh (at /root/.session-state/auto-init.sh) ──
cat > "$AUTOINIT_FILE" << 'AUTOINIT'
#!/bin/bash
# =============================================================================
# 🚀 AUTO-INIT — Shell-Level Session Recovery Hook
# =============================================================================
# Source this from .bashrc or .bash_profile to auto-restore session context
# every time a new terminal is opened.
#
# Add to /root/.bashrc:
#   [ -f /root/.session-state/auto-init.sh ] && source /root/.session-state/auto-init.sh
# =============================================================================

# Only run if we're in an interactive shell
if [[ $- != *i* ]]; then
    return
fi

SESSION_DIR="/root/.session-state"
CHECKPOINT="$SESSION_DIR/checkpoint.json"

if [ -f "$CHECKPOINT" ]; then
    python3 -c "
import json
with open('$CHECKPOINT') as f:
    cp = json.load(f)
tools = cp.get('total_tool_calls', 0)
ctx = cp.get('context_usage_pct', 0)
cmd = cp.get('last_command', '')
if tools > 0 or ctx > 0 or cmd:
    print(f'[Neural Safety] Session checkpoint found: {tools} tools, {ctx}% context')
    print(f'[Neural Safety] Last command: {cmd[:60]}...' if cmd else '')
    print('[Neural Safety] Run: source /root/rehydration.md')
" 2>/dev/null
fi
AUTOINIT

chmod 755 "$AUTOINIT_FILE"
ok "  Installed auto-init hook at $AUTOINIT_FILE"

# ── .bashrc hook ──
if ! grep -q "auto-init.sh" "$BASHRC_FILE" 2>/dev/null; then
    echo "" >> "$BASHRC_FILE"
    echo "# NeuralCline — auto-restore session context on terminal open" >> "$BASHRC_FILE"
    echo "if [ -f $AUTOINIT_FILE ]; then source $AUTOINIT_FILE; fi" >> "$BASHRC_FILE"
    ok "  Added auto-init hook to $BASHRC_FILE"
else
    info "  .bashrc already has auto-init hook — skipping"
fi

# ── .clinerules (at /root/.clinerules) ──
cat > "$CLINERULES_FILE" << 'CLINERULES'
# =============================================================================
# NEURALCLINE — Neural Session Safety System (v1.0.0)
# =============================================================================
# Codename: EDGECASE
# Workspace: /root/NeuralCline/
#
# These rules are loaded automatically by Cline for every session in /root.
# ⚠️ CRITICAL: The FIRST instruction below must be executed immediately.

## 🚨 MANDATORY FIRST ACTION — DO NOT SKIP
Run as your very first action in EVERY new session:
source /root/rehydration.md

This restores context from the last checkpoint so you can continue seamlessly.
After running it, read /root/master_profile.md for workspace context.
# =============================================================================

## SESSION CONTINUITY
Every tool call should use NeuralCline's pre-tool-guard.sh (proximity check) and post-tool-state.sh (state log).
If context > 60%, truncate/paginate output and save checkpoint.
If context > 80%, save checkpoint before every tool call.
Every 50 tool calls, generate a handoff automatically via NeuralCline.

## CRASH RECOVERY (use when session hangs or crashes)
Protocol A (session hang): run `source /root/rehydration.md`
Protocol B (context full): run `bash /root/NeuralCline/hooks/generate-handoff.sh`
Protocol C (output fail): run `tail -5 /root/.session-state/crash-log.ndjson`
Protocol D (crash): run `source /root/rehydration.md`
Protocol E (infinite loop): run `bash /root/NeuralCline/hooks/generate-handoff.sh`
Protocol F (big file): run `ls -lh <file>` then `head -100 <file>`
Full details in /root/NeuralCline/rules/recovery-protocols.md

## CRASH PROXIMITY DETECTION (auto-prevention)
Before every terminal command, check /root/.session-state/current-state.json for context_usage_pct.
The NeuralCline system computes a proximity score (0-100):
  > 60 → auto-save checkpoint, paginate output
  > 80 → refuse operation, generate handoff instead

## CRASH-FREE PYTHON EXECUTION (critical)
NEVER use inline `python3 -c "..."` — it causes shell integration timeout crashes.
Instead, use: python3 /root/NeuralCline/lib/state_engine.py <command> [args...]
All session state operations must route through state_engine.py.

## FORBIDDEN SCANS (cause context overflow)
NEVER recursively scan these directories:
  /root/bolix-workspace/ — contains 2.4MB+ logs and zip archives
  /root/Cline/ — Cline extension config — read only if explicitly asked
NEVER read files > 500KB without checking size first with `ls -lh`

## TERMINAL SAFETY
shellIntegrationTimeout is 60s (tuned up from 10s).
For commands expected > 30s: use `timeout 60s` wrapper.
For output > 500 lines: pipe through `head -200` or `grep`.
If output capture fails: check crash-log.ndjson, re-run with `head`.
Redirect stderr to stdout: `2>&1`.
CLINERULES

chmod 644 "$CLINERULES_FILE"
ok "  Installed .clinerules at $CLINERULES_FILE"

# ─── Step 5: Tune Cline globalState.json ──────────────────────────────────
info "Step 5/6: Tuning Cline configuration..."

if [ -n "$GLOBAL_STATE" ] && [ -f "$GLOBAL_STATE" ]; then
    # Backup
    cp "$GLOBAL_STATE" "${GLOBAL_STATE}.backup"
    ok "  Backed up globalState.json to ${GLOBAL_STATE}.backup"

    # Apply settings using python3 (via file, not inline -c)
    python3 "$NC_DIR/lib/state_engine.py" help >/dev/null 2>&1 || true

    # Use a Python script file instead of -c to stay crash-safe
    TUNE_SCRIPT=$(mktemp /tmp/neuralcline-tune-XXXXXX.py)
    cat > "$TUNE_SCRIPT" << 'PYEOF'
import json
import sys

path = sys.argv[1]
with open(path) as f:
    cfg = json.load(f)

# Tune shell integration timeout: 10s → 60s
if isinstance(cfg, dict):
    if 'shellIntegrationTimeout' in cfg:
        old = cfg['shellIntegrationTimeout']
        cfg['shellIntegrationTimeout'] = 60000
        print(f"  shellIntegrationTimeout: {old}ms → 60000ms")
    else:
        cfg['shellIntegrationTimeout'] = 60000
        print(f"  shellIntegrationTimeout: (not set) → 60000ms")

    if 'terminalOutputLineLimit' in cfg:
        old = cfg['terminalOutputLineLimit']
        cfg['terminalOutputLineLimit'] = 3000
        print(f"  terminalOutputLineLimit: {old} → 3000")
    else:
        cfg['terminalOutputLineLimit'] = 3000
        print(f"  terminalOutputLineLimit: (not set) → 3000")

    with open(path, 'w') as f:
        json.dump(cfg, f, indent=2)
    print("  Configuration updated successfully.")
else:
    print("  WARNING: globalState.json is not a JSON object — skipping tune.")
    sys.exit(1)
PYEOF

    timeout 10 python3 "$TUNE_SCRIPT" "$GLOBAL_STATE"
    rm -f "$TUNE_SCRIPT"
    ok "  Cline settings tuned in $GLOBAL_STATE"
else
    warn "  Could not find Cline globalState.json — skipping tune."
    warn "  You can manually set: shellIntegrationTimeout=60000, terminalOutputLineLimit=3000"
fi

# ─── Step 6: Sanity check and banner ──────────────────────────────────────
info "Step 6/6: Running sanity checks..."

ERRORS=0

check_file() {
    if [ -f "$1" ]; then
        ok "    $1"
    else
        err "    $1 — MISSING"
        ERRORS=$((ERRORS + 1))
    fi
}

check_symlink() {
    if [ -L "$1" ] && [ -e "$1" ]; then
        ok "    $1 -> $(readlink "$1")"
    else
        err "    $1 — MISSING or BROKEN"
        ERRORS=$((ERRORS + 1))
    fi
}

echo ""
echo "  ── Core Files ──"
check_file "$NC_DIR/lib/state_engine.py"
check_file "$NC_DIR/hooks/pre-tool-guard.sh"
check_file "$NC_DIR/hooks/post-tool-state.sh"
check_file "$NC_DIR/hooks/generate-handoff.sh"
check_file "$NC_DIR/hooks/diagnose.sh"
check_file "$NC_DIR/rules/session-safety.md"
check_file "$NC_DIR/rules/recovery-protocols.md"
check_file "$NC_DIR/rehydration.md"
check_file "$NC_DIR/master_profile.md"
check_file "$NC_DIR/docs/MANIFEST.md"

echo "  ── Root Entry Points ──"
check_file "$REHYDRATION_FILE"
check_file "$MASTER_PROFILE"
check_file "$CLINERULES_FILE"
check_file "$AUTOINIT_FILE"

echo "  ── Cline Integration Symlinks ──"
check_symlink "$CLINE_HOOKS/pre-tool-guard.sh"
check_symlink "$CLINE_HOOKS/post-tool-state.sh"
check_symlink "$CLINE_HOOKS/generate-handoff.sh"
check_symlink "$CLINE_HOOKS/diagnose.sh"
check_symlink "$CLINE_RULES/session-safety.md"
check_symlink "$CLINE_RULES/recovery-protocols.md"

echo "  ── Session State ──"
check_file "$SESSION_DIR/current-state.json"
check_file "$SESSION_DIR/crash-log.ndjson"
check_file "$SESSION_DIR/failure-points.json"
check_file "$SESSION_DIR/checkpoint.json"

echo ""
if [ $ERRORS -eq 0 ]; then
    ok "All $ERRORS checks passed — NeuralCline is fully deployed!"
else
    err "$ERRORS checks failed — review output above"
fi

# ─── Final banner ─────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}     ${BOLD}🧠 NeuralCline EDGECASE — Installation Complete${NC}    ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                          ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Deployed to:${NC}  $NC_DIR        ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Session state:${NC} $SESSION_DIR        ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Config tuned:${NC}  shellIntegrationTimeout → 60s  ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                  terminalOutputLineLimit → 3000   ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                          ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Quick start:${NC}                                   ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}    source /root/rehydration.md  — restore last session  ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}    bash $NC_DIR/hooks/generate-handoff.sh  — save checkpoint ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                          ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Recovery:${NC}                                      ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}    6 crash recovery protocols in:                         ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}    $NC_DIR/rules/recovery-protocols.md    ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                          ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Built by EDGECASE — the boundary no system anticipates.${NC} ${GREEN}║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# If running from curl|bash, exit cleanly
exit 0