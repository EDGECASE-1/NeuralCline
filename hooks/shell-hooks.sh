#!/bin/bash
# =============================================================================
# 🔧 NEURAL SHELL HOOKS — Automatic Pre/Post Command Instrumentation
# =============================================================================
# Source this from .bashrc to enable automatic hang/crash detection at the
# shell level. Every command gets:
#   - Pre-command: timestamp recording (for hang detection)
#   - Post-command: timing log + state update
#
# Add to /root/.bashrc:
#   [ -f /root/.session-state/shell-hooks.sh ] && source /root/.session-state/shell-hooks.sh
# =============================================================================

# Only run in interactive shells
[[ $- != *i* ]] && return

# ─── Paths ──────────────────────────────────────────────────────────────────
NEURAL_DIR="/root/NeuralCline"
SESSION_DIR="/root/.session-state"
STATE="$SESSION_DIR/current-state.json"
TIMING="$SESSION_DIR/timing-history.json"
CRASH_LOG="$SESSION_DIR/crash-log.ndjson"
PRE_TOOL_GUARD="$NEURAL_DIR/hooks/pre-tool-guard.sh"
POST_TOOL_STATE="$NEURAL_DIR/hooks/post-tool-state.sh"
TIMING_ENGINE="$NEURAL_DIR/lib/timing_metrics.py"
STATE_ENGINE="$NEURAL_DIR/lib/state_engine.py"
SELF_LEARNING="$NEURAL_DIR/lib/self_learning.py"

# ─── Pre-command timestamp (fires on DEBUG trap before each command) ────────
__neural_preexec() {
    # Save command and start time
    __NEURAL_LAST_CMD="$BASH_COMMAND"
    __NEURAL_START_EPOCH=$(date +%s%N 2>/dev/null || date +%s)
    __NEURAL_START_SEC=$(date +%s)
}

# ─── Post-command hook (fires on PROMPT_COMMAND after each command) ─────────
__neural_precmd() {
    # Guard: only track if we have a preexec timestamp
    [ -z "${__NEURAL_START_EPOCH:-}" ] && return

    local exit_code=$?
    local now_epoch=$(date +%s)
    local now_ns=$(date +%s%N 2>/dev/null || echo "$(date +%s)000000000")
    local start_ns="${__NEURAL_START_EPOCH:-0}"
    local duration_ms=$(( (now_ns - start_ns) / 1000000 ))
    # Fallback if ns calc failed
    [ "$duration_ms" -lt 0 ] || [ "$duration_ms" -gt 600000 ] && duration_ms=$(( (now_epoch - __NEURAL_START_SEC) * 1000 ))

    local cmd="${__NEURAL_LAST_CMD:-unknown}"
    local cmd_short="${cmd:0:120}"

    # ── Detect hang (command took > 30s without output) ──
    # A "hang" is defined as a command that took > 30s with exit code 0
    # (the shell finally got control back, so it's a delayed completion)
    local hang_detected=0
    local hang_reason=""
    if [ "$duration_ms" -gt 30000 ] 2>/dev/null; then
        hang_detected=1
        hang_reason="SLOW: ${duration_ms}ms"
        echo "[NeuralCline] ⏱️  HANG DETECTED: Command '${cmd_short}' took ${duration_ms}ms (${exit_code})" >&2
    fi

    # ── Detect crash (exit code != 0) ──
    local crash_detected=0
    if [ "$exit_code" -ne 0 ] && [ "$exit_code" -ne 130 ] && [ "$exit_code" -ne 141 ]; then
        crash_detected=1
        echo "[NeuralCline] 🛑 CRASH DETECTED: Command '${cmd_short}' exited with code ${exit_code}" >&2
    fi

    # ── Log to timing-history.json ──
    if [ -f "$TIMING_ENGINE" ]; then
        timeout 5 python3 "$TIMING_ENGINE" record_execution "$cmd_short" "$duration_ms" "$exit_code" 0 2>/dev/null || true
    fi

    # ── Log to crash-log.ndjson ──
    if [ "$hang_detected" -eq 1 ] || [ "$crash_detected" -eq 1 ]; then
        local proximity=0
        local entry="{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"session_id\":\"${__NEURAL_SESSION_ID:-shell}\",\"command\":\"${cmd_short//\"/\\\"}\",\"exit_code\":$exit_code,\"duration_ms\":$duration_ms,\"hang_detected\":$hang_detected,\"crash_detected\":$crash_detected,\"reason\":\"${hang_reason:-exit_code=$exit_code}\"}"
        echo "$entry" >> "$CRASH_LOG" 2>/dev/null || true
    fi

    # ── Update state file ──
    if [ -f "$STATE_ENGINE" ]; then
        timeout 5 python3 "$STATE_ENGINE" update_state "$cmd_short" "$exit_code" 0 0 2>/dev/null || true
    fi

    # ── Self-learning snapshot (every 5 commands) ──
    local count=$(( ${__NEURAL_CMD_COUNT:-0} + 1 ))
    __NEURAL_CMD_COUNT=$count
    if [ $((count % 5)) -eq 0 ] && [ -f "$SELF_LEARNING" ]; then
        timeout 5 python3 "$SELF_LEARNING" snapshot 2>/dev/null || true
    fi

    # ── Cleanup ──
    unset __NEURAL_START_EPOCH
    unset __NEURAL_START_SEC
    unset __NEURAL_LAST_CMD
}

