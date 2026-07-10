# 🧠 NeuralCline — Neural Session Safety System

> **Codename:** EDGECASE  
> **Version:** 1.0.1  
> **License:** MIT (core) / Commercial (patches)  
> **Tagline:** *The boundary no system anticipates.*

---

## ❓ The Problem

Every Cline user has felt this:

```
Session crash — context lost
▸ 45 minutes of tool calls gone
▸ Python output never finished
▸ Terminal integration timed out
▸ Command hangs with no trace
▸ Start from scratch
```

**The root cause:** Cline's `python3 -c "..."` inline Python execution pattern. The shell integration timeout (10s default) fires before `python3 -c` closes its stdout stream cleanly. Result: **session crash, context loss, frustration.**

NeuralCline fixes this at the architectural level — with **three compute engines, five safety layers, and automatic shell-level hang detection.**

---

## 💡 The Solution

NeuralCline provides **five layers of protection** that wrap every Cline session:

```
┌─────────────────────────────────────────────────────────────────┐
│                    NeuralCline EDGECASE v1.0.1                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: 🛡️ Crash Prevention (Pre-Tool Guard)                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Computes crash proximity score (0-100) before every    │   │
│  │  tool call. Auto-detects stale state >15min → runs      │   │
│  │  diagnostic. Auto-saves checkpoint when risk > 60%.     │   │
│  │  Includes ⏱️ timing proximity + 🧬 self-learning heal.  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Layer 2: 💾 State Persistence (Post-Tool State)                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Logs every tool call to a neural crash log. Tracks     │   │
│  │  execution timing, failure patterns with weighted       │   │
│  │  scoring, deduplicates, recency-ranks, auto-trims.      │   │
│  │  Includes ⏱️ timing recording + 🧬 memory snapshot.     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Layer 3: 🔄 Session Continuity (Rehydration)                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  One command restores full session context: last        │   │
│  │  command, active goals, next steps, failure history,    │   │
│  │  crash log, timing metrics, organism memory.            │   │
│  │  Pick up exactly where you left off.                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Layer 4: 🔧 Auto Hang/Crash Detection (Shell Hooks)           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  DEBUG trap + PROMPT_COMMAND automatically capture      │   │
│  │  every command's execution time. Hangs >30s logged      │   │
│  │  with hang_detected flag. Crashes logged with exit      │   │
│  │  code. Self-learning snapshot every 5 commands.         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Layer 5: 🔍 Self-Diagnostic (21-Check Engine)                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  21 checks: hooks, state files, engines, timing health, │   │
│  │  EEF (Execution Emulation Factor), timeout proximity,   │   │
│  │  organism memory, shell hooks, Cline config.            │   │
│  │  Verdicts: STABLE / PROBABLE HANG.                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 One-Command Install

```bash
curl -fsSL https://raw.githubusercontent.com/EDGECASE-1/NeuralCline/main/install.sh | bash
```

Or with `git clone`:

```bash
git clone https://github.com/EDGECASE-1/NeuralCline.git /root/NeuralCline
bash /root/NeuralCline/install.sh
```

**What it does:**

| Step | Action |
|------|--------|
| 1 | Deploys 18+ core files to `/root/NeuralCline/` |
| 2 | Initializes session state directory |
| 3 | Creates Cline integration symlinks |
| 4 | Installs `.clinerules`, `.bashrc` hook, `rehydration.md` |
| 5 | Tunes `shellIntegrationTimeout` → **60s** (was 10s) |
| 6 | Tunes `terminalOutputLineLimit` → **3000** (was 1500) |
| 7 | Installs auto-init hook for terminal-level session recovery |
| 8 | Installs shell hooks for automatic hang/crash detection |
| 9 | Runs full sanity check — 20+ checks verified |

---

## 🔧 After Install

```bash
# Recover from any crash or hang:
source /root/rehydration.md

# Run a full system diagnostic (21 checks):
bash /root/NeuralCline/hooks/diagnose.sh

# Check timing state (EEF, timeout proximity):
python3 /root/NeuralCline/lib/timing_metrics.py read_timing

# Predict timeout for a specific command:
python3 /root/NeuralCline/lib/timing_metrics.py predict_timeout "<command>"

# Check self-learning organism health:
python3 /root/NeuralCline/lib/self_learning.py report

# View foresight predictions:
python3 /root/NeuralCline/lib/self_learning.py foresee

