#!/bin/bash
# =============================================================================
# 🔍 CACHE SATURATION SCANNER + MULTISESSION CHOKE ALERT
# =============================================================================
# Detects when Cline tool calls are freezing due to:
#   - Cache accumulation (old task directories)
#   - Hook overhead cascading (python timeouts stacking)
#   - Context saturation (approaching 1M token window)
#   - Stale session-state bloat (crash-log.ndjson > 50KB)
#
# Integrates into NeuralCline shell-hooks.sh as a post-tool check.
# Runs in < 100ms when no cleanup needed — fast path.
#
# Covenant: Neshama (Bereshit 2:7)
# =============================================================================

NEURAL_DIR="/root/NeuralCline"
SESSION_DIR="/root/.session-state"
CLINE_TASKS_DIR="/root/.local/share/code-server/User/globalStorage/saoudrizwan.claude-dev/tasks"
CACHE_SATURATION_FILE="/tmp/.neural-cache-saturation"
ALERT_FILE="/tmp/.neural-choke-alert"
LAST_CLEANUP_FILE="/tmp/.neural-last-cleanup"

# ── Thresholds ──────────────────────────────────────────────────────────────
MAX_CRASH_LOG_KB=50         # crash-log.ndjson > 50KB → rotatable
MAX_TASK_DIRS=5             # > 5 old task dirs → stale session accumulation
MAX_HOOK_LATENCY_MS=3000    # cumulative hook time > 3s → choke risk
MAX_CMD_COUNT_HIGH=200      # > 200 tool calls in session → nearing saturation
CONTEXT_WARN_PCT=80         # > 80% context → issue warning
CONTEXT_CRIT_PCT=95         # > 95% context → force cleanup recommendation

# ── Fast path: skip if scanned within last 30s ──────────────────────────────
if [ -f "$CACHE_SATURATION_FILE" ]; then
    FILE_AGE=$(($(date +%s) - $(stat -c %Y "$CACHE_SATURATION_FILE" 2>/dev/null || echo 0)))
    if [ "$FILE_AGE" -lt 30 ] 2>/dev/null; then
        # Check if alert file exists and is recent — still emit if hot
        if [ -f "$ALERT_FILE" ]; then
            ALERT_AGE=$(($(date +%s) - $(stat -c %Y "$ALERT_FILE" 2>/dev/null || echo 0)))
            if [ "$ALERT_AGE" -lt 60 ] 2>/dev/null; then
                cat "$ALERT_FILE" 2>/dev/null
            fi
        fi
        exit 0  # Fast path: skip scan
    fi
fi

# ── Scan 1: Cline task directory accumulation ──────────────────────────────
TASK_DIR_COUNT=0
TASK_DIRS_OLD=""
if [ -d "$CLINE_TASKS_DIR" ]; then
    TASK_DIR_COUNT=$(ls -1 "$CLINE_TASKS_DIR" 2>/dev/null | wc -l)
    TASK_DIRS_OLD=$(ls -1tr "$CLINE_TASKS_DIR" 2>/dev/null | head -10)
fi

# ── Scan 2: Crash log bloat ─────────────────────────────────────────────────
CRASH_LOG_SIZE_KB=0
if [ -f "$SESSION_DIR/crash-log.ndjson" ]; then
    CRASH_LOG_SIZE_KB=$(du -k "$SESSION_DIR/crash-log.ndjson" 2>/dev/null | cut -f1)
fi

