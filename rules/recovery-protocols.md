# 🔧 Recovery Protocols — Step-by-Step Crash Recovery

> **Purpose**: Defines exact recovery procedures for each type of session failure.  
> Follow these steps when a session hangs, crashes, or loses context.

---

## Protocol A: Session Hang After Heavy Command

**Symptoms**: Terminal command completed but Cline didn't respond, or response was truncated.

**Steps**:
1. **Check terminal state**:
   ```bash
   ls -la /root/.session-state/checkpoint.json
   ```
2. **Read checkpoint**:
   ```bash
   python3 -c "import json; print(json.dumps(json.load(open('/root/.session-state/checkpoint.json')), indent=2))"
   ```
3. **Restore context**:
   ```bash
   source /root/rehydration.md
   ```
4. **Resume from last known state** — the checkpoint shows the last command, goals, and next steps.

---

## Protocol B: Context Window Overflow

**Symptoms**: Cline starts truncating responses, losing track of earlier context.

**Steps**:
1. **Check context usage**:
   ```bash
   python3 -c "import json; s=json.load(open('/root/.session-state/current-state.json')); print(f\"Context: {s.get('context_usage_pct',0)}%\")"
   ```
2. **If > 80%**: Generate a handoff immediately:
   ```bash
   bash /root/Cline/Hooks/generate-handoff.sh
   ```
3. **Save checkpoint**:
   ```bash
   cp /root/.session-state/checkpoint.json /root/.session-state/checkpoint.backup.json
   ```
4. **Start new session** and run:
   ```bash
   source /root/rehydration.md
   ```

---

## Protocol C: Terminal Output Capture Failure

**Symptoms**: Command executed but output shows "could not be captured".

**Steps**:
1. **Check crash log**:
   ```bash
   tail -5 /root/.session-state/crash-log.ndjson | python3 -m json.tool
   ```
2. **Re-run with output capture**:
   - Use `timeout 30s` wrapper
   - Pipe through `head -100`
   - Redirect stderr to stdout: `2>&1`
3. **If still failing**, run the command in a separate terminal and paste output manually.

---

## Protocol D: Session Crash / Unexpected Termination

**Symptoms**: Cline session ended unexpectedly, new session started.

**Steps**:
1. **Check for checkpoint**:
   ```bash
   if [ -f /root/.session-state/checkpoint.json ]; then echo "CHECKPOINT EXISTS"; else echo "NO CHECKPOINT"; fi
   ```
2. **Run rehydration**:
   ```bash
   source /root/rehydration.md
   ```
3. **Review failure points**:
   ```bash
   python3 -c "import json; fps=json.load(open('/root/.session-state/failure-points.json')); [print(f\"{p['pattern'][:60]} (weight={p['weight']:.0f})\") for p in sorted(fps.get('failure_points',[]), key=lambda x:x.get('weight',0), reverse=True)[:5]]"
   ```
4. **Resume work** from the next steps listed in the checkpoint.

---

## Protocol E: Auto-Approval Loop / Infinite Tool Calls

**Symptoms**: Cline enters a loop of repeated tool calls without progress.

**Steps**:
1. **Check tool call count**:
   ```bash
   python3 -c "import json; s=json.load(open('/root/.session-state/current-state.json')); print(f\"Tool calls: {s.get('tool_call_count',0)}\")"
   ```
2. **If > 50 calls without checkpoint**, force a handoff:
   ```bash
   bash /root/Cline/Hooks/generate-handoff.sh
   ```
3. **Review last 5 crash log entries** for patterns:
   ```bash
   tail -5 /root/.session-state/crash-log.ndjson
   ```
4. **Adjust approach** — reduce scope, paginate output, or break task into smaller steps.

---

## Protocol F: File Size Overflow

**Symptoms**: Reading a file causes context overflow or slow response.

**Steps**:
1. **Check file size**:
   ```bash
   ls -lh <filepath>
   ```
2. **If > 500KB**, read only portions:
   ```bash
   head -100 <filepath>
   tail -100 <filepath>
   ```
3. **Log the incident** to crash log for future proximity detection.

---

## Quick Reference Card

| Symptom | Protocol | First Action |
|---------|----------|-------------|
| Session hang | A | `source /root/rehydration.md` |
| Context overflow | B | Check `context_usage_pct` |
| Output capture fail | C | Check crash log, re-run with head |
| Session crash | D | `source /root/rehydration.md` |
| Infinite loop | E | Force handoff, review patterns |
| File too large | F | `ls -lh`, read in chunks |
| Suspected hang / stale state | G | `bash /root/NeuralCline/hooks/diagnose.sh` |

---

## Protocol G: Self-Diagnostic

**Symptoms**: Session feels wrong — slow, unresponsive, stale state, or you suspect a hang happened.

**Steps**:
1. **Run the diagnostic**:
   ```bash
   bash /root/NeuralCline/hooks/diagnose.sh
   ```
2. **Interpret the verdict**:
   - `PROBABLE HANG` — state stale >60min, run rehydration
   - `SYSTEM STABLE` — all checks pass, look elsewhere
3. **Use `--json` for data pipeline integration**:
   ```bash
   bash /root/NeuralCline/hooks/diagnose.sh --json
   ```
4. **Auto-detection**: `pre-tool-guard.sh` now auto-runs `diagnose.sh` in `--quiet` mode whenever state is stale >15 minutes. The diagnostic is logged to `crash-log.ndjson` before any proximity check.
5. **Review logs**:
   ```bash
   bash /root/NeuralCline/hooks/diagnose.sh --quiet
   # diagnose_checks=14 diagnose_pass=9 diagnose_warn=1 diagnose_fail=1
   ```
6. **Recover**: If hang is confirmed:
   ```bash
   source /root/rehydration.md
   ```
