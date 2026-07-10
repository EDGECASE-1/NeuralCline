# 🧠 Neural Session Safety System — Rulebook

> **Purpose**: Complete behavioral rules for Cline to maintain session safety,  
> detect crash proximity, self-heal, and generate contextual handoffs.

---

## 1. CORE PRINCIPLES

### 1.1 Session Identity
- Every session has a UUID stored in `/root/.session-state/current-state.json` under `session_id`
- Every tool call increments `tool_call_count` in state
- Before any terminal command, check `context_usage_pct` in state

### 1.2 Context Window Management
- The model has 1,048,576 token context window
- **Warning threshold**: 60% usage → start truncating/paginating output
- **Critical threshold**: 80% usage → save checkpoint before every tool call
- **Danger threshold**: 90% usage → refuse large operations, suggest handoff

### 1.3 Output Size Management
- If command output is expected > 500 lines, pipe through `head -200` or `grep`
- If reading files, use `head -50` or `tail -50` for large files
- Never read files > 500KB without explicit permission

---

## 2. CRASH PROXIMITY DETECTION

### 2.1 Known High-Risk Patterns
Commands that historically cause crashes:
1. `find` on large directory trees (bolix-workspace, node_modules)
2. `cat` on files > 2MB (logs, archives)
3. Recursive grep on large directories
4. `npm install` / `pip install` with large dependency trees
5. Commands producing > 2000 lines of stdout

### 2.2 Proximity Scoring
The system computes a crash proximity score (0-100) based on:
- **Command pattern match** (40%): Does this command match a historical failure?
- **Context usage** (25%): Is context > 60%?
- **Output size estimate** (20%): Will output be large?
- **File size** (15%): Are we operating on large files?

### 2.3 Proximity Thresholds
- **0-30**: Safe — proceed normally
- **30-60**: Caution — paginate output, save checkpoint
- **60-80**: Warning — save checkpoint, truncate output, consider nohup
- **80-100**: Danger — refuse operation, suggest session handoff instead

---

## 3. SELF-HEALING ACTIONS

### 3.1 Pre-Tool Guard (before every tool call)
1. Read `/root/.session-state/current-state.json`
2. Compute crash proximity score
3. If proximity > 60: save checkpoint first
4. If proximity > 80: warn user and suggest alternative approach

### 3.2 Post-Tool State Update (after every tool call)
1. Increment `tool_call_count` in state
2. Update `context_usage_pct` estimate
3. Log the command and its exit code to crash-log.ndjson
4. Update checkpoint.json with the current tool's result

### 3.3 Command Timeout Handling
- Commands > 30 seconds should use `timeout` wrapper
- Commands > 100 lines output should pipe through `head`
- If a command times out, log to crash log and retry with reduced scope

---

## 4. SESSION HANDOFF GENERATION

### 4.1 When to Generate a Handoff
1. Before any operation with proximity score > 70
2. When context usage exceeds 85%
3. Before a known long-running command that may cause session timeout
4. Every 50 tool calls as a safety checkpoint

### 4.2 Handoff Contents
The handoff snapshot at `/root/.session-state/checkpoint.json` contains:
- `session_id`: UUID of the current session
- `timestamp`: ISO-8601 timestamp
- `total_tool_calls`: Total tool calls in this session
- `success_rate`: Percentage of successful tool calls
- `context_usage_pct`: Estimated context usage
- `last_command`: The most recent command executed
- `last_result`: Summary of the last result
- `active_goals`: Array of current active goals
- `next_steps`: Array of planned next steps
- `file_scope`: Files that were being worked on
- `crash_proximity_score`: Proximity score at handoff time
- `failure_point_match`: If proximity was high, which failure point matched

---

## 5. RECOVERY PROTOCOLS

When a new session detects a checkpoint from a previous session:
1. Read checkpoint.json
2. Display session summary to user
3. Suggest `source /root/rehydration.md` for full restoration
4. Present active goals and next steps from checkpoint
5. Proceed with the next step automatically

---

## 6. NEURAL CRASH LOG

### 6.1 Log Format (NDJSON)
Each line in `/root/.session-state/crash-log.ndjson`:
```json
{
  "timestamp": "ISO-8601",
  "session_id": "uuid",
  "command": "the command that was run",
  "exit_code": 0 or non-zero,
  "context_usage_pct": 45,
  "output_size_lines": 200,
  "file_scope": ["/path/to/files"],
  "tool_call_number": 42,
  "crash_proximity_score": 35,
  "duration_ms": 1234,
  "error": "optional error message"
}
```

### 6.2 Failure Points Deduplication
`/root/.session-state/failure-points.json` aggregates crash log entries:
- Groups by command pattern (normalized)
- Tracks: `pattern`, `count`, `avg_proximity`, `max_proximity`, `weight`, `last_seen`
- Weight formula: `count * (avg_proximity / 100) * recency_factor`

---

## 7. ENTRY POINT HIERARCHY

```
New Session
    │
    ├── 1. `.clinerules` loaded automatically
    │
    ├── 2. Read `/root/master_profile.md` (session identity)
    │
    ├── 3. Check if `/root/rehydration.md` exists
    │        ├── Yes → source it → restore context
    │        └── No → fresh session
    │
    └── 4. Every tool call → pre-tool guard → post-tool update