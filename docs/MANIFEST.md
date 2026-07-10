# 🧠 NeuralCline — Neural Session Safety System

> **Version:** 1.0.0  
> **Codename:** EDGECASE  
> **License:** Proprietary / MIT Core (TBD)  
> **Repository:** Private — `EDGECASE/NeuralCline`  

## What It Is

NeuralCline is a **neural session safety system** for [Cline](https://cline.bot) (VS Code AI coding assistant). It solves the fundamental problem of session crashes, context loss, and terminal output capture failures that plague large-model coding sessions.

## The Problem

Cline sessions crash when:
1. **Shell integration timeout** — `python3 -c "..."` inline calls timeout before stdout closes
2. **Large terminal output** — 1500+ line outputs overflow the context window
3. **Context window saturation** — tool calls accumulate tokens until truncation
4. **Session hang** — no recovery mechanism, user must restart from scratch

## The Solution

NeuralCline provides **three layers of protection**:

### Layer 1: Crash Prevention (Pre-Tool Guard)
- Computes a **crash proximity score** (0-100) before every tool call
- Scores are based on: historical failure patterns (40%), context usage (25%), output size (20%), known risky commands (15%)
- Auto-saves checkpoints when proximity exceeds 60%
- Refuses operations when proximity exceeds 80%

### Layer 2: State Persistence (Post-Tool State)
- Updates session state after every tool call
- Writes to a neural crash log (`crash-log.ndjson`) with all metadata
- Deduplicates failure patterns with weighted recency scoring
- Maintains a failure points database (`failure-points.json`)

### Layer 3: Session Continuity (Rehydration)
- `master_profile.md` — session identity and workspace context
- `rehydration.md` — one-command context restoration from last checkpoint
- Generates full handoff snapshots with active goals, next steps, and crash history
- Auto-inits via `.clinerules` on every new session

## Architecture

```
                    ┌──────────────────────────┐
                    │  .clinerules (auto-load) │
                    │  "source rehydration.md" │
                    └──────────┬───────────────┘
                               │
                    ┌──────────▼───────────────┐
                    │  state_engine.py         │
                    │  (crash-safe Python lib) │
                    └──────────┬───────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
  ┌─────▼──────┐       ┌──────▼──────┐       ┌───────▼──────┐
  │ Pre-Tool   │       │ Post-Tool   │       │ Session     │
  │ Guard      │       │ State       │       │ Handoff     │
  │ (proximity)│       │ (logging)   │       │ (checkpoint)│
  └─────┬──────┘       └──────┬──────┘       └───────┬──────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                    ┌──────────▼───────────────┐
                    │  .session-state/         │
                    │  ├── current-state.json  │
                    │  ├── checkpoint.json     │
                    │  ├── crash-log.ndjson    │
                    │  └── failure-points.json │
                    └──────────────────────────┘
```

## Key Innovation: Crash-Free Python Execution

The **root cause** of Cline session crashes is `python3 -c "import json; ..."` — inline Python with shell integration. The stdout stream from `python3 -c` doesn't close cleanly, causing the shell integration timeout to fire.

**NeuralCline fixes this** by using a dedicated Python library file (`state_engine.py`) executed as `python3 /path/to/lib.py` — which has a stable, predictable stdout stream. All state operations route through this single file.

## File Structure

```
/root/NeuralCline/
├── lib/
│   └── state_engine.py          # Crash-safe Python operations library
├── hooks/
│   ├── pre-tool-guard.sh        # Pre-tool proximity detection
│   ├── post-tool-state.sh        # Post-tool state logging
│   └── generate-handoff.sh       # Checkpoint generator
├── rules/
│   ├── session-safety.md         # Safety rulebook
│   └── recovery-protocols.md     # Crash recovery procedures
├── session-state/                # (symlink to /root/.session-state)
│   ├── current-state.json
│   ├── checkpoint.json
│   ├── crash-log.ndjson
│   └── failure-points.json
├── docs/
│   └── MANIFEST.md               # This file
├── install.sh                    # One-command installer
└── README.md                     # Quick-start guide
```

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/null-parse/NeuralCline/main/install.sh | bash
```

Or manually:

```bash
git clone https://github.com/null-parse/NeuralCline.git /root/NeuralCline
bash /root/NeuralCline/install.sh
```

## Configuration

Settings in Cline's `globalState.json` are auto-tuned:

| Setting | Before | After |
|---------|--------|-------|
| `shellIntegrationTimeout` | 10,000ms | **60,000ms** |
| `terminalOutputLineLimit` | 1,500 | **3,000** |

## Recovery

After any session crash or hang:

```bash
source /root/rehydration.md
```

This restores full context — last command, active goals, next steps, failure history.

---

*Built by EDGECASE — the boundary no system anticipates.*