# Save a checkpoint manually:
bash /root/NeuralCline/hooks/generate-handoff.sh
```

Every new Cline session will automatically:
1. Run `source /root/rehydration.md` (via `.clinerules`)
2. Display session context — last command, goals, next steps
3. Route all Python operations through `state_engine.py` (crash-safe)
4. Detect stale state >15 minutes and auto-run diagnostic
5. Auto-capture command execution timing via shell hooks

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     NEURALCLINE EDGECASE v1.0.1                │
│                  Session Safety + Timing + Self-Learning       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PRE-TOOL GUARD (before every command)                  │   │
│  │  Step 1:    Stale state detection (hang diagnosis)       │   │
│  │  Step 1.5:  ⏱️ Timing proximity check (predict_timeout) │   │
│  │  Step 1.75: 🧬 Self-learning heal (foresee + adjust)    │   │
│  │  Step 2:    Crash proximity scoring (state_engine)       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  COMMAND EXECUTION                                      │   │
│  │  🔧 Shell hooks auto-capture timing + hangs + crashes   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  POST-TOOL STATE (after every command)                  │   │
│  │  Step 0:    ⏱️ Record execution timing (EEF update)     │   │
│  │  Step 0.5:  🧬 Self-learning snapshot (memory record)   │   │
│  │  Step 1:    Update state (context, tool calls)          │   │
│  │  Step 2:    Write crash log (if failure)                │   │
│  │  Step 3:    Update failure points (pattern analysis)    │   │
│  │  Step 4:    Generate checkpoint (persistence)           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  THREE ENGINE LAYERS:                                           │
│                                                                 │
│  📊 state_engine.py    → Session state, crash logs, checkpoints │
│  ⏱️  timing_metrics.py  → EEF, timeout prediction, timing hist  │
│  🧬  self_learning.py  → Memory, foresight, self-healing       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  SESSION STATE FILES (6 total):                                 │
│                                                                 │
│  /root/.session-state/                                          │
│  ├── current-state.json      ← Live session state              │
│  ├── checkpoint.json         ← Restorable checkpoint           │
│  ├── crash-log.ndjson        ← Structured crash events         │
│  ├── failure-points.json     ← Weighted failure patterns       │
│  ├── timing-history.json     ← Execution durations + EEF       │
│  └── session-memory.json     ← Organism memories + patterns    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 File Structure

```
/root/NeuralCline/
├── lib/
│   ├── state_engine.py          # Crash-safe Python operations (8 commands)
│   ├── timing_metrics.py        # Execution Emulation Factor + timeout prediction
│   └── self_learning.py         # Persistent memory, foresight, self-healing
├── hooks/
│   ├── pre-tool-guard.sh        # Crash proximity + timing check + self-learning heal
│   ├── post-tool-state.sh       # State logging + timing record + memory snapshot
│   ├── generate-handoff.sh      # Checkpoint generator
│   ├── diagnose.sh              # 21-check self-diagnostic engine
│   └── shell-hooks.sh           # Auto hang/crash detection at shell level
├── rules/
│   ├── session-safety.md        # Behavioral rulebook for Cline
│   └── recovery-protocols.md    # 8 crash recovery protocols (A-H)
├── docs/
│   ├── MANIFEST.md              # Full system documentation
│   └── TIMELINE.md              # Project roadmap
├── install.sh                   # One-command installer
├── master_profile.md            # Session identity profile
├── rehydration.md               # Shell-level context restoration
├── LICENSE                      # MIT + Commercial
└── README.md                    # This file
```

---

## 🔍 Self-Diagnostic System (21 Checks)

NeuralCline includes a **21-check diagnostic engine** that detects session hangs, stale state, missing hooks, timing degradation, and shell integration failures:

```bash
bash /root/NeuralCline/hooks/diagnose.sh
```

Sample output:

```
╔══════════════════════════════════════════════════════════════╗
║     🔍 NeuralCline Self-Diagnostic                          ║
╚══════════════════════════════════════════════════════════════╝

✅ VERDICT: SYSTEM STABLE

Summary: 16 passed, 1 warnings, 0 failures, 4 info

─── Detail ───
✅ State freshness — last updated 0min ago
✅ Hooks — all 3 hooks present and executable
✅ Symlinks — all 5 intact
✅ State engine — responds with 8 commands
✅ .clinerules — has rehydration directive
✅ Rehydration engine — present and executable
✅ .bashrc — auto-init hook installed
✅ auto-init.sh — present
✅ Session state files — all 4 present
⚠️  Shell integration — non-interactive shell
✅ Cline config — shellIntegrationTimeout=60000ms
✅ Failure patterns — tracking 19 crash events
✅ Timing engine — responds with 5 commands
✅ Timing history — 10 entries, 8 patterns, EEF=0.3
✅ EEF health — 0.3 (normal)
✅ Timeout proximity — 0/100 — safe
✅ Self-learning organism — alive and functional
✅ Session memory — 6 memories, 2 patterns, 0 healings
✅ Shell hooks — installed and active
```

Use `--quiet` for machine-readable output or `--json` for data pipeline integration:

```bash
bash /root/NeuralCline/hooks/diagnose.sh --quiet
bash /root/NeuralCline/hooks/diagnose.sh --json
```

---

## ⏱️ Timing Metrics & Execution Emulation Factor (EEF)

The NeuralCline Timing Metrics Engine tracks execution durations and computes a real-time **Execution Emulation Factor (EEF)** — a coefficient that measures how much slower operations are running compared to baseline:

| EEF Range | Status | Action |
|-----------|--------|--------|
| < 1.2 | ✅ Normal | Environment healthy |
| 1.2–1.8 | ⚠️ Moderate | Monitor execution |
| 1.8–2.5 | 🔶 Elevated | Paginate output, consider smaller steps |
| > 2.5 | 🔴 Critical | System severely degraded, fragment all operations |

```bash
# Check current timing state
python3 /root/NeuralCline/lib/timing_metrics.py read_timing