# ─── Install hooks (deferred VS Code compatible) ───────────────────────────
# VS Code's terminal integration injects __vsc_preexec_all + __vsc_prompt_cmd_original
# AFTER .bashrc finishes loading, so we can't detect them at source time.
#
# Strategy: Use PROMPT_COMMAND as a "deferred installer" that:
#   1. Waits until VS Code's functions exist (usually by the 2nd prompt)
#   2. Patches __vsc_preexec_all to call __neural_preexec first
#   3. Patches __vsc_prompt_cmd_original to call __neural_precmd first
#   4. Removes itself after successful patching
#
# For non-VS Code terminals (ssh, tty), install hooks directly at source time.

# Only install if not already installed
if [[ "$__NEURAL_HOOKS_INSTALLED" != "1" ]]; then

    __NEURAL_SESSION_ID="shell-$(date +%s)-$$"

    # ── Try direct install first (works for non-VS Code terminals) ──
    if declare -F __vsc_preexec_all &>/dev/null && declare -F __vsc_prompt_cmd_original &>/dev/null; then
        # VS Code functions already exist — patch them immediately
        __NEURAL_ORIG_VSCODE_PREEXEC=$(declare -f __vsc_preexec_all)
        eval "$(echo "__vsc_preexec_all() { __neural_preexec; $(declare -f __vsc_preexec_all | tail -n +2)")" 2>/dev/null || true
        __NEURAL_ORIG_VSCODE_PROMPT=$(declare -f __vsc_prompt_cmd_original)
        eval "$(echo "__vsc_prompt_cmd_original() { __neural_precmd; $(declare -f __vsc_prompt_cmd_original | tail -n +2)")" 2>/dev/null || true
        __NEURAL_HOOKS_INSTALLED=1
        echo "[NeuralCline] 🔧 Shell hooks installed (direct VS Code patch)" >&2
    elif [ -n "${PS1:-}" ] && [ -z "${__VSCODE_PREINIT:-}" ]; then
        # Not a VS Code terminal (or VS Code hasn't loaded yet)
        # Install our own hooks directly
        __NEURAL_OLD_DEBUG_TRAP=$(trap -p DEBUG 2>/dev/null || true)
        if ! echo "$__NEURAL_OLD_DEBUG_TRAP" | grep -q "__neural_preexec"; then
            trap '__neural_preexec; '"${__NEURAL_OLD_DEBUG_TRAP#trap -- \'}" 2>/dev/null || \
            trap '__neural_preexec' DEBUG
        fi
        if ! echo "${PROMPT_COMMAND:-}" | grep -q "__neural_precmd"; then
            PROMPT_COMMAND="__neural_precmd; ${PROMPT_COMMAND:-}"
        fi
        __NEURAL_HOOKS_INSTALLED=1
        echo "[NeuralCline] 🔧 Shell hooks installed (direct DEBUG + PROMPT_COMMAND)" >&2
    else
        # VS Code will load after .bashrc — set up deferred installer via PROMPT_COMMAND
        # This runs on the FIRST prompt, AFTER VS Code has injected its hooks.
        if ! declare -F __neural_deferred_install &>/dev/null; then
            __neural_deferred_install() {
                # Check if VS Code hooks are now loaded
                if declare -F __vsc_preexec_all &>/dev/null && declare -F __vsc_prompt_cmd_original &>/dev/null; then
                    # Patch VS Code's functions
                    eval "$(echo "__vsc_preexec_all() { __neural_preexec; $(declare -f __vsc_preexec_all | tail -n +2)")" 2>/dev/null || true
                    eval "$(echo "__vsc_prompt_cmd_original() { __neural_precmd; $(declare -f __vsc_prompt_cmd_original | tail -n +2)")" 2>/dev/null || true
                    __NEURAL_HOOKS_INSTALLED=1
                    # Remove this deferred installer from PROMPT_COMMAND
                    PROMPT_COMMAND="${PROMPT_COMMAND//__neural_deferred_install; /}"
                    PROMPT_COMMAND="${PROMPT_COMMAND//; __neural_deferred_install/}"
                    PROMPT_COMMAND="${PROMPT_COMMAND//__neural_deferred_install/}"
                    echo "[NeuralCline] 🔧 Shell hooks installed (deferred VS Code patch)" >&2
                fi
                # If VS Code still not loaded, stay in PROMPT_COMMAND and try again next prompt
            }
            PROMPT_COMMAND="__neural_deferred_install; ${PROMPT_COMMAND:-}"
        fi
        # Set a marker so we know this is a VS Code terminal waiting for init
        __VSCODE_PREINIT=1
    fi
fi
