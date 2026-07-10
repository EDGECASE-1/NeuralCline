#!/bin/bash
# =============================================================================
# ⏱️ HANG BUFFER — Detached subprocess execution for long-running commands
# =============================================================================
# Purpose: When a command is predicted to exceed the shell integration timeout
# (60s), this wrapper forks it into a detached subprocess so Cline's terminal
# doesn't lock up. Control returns to Cline immediately.
#
# Mechanism:
#   1. pre-tool-guard.sh predicts timeout proximity (0-100)
#   2. If > 60 (WARNING): fork into background, return PID
#   3. Cline can poll status via: bash hang-buffer.sh status <pid>
#   4. Once complete, results are in hang-buffer-log/
#
# Usage:
#   bash hang-buffer.sh exec "<command>"    # Execute in buffer
#   bash hang-buffer.sh status <pid>        # Check status
#   bash hang-buffer.sh result <pid>        # Get result
#   bash hang-buffer.sh list                # List active buffers
#   bash hang-buffer.sh reap                # Clean completed buffers
# =============================================================================

NEURAL_DIR="/root/NeuralCline"
BUFFER_DIR="/root/.session-state/hang-buffer"
mkdir -p "$BUFFER_DIR"

# ─── Detect if a command will hang (timeout proximity) ──────────────────────
predict_hang() {
    local cmd="$1"
    local result
    result=$(timeout 10 python3 "$NEURAL_DIR/lib/timing_metrics.py" predict_timeout "$cmd" 2>&1)
    local timeout_prox=$(echo "$result" | grep "^TIMEOUT_PROXIMITY=" | cut -d= -f2)
    local estimated_sec=$(echo "$result" | grep "^ESTIMATED_SEC=" | cut -d= -f2)
    local eef=$(echo "$result" | grep "^EEF=" | cut -d= -f2)
    local severity=$(echo "$result" | grep "^SEVERITY=" | cut -d= -f2)

    echo "TIMEOUT_PROXIMITY=$timeout_prox"
    echo "ESTIMATED_SEC=$estimated_sec"
    echo "EEF=$eef"
    echo "SEVERITY=$severity"

    # Return 0 (will hang) if proximity > 60 or estimated > 30s
    if [ "$timeout_prox" -ge 60 ] 2>/dev/null || [ "$estimated_sec" -gt 30 ] 2>/dev/null; then
        return 0  # Will hang — use buffer
    fi
    return 1  # Safe — run directly
}

# ─── Execute command in detached buffer ──────────────────────────────────────
exec_buffer() {
    local cmd="$1"
    local buffer_id
    buffer_id="buf-$(date +%s)-$$-$((RANDOM % 1000))"
    local log_file="$BUFFER_DIR/$buffer_id.log"
    local meta_file="$BUFFER_DIR/$buffer_id.meta"
    local result_file="$BUFFER_DIR/$buffer_id.result"
    local pid_file="$BUFFER_DIR/$buffer_id.pid"

    # Write metadata
    cat > "$meta_file" <<META
buffer_id=$buffer_id
command=$cmd
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
status=running
META

    # Write command to a temp script file — avoids shell integration parsing the pipe chain
    local script_file="$BUFFER_DIR/$buffer_id.sh"
    cat > "$script_file" << EOF
#!/bin/bash
export __NEURAL_SUBPROCESS=1
export BUFFER_ID="$buffer_id"
$cmd
exit \$?
EOF
    chmod +x "$script_file"

    # Fork into detached subprocess with setsid (no terminal attached)
    (
        # Redirect stdin, stdout, stderr away from the terminal
        exec </dev/null
        exec >"$log_file" 2>&1

        # Set a marker so shell hooks don't fire on this subprocess
        export __NEURAL_SUBPROCESS=1
        export BUFFER_ID="$buffer_id"

        # Record start
        local start_epoch=$(date +%s)

        # Run the script file — not the raw command, so pipes/chains don't hit shell integration
        bash "$script_file" 2>&1
        local exit_code=$?

        local end_epoch=$(date +%s)
        local duration=$(( end_epoch - start_epoch ))

        # Write result
        cat > "$result_file" <<RESULT
exit_code=$exit_code
duration_sec=$duration
completed=$(date -u +%Y-%m-%dT%H:%M:%SZ)
RESULT

        # Update meta to completed
        sed -i "s/status=running/status=completed/" "$meta_file"
        echo "exit_code=$exit_code" >> "$meta_file"
    ) &

    local bg_pid=$!
    echo "$bg_pid" > "$pid_file"

    # Return immediately with PID and buffer ID
    echo "BUFFER_ID=$buffer_id"
    echo "PID=$bg_pid"
    echo "COMMAND=$cmd"
    echo "INFO=Forked to background. Use 'status $buffer_id' to check."
}