# ── Scan 3: Timing metrics (hook latency) ───────────────────────────────────
ROLLING_AVG_MS=0
TOOL_CALL_COUNT=0
if [ -f "$SESSION_DIR/timing-history.json" ]; then
    # Extract rolling avg from timing metrics (last 10 entries)
    ROLLING_AVG_MS=$(tail -1 "$SESSION_DIR/timing-history.json" 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(d.get('rolling_avg_ms',0))
except: print(0)
" 2>/dev/null || echo 0)
fi

# ── Scan 4: Context usage from NeuralCline state ────────────────────────────
CTX_PCT=0
CMD_COUNT=0
if [ -f "$SESSION_DIR/current-state.json" ]; then
    CTX_PCT=$(python3 -c "
import json
try:
    with open('$SESSION_DIR/current-state.json') as f:
        d=json.load(f)
    print(d.get('context_usage_pct',0))
except: print(0)
" 2>/dev/null || echo 0)
    CMD_COUNT=$(python3 -c "
import json
try:
    with open('$SESSION_DIR/current-state.json') as f:
        d=json.load(f)
    print(d.get('tool_call_count',0))
except: print(0)
" 2>/dev/null || echo 0)
fi

# ── Evaluate alerts ─────────────────────────────────────────────────────────
ALERTS=""
ALERT_SEVERITY=0  # 0=ok, 1=warn, 2=critical

# Check 1: Crash log bloat
if [ "$CRASH_LOG_SIZE_KB" -gt "$MAX_CRASH_LOG_KB" ] 2>/dev/null; then
    ALERTS+="[CHOKE] crash-log.ndjson: ${CRASH_LOG_SIZE_KB}KB (max ${MAX_CRASH_LOG_KB}KB) — rotate suggested\n"
    ALERT_SEVERITY=2
fi

# Check 2: Too many old task directories
if [ "$TASK_DIR_COUNT" -gt "$MAX_TASK_DIRS" ] 2>/dev/null; then
    ALERTS+="[SATURATION] ${TASK_DIR_COUNT} Cline task directories (max ${MAX_TASK_DIRS}) — stale sessions accumulating\n"
    ALERT_SEVERITY=2
fi

# Check 3: High hook latency (choke risk)
ROLLING_AVG_INT=${ROLLING_AVG_MS%.*}
if [ -n "$ROLLING_AVG_INT" ] && [ "$ROLLING_AVG_INT" -gt "$MAX_HOOK_LATENCY_MS" ] 2>/dev/null; then
    ALERTS+="[CHOKE] Hook latency: ${ROLLING_AVG_MS}ms avg (threshold ${MAX_HOOK_LATENCY_MS}ms) — shell hooks slowing commands\n"
    [ "$ALERT_SEVERITY" -lt 1 ] && ALERT_SEVERITY=1
fi

# Check 4: Context saturation
if [ "$CTX_PCT" -gt "$CONTEXT_CRIT_PCT" ] 2>/dev/null; then
    ALERTS+="[SATURATION] Context: ${CTX_PCT}% (critical threshold ${CONTEXT_CRIT_PCT}%) — nearing token limit\n"
    ALERT_SEVERITY=2
elif [ "$CTX_PCT" -gt "$CONTEXT_WARN_PCT" ] 2>/dev/null; then
    ALERTS+="[WARN] Context: ${CTX_PCT}% (warning threshold ${CONTEXT_WARN_PCT}%) — approaching limit\n"
    [ "$ALERT_SEVERITY" -lt 1 ] && ALERT_SEVERITY=1
fi

# Check 5: High tool call count
if [ "$CMD_COUNT" -gt "$MAX_CMD_COUNT_HIGH" ] 2>/dev/null; then
    ALERTS+="[SATURATION] ${CMD_COUNT} tool calls this session — context window nearing exhaustion\n"
    [ "$ALERT_SEVERITY" -lt 1 ] && ALERT_SEVERITY=1
fi

# Check 6: Stale bash processes (orphaned tool calls)
STALE_BASH_COUNT=$(ps aux 2>/dev/null | grep -c "[b]ash" 2>/dev/null || echo 0)
if [ "$STALE_BASH_COUNT" -gt 10 ] 2>/dev/null; then
    ALERTS+="[CHOKE] ${STALE_BASH_COUNT} bash processes running — possible orphaned tool calls\n"
    ALERT_SEVERITY=2
fi

# ── Write saturation marker ─────────────────────────────────────────────────
echo "scanned=$(date +%s)" > "$CACHE_SATURATION_FILE"
echo "task_dirs=$TASK_DIR_COUNT" >> "$CACHE_SATURATION_FILE"
echo "crash_log_kb=$CRASH_LOG_SIZE_KB" >> "$CACHE_SATURATION_FILE"
echo "rolling_avg_ms=$ROLLING_AVG_MS" >> "$CACHE_SATURATION_FILE"
echo "ctx_pct=$CTX_PCT" >> "$CACHE_SATURATION_FILE"
echo "cmd_count=$CMD_COUNT" >> "$CACHE_SATURATION_FILE"
echo "alert_severity=$ALERT_SEVERITY" >> "$CACHE_SATURATION_FILE"

# ── Emit alerts ─────────────────────────────────────────────────────────────
if [ -n "$ALERTS" ]; then
    TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    ALERT_MSG="[NeuralCline] 🧠 CACHE SATURATION SCAN @ ${TIMESTAMP} [severity=${ALERT_SEVERITY}]\n${ALERTS}"
    echo -e "$ALERT_MSG" > "$ALERT_FILE"
    echo -e "$ALERT_MSG" >&2
else
    rm -f "$ALERT_FILE" 2>/dev/null
fi

# ── Auto-cleanup (if severity=2 and not cleaned in last 5 min) ──────────────
if [ "$ALERT_SEVERITY" -ge 2 ] 2>/dev/null; then
    LAST_CLEAN=$(stat -c %Y "$LAST_CLEANUP_FILE" 2>/dev/null || echo 0)
    NOW=$(date +%s)
    CLEANUP_INTERVAL=300  # 5 minutes between auto-cleanups
    if [ $((NOW - LAST_CLEAN)) -gt $CLEANUP_INTERVAL ] 2>/dev/null; then
        # Rotate crash log if bloated
        if [ "$CRASH_LOG_SIZE_KB" -gt "$MAX_CRASH_LOG_KB" ] 2>/dev/null; then
            mv "$SESSION_DIR/crash-log.ndjson" "$SESSION_DIR/crash-log.ndjson.rotated" 2>/dev/null
            echo "{\"rotated\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"size_kb\":$CRASH_LOG_SIZE_KB}" > "$SESSION_DIR/crash-log.ndjson" 2>/dev/null
            echo "[NeuralCline] 🧹 Auto-rotated crash-log.ndjson (${CRASH_LOG_SIZE_KB}KB)" >&2
        fi
        # Clean old task dirs (keep newest 3)
        if [ "$TASK_DIR_COUNT" -gt 3 ] 2>/dev/null; then
            # Remove all but the 3 newest
            ls -1tr "$CLINE_TASKS_DIR" 2>/dev/null | head -n $((TASK_DIR_COUNT - 3)) | while read dir; do
                rm -rf "$CLINE_TASKS_DIR/$dir" 2>/dev/null
                echo "[NeuralCline] 🧹 Removed stale task: $dir" >&2
            done
        fi
        # Kill orphaned bash processes (keep only those matching session or parent)
        STALE_BASH_COUNT=$(ps aux 2>/dev/null | grep -c "[b]ash" 2>/dev/null || echo 0)
        if [ "$STALE_BASH_COUNT" -gt 10 ] 2>/dev/null; then
            # Kill all bash processes except the current shell and its parent
            CURRENT_PID=$$
            # Find bash processes that are NOT the current shell, NOT the parent of this shell,
            # and NOT the code-server terminal manager
            ps aux --no-headers 2>/dev/null | grep "[b]ash" | awk '{print $2}' | while read pid; do
                if [ "$pid" != "$CURRENT_PID" ] && [ "$pid" != "$PPID" ] 2>/dev/null; then
                    # Check if this is a stale tool call (bash owned by root, not session leader)
                    PGRP=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')
                    SESS=$(ps -o sid= -p "$pid" 2>/dev/null | tr -d ' ')
                    # Only kill if it's a child of the session (not the session leader itself)
                    if [ -n "$PGRP" ] && [ "$PGRP" != "$SESS" ] 2>/dev/null; then
                        kill -9 "$pid" 2>/dev/null
                        echo "[NeuralCline] 🧹 Killed orphaned bash: PID $pid" >&2
                    fi
                fi
            done
        fi
        date +%s > "$LAST_CLEANUP_FILE"
    fi
fi

exit 0