# Predict timeout risk for a specific command
python3 /root/NeuralCline/lib/timing_metrics.py predict_timeout "<command>"
```

---

## 🧬 Self-Learning Foresight Organism

NeuralCline includes a persistent **self-learning organism** that maintains:

- **Memory**: Full parameter snapshots per tool call (up to 1000), with temporal decay
- **Foresight**: Predictive insights using trend analysis (linear regression) and pattern matching
- **Self-Healing**: Auto-adjusts thresholds, tightens danger zones, saves checkpoints

```bash
# Check organism health
python3 /root/NeuralCline/lib/self_learning.py report

# View foresight predictions
python3 /root/NeuralCline/lib/self_learning.py foresee

# Take a manual memory snapshot
python3 /root/NeuralCline/lib/self_learning.py snapshot
```

The organism runs automatically:
- `heal` before every command — predicts risks, adjusts thresholds
- `snapshot` after every command — records all parameters to memory

Self-healing triggers when:
- EEF trending toward critical (>2.5) → tightens thresholds, generates checkpoint
- Timeout risk imminent (>60) → lowers timeout danger threshold
- Failure cascade detected (≥3 consecutive failures) → increases checkpoint frequency
- Context pressure high (>60%) → recommends handoff generation

---

## 🔧 Shell Hooks — Automatic Hang/Crash Detection

NeuralCline installs automatic shell-level hooks that capture **every command**:

```
DEBUG trap (pre-exec) → saves command + start timestamp
PROMPT_COMMAND (post-exec) → logs duration, detects hangs/crashes
```

| Detection | Threshold | What Gets Logged |
|-----------|-----------|------------------|
| ⏱️ Hang | > 30 seconds | `hang_detected: 1` + duration in crash-log.ndjson |
| 🛑 Crash | exit code != 0 | `crash_detected: 1` + exit code in crash-log.ndjson |
| 📊 Timing | Every command | Duration, pattern, EEF update in timing-history.json |
| 🧬 Memory | Every 5 commands | Snapshot in session-memory.json |

To verify hooks are active:
```bash
echo $__NEURAL_HOOKS_INSTALLED
# Should output "1"
```

---

## 📊 Crash Proximity Scoring

Before every tool call, NeuralCline computes a risk score (0-100):

| Factor | Weight | What it checks |
|--------|--------|---------------|
| Historical failures | 40% | Matches command against known crash patterns |
| Context saturation | 25% | How full is your context window (>60% = risky) |
| Command size | 20% | Long commands with large output risk timeout |
| Risk patterns | 15% | `find`, `grep -r`, `cat *.log`, `npm install` |

**Thresholds:**

| Score | Action |
|-------|--------|
| 0-30 | ✅ Safe — proceed normally |
| 31-60 | ⚠️ Caution — consider paginating output |
| 61-80 | 🚨 Warning — auto-save checkpoint |
| 81-100 | 🔴 Danger — generate handoff, refuse operation |

---

## 🛡 Crash Recovery Protocols

| Protocol | When | Command |
|----------|------|---------|
| **A** | Session hang | `source /root/rehydration.md` |
| **B** | Context full | `bash /root/NeuralCline/hooks/generate-handoff.sh` |
| **C** | Output fail | `tail -5 /root/.session-state/crash-log.ndjson` |
| **D** | Crash | `source /root/rehydration.md` |
| **E** | Infinite loop | `bash /root/NeuralCline/hooks/generate-handoff.sh` |
| **F** | Big file | `ls -lh <file>` then `head -100 <file>` |
| **G** | Suspected hang / stale state | `bash /root/NeuralCline/hooks/diagnose.sh` |
| **H** | Timing degradation | `python3 /root/NeuralCline/lib/timing_metrics.py read_timing` |

Full details: `/root/NeuralCline/rules/recovery-protocols.md`

---

## 🧪 State Engine Commands

All Python operations route through a single crash-safe library:

```bash
python3 /root/NeuralCline/lib/state_engine.py <command> [args...]
```

| Command | Purpose |
|---------|---------|
| `update_state` | Record tool call metrics |
| `write_crash_log` | Append crash log entry |
| `update_failure_points` | Re-detect failure patterns |
| `compute_proximity` | Get crash risk score |
| `read_checkpoint` | View current checkpoint |
| `generate_checkpoint` | Save session snapshot |
| `check_checkpoint` | Quick checkpoint existence check |
| `read_failure_points` | Show top failure patterns |
| `help` | List all commands |

---

## 🔬 The Key Innovation

**Crash-Free Python Execution**

The root cause of Cline session crashes is `python3 -c "import json; ..."` — inline Python with shell integration. The stdout stream doesn't close cleanly, triggering the 10s timeout.

**NeuralCline fixes this** by using a dedicated Python library file (`state_engine.py`) executed as:

```bash
python3 /path/to/lib.py <command> [args...]
```

This has a stable, predictable stdout stream. All state operations route through this single file. **No more `python3 -c` crashes.**

---

## ⚙️ Configuration

Settings auto-tuned in Cline's `globalState.json`:

| Setting | Before | After | Why |
|---------|--------|-------|-----|
| `shellIntegrationTimeout` | 10,000ms | **60,000ms** | Give long-running commands time to finish |
| `terminalOutputLineLimit` | 1,500 | **3,000** | Keep more output visible before truncation |

Backup created at: `<globalState.json>.backup`

---

## 🚀 Launch Automation

The launch pipeline is fully automated via `gh` CLI. No browser needed.

### Quick Start

```bash
# Step 1: Create GitHub Discussion, Issues, Pages, and launch content
bash /root/NeuralCline/launch/automation/02-launch-orchestrator.sh

