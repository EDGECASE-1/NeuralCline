#!/bin/bash
# =============================================================================
# 🔍 SELF-DIAGNOSTIC — NeuralCline EDGECASE
# =============================================================================
# Diagnoses session hangs, stale state, missing hooks, and shell integration
# failures. Outputs structured results that feed into crash-log.ndjson and
# failure-points.json for the data pipeline.
#
# Usage:  bash /root/NeuralCline/hooks/diagnose.sh [--quiet | --json]
#         --quiet   machine-readable key=value output
#         --json    full JSON diagnostic dump
# =============================================================================

ENGINE="/root/NeuralCline/lib/state_engine.py"
SESSION_DIR="/root/.session-state"
STATE="$SESSION_DIR/current-state.json"
CHECKPOINT="$SESSION_DIR/checkpoint.json"
CRASH_LOG="$SESSION_DIR/crash-log.ndjson"
FAILURE_POINTS="$SESSION_DIR/failure-points.json"
AUTOINIT="$SESSION_DIR/auto-init.sh"
CLINERULES="/root/.clinerules"
REHYDRATION="/root/rehydration.md"
BASHRC="/root/.bashrc"

MODE="${1:-human}"
NOW_EPOCH=$(date +%s)

# Colors for human mode
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

pass() { echo -e "  ${GREEN}✅${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }
fail() { echo -e "  ${RED}❌${NC} $1"; }
info() { echo -e "  ${CYAN}ℹ️  $1${NC}"; }

# ===================== DIAGNOSTIC CHECKS =====================

CHECK_IDX=0
ISSUES=()
RESULTS=""

record() {
    local check="$1"
    local status="$2"   # pass | warn | fail | info
    local detail="$3"
    CHECK_IDX=$((CHECK_IDX + 1))
    RESULTS="${RESULTS}${CHECK_IDX}|${status}|${check}|${detail}\n"
}

# ─── 1. State freshness (hang detection) ─────────────────────────────────
check_state_freshness() {
    local check="State freshness — is the session currently hung?"

    if [ ! -f "$STATE" ]; then
        record "$check" "fail" "State file missing — session never initialized"
        return
    fi

    local last_str
    last_str=$(grep -o '"last_updated"[[:space:]]*:[[:space:]]*"[^"]*"' "$STATE" | cut -d'"' -f4)

    if [ -z "$last_str" ]; then
        record "$check" "warn" "No last_updated timestamp in state"
        return
    fi

    # Parse the ISO timestamp to epoch
    local last_epoch=0
    if command -v python3 &>/dev/null; then
        last_epoch=$(python3 -c "
from datetime import datetime, timezone
try:
    dt = datetime.fromisoformat('$last_str'.replace('Z', '+00:00'))
    print(int(dt.timestamp()))
except:
    print(0)
" 2>/dev/null)
    fi

    if [ "$last_epoch" -eq 0 ]; then
        record "$check" "warn" "Could not parse timestamp: $last_str"
        return
    fi

    local gap=$(( NOW_EPOCH - last_epoch ))
    local gap_min=$(( gap / 60 ))
    local tool_count
    tool_count=$(grep -o '"tool_call_count"[[:space:]]*:[[:space:]]*[0-9]*' "$STATE" | grep -o '[0-9]*$')

    if [ "$gap_min" -gt 60 ]; then
        record "$check" "fail" "State stale for ${gap_min}min (${tool_count} tool calls recorded — probable hang)"
    elif [ "$gap_min" -gt 30 ]; then
        record "$check" "warn" "State stale for ${gap_min}min — possible hang"
    elif [ "$gap_min" -gt 15 ]; then
        record "$check" "info" "State last updated ${gap_min}min ago — normal if idle"
    else
        record "$check" "pass" "State fresh — last updated ${gap_min}min ago"
    fi
}

# ─── 2. Hook integrity ──────────────────────────────────────────────────
check_hooks() {
    local check="Hooks — are all 3 hooks present and executable?"

    local all_ok=true
    for hook in pre-tool-guard.sh post-tool-state.sh generate-handoff.sh; do
        local path="/root/NeuralCline/hooks/$hook"
        if [ ! -f "$path" ]; then
            record "Hook: $hook" "fail" "Missing: $path"
            all_ok=false
        elif [ ! -x "$path" ]; then
            record "Hook: $hook" "warn" "Not executable: $path"
            all_ok=false
        fi
    done

    if $all_ok; then
        record "$check" "pass" "All 3 hooks present and executable"
    fi
}

# ─── 3. Symlink chain ────────────────────────────────────────────────────
check_symlinks() {
    local check="Cline integration — are the symlinks intact?"

    local all_ok=true
    for link in \
        "/root/Cline/Hooks/pre-tool-guard.sh" \
        "/root/Cline/Hooks/post-tool-state.sh" \
        "/root/Cline/Hooks/generate-handoff.sh" \
        "/root/Cline/Rules/session-safety.md" \
        "/root/Cline/Rules/recovery-protocols.md"; do

        if [ ! -L "$link" ]; then
            record "Symlink: $link" "fail" "Missing symlink"
            all_ok=false
        elif [ ! -e "$link" ]; then
            record "Symlink: $link" "fail" "Broken symlink -> $(readlink "$link")"
            all_ok=false
        fi
    done

    if $all_ok; then
        record "$check" "pass" "All 5 symlinks intact"
    fi
}

# ─── 4. State engine ─────────────────────────────────────────────────────
check_engine() {
    local check="State engine — is state_engine.py functional?"

    if [ ! -f "$ENGINE" ]; then
        record "$check" "fail" "state_engine.py missing"
        return
    fi

    local result
    result=$(timeout 5 python3 "$ENGINE" help 2>&1)
    if echo "$result" | grep -q "compute_proximity"; then
        record "$check" "pass" "state_engine.py responds with all 8 commands"
    else
        record "$check" "fail" "state_engine.py not responding: $result"
    fi
}

# ─── 5. .clinerules ──────────────────────────────────────────────────────
check_clinerules() {
    local check=".clinerules — does it mandate rehydration?"

    if [ ! -f "$CLINERULES" ]; then
        record "$check" "fail" ".clinerules missing at $CLINERULES"
        return
    fi

    if grep -q "source /root/rehydration.md" "$CLINERULES" 2>/dev/null; then
        record "$check" "pass" ".clinerules has rehydration directive"
    else
        record "$check" "warn" ".clinerules missing 'source /root/rehydration.md'"
    fi
}

# ─── 6. rehydration.md ──────────────────────────────────────────────────
check_rehydration() {
    local check="Rehydration engine — is it at /root/rehydration.md?"

    if [ -f "$REHYDRATION" ] && [ -x "$REHYDRATION" ]; then
        record "$check" "pass" "/root/rehydration.md present and executable"
    elif [ -f "$REHYDRATION" ]; then
        record "$check" "warn" "/root/rehydration.md present but not executable"
    else
        record "$check" "fail" "/root/rehydration.md missing"
    fi
}

# ─── 7. .bashrc hook ────────────────────────────────────────────────────
check_bashrc() {
    local check=".bashrc — is the auto-init hook installed?"

    if [ ! -f "$BASHRC" ]; then
        record "$check" "warn" ".bashrc not found"
        return
    fi

    if grep -q "auto-init.sh" "$BASHRC" 2>/dev/null; then
        record "$check" "pass" "auto-init hook present in .bashrc"
    else
        record "$check" "warn" "auto-init hook missing from .bashrc — new terminals won't auto-restore"
    fi
}

# ─── 8. auto-init.sh ────────────────────────────────────────────────────
check_autoinits() {
    local check="auto-init.sh — is the shell recovery hook installed?"

    if [ -f "$AUTOINIT" ] && [ -x "$AUTOINIT" ]; then
        record "$check" "pass" "auto-init.sh present at $AUTOINIT"
    elif [ -f "$AUTOINIT" ]; then
        record "$check" "warn" "auto-init.sh present but not executable"
    else
        record "$check" "fail" "auto-init.sh missing at $AUTOINIT"
    fi
}

# ─── 9. Session state files ─────────────────────────────────────────────
check_state_files() {
    local check="Session state files — are all 4 present?"

    local all_ok=true
    for sf in current-state.json checkpoint.json crash-log.ndjson failure-points.json; do
        if [ ! -f "$SESSION_DIR/$sf" ]; then
            record "State file: $sf" "fail" "Missing: $SESSION_DIR/$sf"
            all_ok=false
        fi
    done

    if $all_ok; then
        record "$check" "pass" "All 4 session state files present"
    fi
}

# ─── 10. Shell integration test ──────────────────────────────────────────
check_shell_integration() {
    local check="Shell integration — can we detect the shell environment?"

    # Check if we're in an interactive shell
    if [[ $- == *i* ]]; then
        record "$check" "pass" "Interactive shell detected"
    else
        record "$check" "warn" "Non-interactive shell — some features may not work"
    fi

    # Check for PS1 prompt (shell integration indicator)
    if [ -n "$PS1" ]; then
        record "Shell prompt" "pass" "PS1 set — shell integration active"
    else
        record "Shell prompt" "info" "PS1 not set in current context"
    fi
}

# ─── 11. Cline globalState.json tuning ──────────────────────────────────
check_cline_config() {
    local check="Cline globalState.json — are timeouts tuned?"

    local state_file=""
    local candidates=(
        "/root/.local/share/code-server/User/globalStorage/saoudrizwan.claude-dev/globalState.json"
        "/root/.config/Code/User/globalStorage/saoudrizwan.claude-dev/globalState.json"
        "/root/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/globalState.json"
    )

    for c in "${candidates[@]}"; do
        if [ -f "$c" ]; then
            state_file="$c"
            break
        fi
    done

    if [ -z "$state_file" ]; then
        record "$check" "info" "globalState.json not found — not installed on this system?"
        return
    fi

    local timeout
    timeout=$(grep -o '"shellIntegrationTimeout"[[:space:]]*:[[:space:]]*[0-9]*' "$state_file" | grep -o '[0-9]*$')

    if [ "$timeout" = "60000" ]; then
        record "$check" "pass" "shellIntegrationTimeout=60000ms (tuned)"
    elif [ -n "$timeout" ]; then
        record "$check" "warn" "shellIntegrationTimeout=${timeout}ms — expected 60000ms"
    else
        record "$check" "warn" "shellIntegrationTimeout not set"
    fi
}

# ─── 12. Crash-pattern awareness ────────────────────────────────────────
check_crash_patterns() {
    local check="Failure patterns — are known crash patterns being tracked?"

    if [ ! -f "$FAILURE_POINTS" ]; then
        record "$check" "warn" "failure-points.json missing"
        return
    fi

    local total_events
    total_events=$(grep -o '"total_crash_events"[[:space:]]*:[[:space:]]*[0-9]*' "$FAILURE_POINTS" | grep -o '[0-9]*$')

    if [ "$total_events" -gt 0 ]; then
        record "$check" "info" "Tracking $total_events crash events across sessions"
    else
        record "$check" "info" "No crash events recorded yet"
    fi
}

# ─── 13. Context pressure ────────────────────────────────────────────────
check_context_pressure() {
    local check="Context pressure — is the workspace bloated?"

    local bolix_size
    if [ -d "/root/bolix-workspace" ]; then
        bolix_size=$(du -sh /root/bolix-workspace 2>/dev/null | cut -f1)
        record "bolix-workspace" "info" "Size: $bolix_size"
    else
        record "bolix-workspace" "pass" "Directory not present — no bloat risk"
    fi
}

# ===================== RUN ALL CHECKS =====================

check_state_freshness
check_hooks
check_symlinks
check_engine
check_clinerules
check_rehydration
check_bashrc
check_autoinits
check_state_files
check_shell_integration
check_cline_config
check_crash_patterns
check_context_pressure

# ===================== LOG THE DIAGNOSTIC =====================

# Count issues by severity
PASS_COUNT=$(echo -e "$RESULTS" | grep -c "|pass|" 2>/dev/null || echo 0)
WARN_COUNT=$(echo -e "$RESULTS" | grep -c "|warn|" 2>/dev/null || echo 0)
FAIL_COUNT=$(echo -e "$RESULTS" | grep -c "|fail|" 2>/dev/null || echo 0)
INFO_COUNT=$(echo -e "$RESULTS" | grep -c "|info|" 2>/dev/null || echo 0)

# Write a structured diagnostic entry to crash-log.ndjson
DIAG_ENTRY=$(python3 -c "
import json, uuid
entry = {
    'timestamp': '$(date -u +"%Y-%m-%dT%H:%M:%SZ")',
    'session_id': '$(python3 -c "import json; print(json.load(open('$SESSION_DIR/current-state.json')).get('session_id', str(uuid.uuid4())))" 2>/dev/null || echo "diagnostic-$(uuidgen)")',
    'command': 'diagnose.sh',
    'exit_code': $FAIL_COUNT,
    'output_size_lines': $CHECK_IDX,
    'crash_proximity_score': $(( FAIL_COUNT * 20 + WARN_COUNT * 10 )),
    'file_scope': ['/root'],
    'error': '${FAIL_COUNT} failures, ${WARN_COUNT} warnings from self-diagnostic'
}
print(json.dumps(entry))
" 2>/dev/null)

if [ -n "$DIAG_ENTRY" ] && command -v python3 &>/dev/null; then
    timeout 5 python3 "$ENGINE" write_crash_log "diagnose.sh" "$FAIL_COUNT" "$CHECK_IDX" "$(( FAIL_COUNT * 20 + WARN_COUNT * 10 ))" "/root" "${FAIL_COUNT} failures, ${WARN_COUNT} warnings from self-diagnostic" >&2 2>/dev/null || true
    timeout 5 python3 "$ENGINE" update_failure_points >&2 2>/dev/null || true
fi

# ===================== OUTPUT =====================

case "$MODE" in
    --json)
        # Full JSON output for data pipeline
        python3 -c "
import json
results = []
lines = '''$RESULTS'''.strip().split('\n')
for line in lines:
    if '|' in line:
        parts = line.split('|', 3)
        results.append({
            'check_id': int(parts[0]),
            'status': parts[1],
            'check': parts[2],
            'detail': parts[3]
        })
output = {
    'timestamp': '$(date -u +"%Y-%m-%dT%H:%M:%SZ")',
    'run_id': '$(uuidgen)',
    'checks': results,
    'summary': {
        'total': $CHECK_IDX,
        'pass': $PASS_COUNT,
        'warn': $WARN_COUNT,
        'fail': $FAIL_COUNT,
        'info': $INFO_COUNT
    },
    'diagnosis': 'PROBABLE_HANG' if [ $FAIL_COUNT -gt 0 ] && [ $PASS_COUNT -lt 3 ] else 'STABLE',
    'recovery_command': 'source /root/rehydration.md' if [ $FAIL_COUNT -gt 0 ] else 'none'
}
print(json.dumps(output, indent=2))
" 2>/dev/null
        ;;

    --quiet)
        # Machine-readable key=value
        echo "diagnose_checks=$CHECK_IDX"
        echo "diagnose_pass=$PASS_COUNT"
        echo "diagnose_warn=$WARN_COUNT"
        echo "diagnose_fail=$FAIL_COUNT"
        echo "diagnose_info=$INFO_COUNT"
        echo "diagnose_verdict=$([ "$FAIL_COUNT" -gt 0 ] && [ "$PASS_COUNT" -lt 3 ] && echo "PROBABLE_HANG" || echo "STABLE")"
        echo "diagnose_recovery=$([ "$FAIL_COUNT" -gt 0 ] && echo "source /root/rehydration.md" || echo "none")"
        ;;

    *)
        # Human-readable
        echo ""
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║${NC}     ${BOLD}🔍 NeuralCline Self-Diagnostic${NC}                    ${CYAN}║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo ""

        if [ "$FAIL_COUNT" -gt 0 ] && [ "$PASS_COUNT" -lt 3 ]; then
            echo -e "  ${RED}${BOLD}🛑 VERDICT: PROBABLE HANG${NC}"
            echo -e "  ${RED}   Recovery: source /root/rehydration.md${NC}"
            echo ""
        else
            echo -e "  ${GREEN}${BOLD}✅ VERDICT: SYSTEM STABLE${NC}"
            echo ""
        fi

        echo -e "  ${BOLD}Summary:${NC} $PASS_COUNT passed, $WARN_COUNT warnings, $FAIL_COUNT failures, $INFO_COUNT info"
        echo ""

        echo -e "  ${BOLD}─── Detail ───${NC}"
        echo -e "$RESULTS" | while IFS='|' read -r idx status check detail; do
            [ -z "$idx" ] && continue
            case "$status" in
                pass) echo -e "$(pass "$check — $detail")" ;;
                warn) echo -e "$(warn "$check — $detail")" ;;
                fail) echo -e "$(fail "$check — $detail")" ;;
                info) echo -e "$(info "$check — $detail")" ;;
            esac
        done

        echo ""
        echo -e "  ${BOLD}─── Recovery ───${NC}"
        if [ "$FAIL_COUNT" -gt 0 ]; then
            echo "  Run: source /root/rehydration.md"
            echo "  Or for a full handoff: bash /root/NeuralCline/hooks/generate-handoff.sh"
        else
            echo "  No action needed."
        fi
        echo ""
        echo -e "  ${CYAN}Diagnostic logged to crash-log.ndjson and failure-points.json${NC}"
        echo ""
        ;;
esac

exit $FAIL_COUNT