# ─── Check buffer status ────────────────────────────────────────────────────
status_buffer() {
    local buffer_id="$1"
    local meta_file="$BUFFER_DIR/$buffer_id.meta"
    local pid_file="$BUFFER_DIR/$buffer_id.pid"

    if [ ! -f "$meta_file" ]; then
        echo "STATUS=not_found"
        echo "BUFFER_ID=$buffer_id"
        return 1
    fi

    local status=$(grep "^status=" "$meta_file" | cut -d= -f2)
    local pid=""
    [ -f "$pid_file" ] && pid=$(cat "$pid_file")

    echo "BUFFER_ID=$buffer_id"
    echo "STATUS=$status"
    echo "PID=$pid"

    # If status is running, check if process still exists
    if [ "$status" = "running" ] && [ -n "$pid" ]; then
        if ! kill -0 "$pid" 2>/dev/null; then
            # Process died without updating meta — orphan
            echo "WARNING=Process vanished, may have been reaped"
            echo "STATUS=orphan"
        fi
    fi

    echo "META_FILE=$meta_file"
    cat "$meta_file" | grep -v "^status=" | grep -v "^buffer_id=" | grep -v "^command="
}

# ─── Get buffer result ──────────────────────────────────────────────────────
result_buffer() {
    local buffer_id="$1"
    local result_file="$BUFFER_DIR/$buffer_id.result"
    local log_file="$BUFFER_DIR/$buffer_id.log"

    if [ ! -f "$result_file" ]; then
        echo "STATUS=not_completed"
        echo "BUFFER_ID=$buffer_id"
        return 1
    fi

    cat "$result_file"
    echo "---"
    echo "LOG_FILE=$log_file"
    echo "LOG_SIZE=$(wc -c < "$log_file" 2>/dev/null || echo 0)"
}

# ─── List all buffers ───────────────────────────────────────────────────────
list_buffers() {
    local active=0
    local completed=0

    for meta in "$BUFFER_DIR"/*.meta; do
        [ ! -f "$meta" ] && continue
        local id=$(basename "$meta" .meta)
        local status=$(grep "^status=" "$meta" | cut -d= -f2)
        local cmd=$(grep "^command=" "$meta" | cut -d= -f2-)
        local started=$(grep "^started=" "$meta" | cut -d= -f2)

        if [ "$status" = "running" ]; then
            echo "🟡 $id | $cmd | started=$started"
            active=$(( active + 1 ))
        else
            echo "🟢 $id | $cmd | started=$started"
            completed=$(( completed + 1 ))
        fi
    done

    echo "---"
    echo "ACTIVE=$active"
    echo "COMPLETED=$completed"
}

# ─── Reap completed buffers (clean up old logs) ────────────────────────────
reap_buffers() {
    local count=0
    for meta in "$BUFFER_DIR"/*.meta; do
        [ ! -f "$meta" ] && continue
        local status=$(grep "^status=" "$meta" | cut -d= -f2)
        if [ "$status" = "completed" ]; then
            local id=$(basename "$meta" .meta)
            rm -f "$BUFFER_DIR/$id"*.{meta,log,result,pid} 2>/dev/null
            count=$(( count + 1 ))
        fi
    done
    echo "REAPED=$count"
}

# ─── Main dispatch ──────────────────────────────────────────────────────────
case "${1:-help}" in
    predict)
        predict_hang "${2:-}"
        ;;
    exec)
        exec_buffer "${2:-}"
        ;;
    status)
        status_buffer "${2:-}"
        ;;
    result)
        result_buffer "${2:-}"
        ;;
    list)
        list_buffers
        ;;
    reap)
        reap_buffers
        ;;
    *)
        echo "Hang Buffer — Detached subprocess execution"
        echo ""
        echo "Usage:"
        echo "  bash hang-buffer.sh predict \"<cmd>\"   # Predict if command will hang"
        echo "  bash hang-buffer.sh exec \"<cmd>\"       # Execute in detached buffer"
        echo "  bash hang-buffer.sh status <id>         # Check buffer status"
        echo "  bash hang-buffer.sh result <id>         # Get buffer result"
        echo "  bash hang-buffer.sh list                # List all buffers"
        echo "  bash hang-buffer.sh reap                # Clean completed buffers"
        ;;
esac