# Step 2: Prepare external platform content (Reddit, HN, PH)
bash /root/NeuralCline/launch/automation/03-external-launch.sh

# Step 3: Check real-time metrics
bash /root/NeuralCline/launch/automation/04-check-metrics.sh
```

### What It Creates

| Channel | Tool | Automation |
|---------|------|-----------|
| GitHub Discussion | `gh api graphql` | ✅ Fully automated |
| GitHub Issues (6) | `gh issue create` | ✅ Fully automated |
| GitHub Pages | `gh api pages` | ✅ Fully automated |
| Reddit | `gh issue create` (content) + PRAW | ✅ Content prepared, OAuth needed |
| Hacker News | `gh issue create` (content) | ✅ Content prepared, manual submit |
| Product Hunt | `gh issue create` (content) | ✅ Content prepared, manual submit |

### Files

- `launch/automation/01-create-discussion.sh` — Creates the launch announcement
- `launch/automation/02-launch-orchestrator.sh` — Full GH pipeline (Discussion, Issues, Pages)
- `launch/automation/03-external-launch.sh` — External platform content preparation
- `launch/automation/04-check-metrics.sh` — Real-time metrics dashboard
- `launch/automation/create_discussion.py` — Python GraphQL client for Discussions
- `launch/automation/discussion-body.md` — Launch post body content
- `launch/launch_reddit.py` — Reddit posting script (requires OAuth setup)
- `launch/EXECUTIVE_BRIEF.md` — Business case documentation
- `launch/MARKET_MAP.md` — Market analysis ($12.9B TAM)
- `launch/PROJECTION_METRICS.md` — Growth projections
- `launch/LAUNCH_POSTS.md` — All launch post content

---

## 🧠 EDGECASE — The Mission

NeuralCline is the first release from **EDGECASE**, a project dedicated to documenting and fixing the unanticipated failure modes of AI coding tools.

We're building a **Glitchware Library** — a catalog of known model glitches, their root causes, and production-ready patches. The `python3 -c` crash is Cline Glitch #1.

---

## 📄 License

- **Core library** (`state_engine.py`, `timing_metrics.py`, `self_learning.py`, hooks, rules): MIT License  
- **Patches and commercial extensions**: Proprietary, available via Patch Pack

---

## 🔗 Links

- **Repository:** [github.com/EDGECASE-1/NeuralCline](https://github.com/EDGECASE-1/NeuralCline)
- **Install:** `curl -fsSL https://raw.githubusercontent.com/EDGECASE-1/NeuralCline/main/install.sh | bash`
- **Recovery:** `source /root/rehydration.md`
- **Diagnostic:** `bash /root/NeuralCline/hooks/diagnose.sh`
- **Timing:** `python3 /root/NeuralCline/lib/timing_metrics.py read_timing`
- **Organism:** `python3 /root/NeuralCline/lib/self_learning.py report`
- **Project roadmap:** [`docs/TIMELINE.md`](docs/TIMELINE.md)

---

*Built by EDGECASE — the boundary no system anticipates.*