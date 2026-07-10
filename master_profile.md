# 🧠 Master Profile — Neural Session Identity

> **Purpose**: This file is the first-read entry point for any new Cline session.  
> It defines the workspace identity, active projects, and links to rehydration.

---

## Session Identity

| Field | Value |
|-------|-------|
| **Workspace** | `/root` |
| **Mnemonic** | `AXON-1` — Primary workspace server |
| **Core Model** | DeepSeek V4 Flash (1M context window) |
| **Safety System** | Neural Session Safety v1.0 |
| **Session State** | `/root/.session-state/` |
| **Checkpoint** | `/root/.session-state/checkpoint.json` |
| **Crash Log** | `/root/.session-state/crash-log.ndjson` |
| **Failure Points** | `/root/.session-state/failure-points.json` |

---

## 🚀 Session Startup Procedure

Every new Cline session should follow this entry point hierarchy:

```
1. .clinerules            ← loaded automatically (contains recovery directives)
2. master_profile.md      ← you are here (session identity, workspace context)
3. rehydration.md         ← source this to restore last checkpoint context
   source /root/rehydration.md
```

---

## 🔄 Rehydration

After a session crash or hang, run:
```bash
source /root/rehydration.md
```
This reads the checkpoint, crash log, and failure points database to restore full context — no need to re-query for project details.

---

## 🛡️ Safety System Overview

The **Neural Session Safety System** provides:

| Component | File | What it does |
|-----------|------|-------------|
| Rules | `/root/Cline/Rules/session-safety.md` | Behavioral rulebook for Cline |
| Recovery | `/root/Cline/Rules/recovery-protocols.md` | Step-by-step crash recovery (6 protocols) |
| Pre-Guard | `/root/Cline/Hooks/pre-tool-guard.sh` | Computes crash proximity before each tool call |
| Post-State | `/root/Cline/Hooks/post-tool-state.sh` | Logs state, crash log, updates failure points |
| Handoff | `/root/Cline/Hooks/generate-handoff.sh` | Generates checkpoint with full context snapshot |
| Rehydration | `/root/rehydration.md` | Restores context from checkpoint on new session |

---

## Active Projects

> Edit this section to list current project(s), goals, and relevant file paths.

- _(none currently set; update manually)_

---

## Configuration

| Setting | Value | Location |
|---------|-------|----------|
| Shell integration timeout | **60,000ms** (was 10,000ms) | `globalState.json` |
| Terminal output line limit | **3,000** (was 1,500) | `globalState.json` |
| Context window | 1,048,576 tokens | Model limit |