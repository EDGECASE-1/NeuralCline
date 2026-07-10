# 🧠 NeuralCline — Neural Session Safety System

> **Codename:** EDGECASE  
> **Version:** 1.0.0  
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
▸ Start from scratch
```

**The root cause:** Cline's `python3 -c "..."` inline Python execution pattern. The shell integration timeout (10s default) fires before `python3 -c` closes its stdout stream cleanly. Result: **session crash, context loss, frustration.**

NeuralCline fixes this at the architectural level.

---

## 💡 The Solution

NeuralCline provides **four layers of protection** that wrap every Cline session:

```
┌───────────────────────────────────────────────────────────────┐
│                    NeuralCline EDGECASE                       │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 1: 🛡️ Crash Prevention (Pre-Tool Guard)               │
│  ┌───────────────────────────────────────────────────────┐    │
│  │  Computes crash proximity score (0-100) before every  │    │
│  │  tool call. Auto-detects stale state >15min → runs    │    │
│  │  diagnostic. Auto-saves checkpoint when risk > 60%.   │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                               │
│  Layer 2: 💾 State Persistence (Post-Tool State)              │
│  ┌───────────────────────────────────────────────────────┐    │
│  │  Logs every tool call to a neural crash log. Tracks   │    │
│  │  failure patterns with weighted scoring, deduplicates,│    │
│  │  recency-ranks, auto-trims to 1000 entries.           │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                               │
│  Layer 3: 🔄 Session Continuity (Rehydration)                 │
│  ┌───────────────────────────────────────────────────────┐    │
│  │  One command restores full session context: last      │    │
│  │  command, active goals, next steps, failure history,  │    │
│  │  crash log. Pick up exactly where you left off.       │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                               │
│  Layer 4: 🔍 Self-Diagnostic (Diagnose Engine)                │
│  ┌───────────────────────────────────────────────────────┐    │
│  │  14-check system health scan: hooks, state files,     │    │
│  │  Python lib, checkpoint integrity, auto-init, stale   │    │
│  │  state detection. Verdicts: STABLE / PROBABLE HANG.   │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## 🚀 One-Command Install

```bash
curl -fsSL https://raw.githubusercontent.com/null-parse/NeuralCline/main/install.sh | bash
```

Or with `git clone`:

```bash
git clone https://github.com/null-parse/NeuralCline.git /root/NeuralCline
bash /root/NeuralCline/install.sh
```

**What it does:**

| Step | Action |
|------|--------|
| 1 | Deploys 15 core files to `/root/NeuralCline/` |
| 2 | Initializes session state directory |
| 3 | Creates Cline integration symlinks |
| 4 | Installs `.clinerules`, `.bashrc` hook, `rehydration.md` |
| 5 | Tunes `shellIntegrationTimeout` → **60s** (was 10s) |
| 6 | Tunes `terminalOutputLineLimit` → **3000** (was 1500) |
| 7 | Installs auto-init hook for terminal-level session recovery |
| 8 | Runs full sanity check — 22 files verified |

---

## 🔧 After Install

```bash
# Recover from any crash or hang:
source /root/rehydration.md

# Run a full system diagnostic:
bash /root/NeuralCline/hooks/diagnose.sh

# Save a checkpoint manually:
bash /root/NeuralCline/hooks/generate-handoff.sh

# Check your crash proximity:
bash /root/NeuralCline/hooks/pre-tool-guard.sh "<command>"
```

Every new Cline session will automatically:
1. Run `source /root/rehydration.md` (via `.clinerules`)
2. Display session context — last command, goals, next steps
3. Route all Python operations through `state_engine.py` (crash-safe)
4. Detect stale state >15 minutes and auto-run diagnostic

---

## 🏗 Architecture

```
                     ┌──────────────────────────┐
                     │  .clinerules (auto-load) │
                     │  "source rehydration.md" │
                     └──────────┬───────────────┘
                                │
                     ┌──────────▼───────────────┐
                     │  state_engine.py         │
                     │  (crash-safe Python lib) │
                     │  9 commands · 453 lines  │
                     └──────────┬───────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
  ┌─────▼──────┐       ┌───────▼──────┐       ┌───────▼──────┐
  │ Pre-Tool   │       │ Post-Tool    │       │ Self-        │
  │ Guard      │       │ State        │       │ Diagnostic   │
  │ (proximity │       │ (logging)    │       │ (diagnose.sh)│
  │ + stale    │       │              │       │ 14 checks    │
  │ detection) │       │              │       │              │
  └─────┬──────┘       └───────┬──────┘       └───────┬──────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                     ┌──────────▼───────────────┐
                     │  .session-state/         │
                     │  ├── current-state.json  │
                     │  ├── checkpoint.json     │
                     │  ├── crash-log.ndjson    │
                     │  └── failure-points.json │
                     └──────────────────────────┘
```

---

## 📦 File Structure

```
/root/NeuralCline/
├── lib/
│   └── state_engine.py          # Crash-safe Python operations (9 commands)
├── hooks/
│   ├── pre-tool-guard.sh        # Crash proximity detection + stale state
│   ├── post-tool-state.sh       # State logging + failure tracking
│   ├── generate-handoff.sh      # Checkpoint generator
│   └── diagnose.sh              # 14-check self-diagnostic engine (465 lines)
├── rules/
│   ├── session-safety.md        # Behavioral rulebook for Cline
│   └── recovery-protocols.md    # 7 crash recovery protocols (A-G)
├── docs/
│   ├── MANIFEST.md              # Full system documentation
│   └── TIMELINE.md              # Project roadmap
├── install.sh                   # One-command installer (437 lines)
├── master_profile.md            # Session identity profile
├── rehydration.md               # Shell-level context restoration
├── LICENSE                      # MIT + Commercial
└── README.md                    # This file
```

---

## 🔍 Self-Diagnostic System

NeuralCline includes a **14-check diagnostic engine** that detects session hangs, stale state, missing hooks, and shell integration failures:

```bash
bash /root/NeuralCline/hooks/diagnose.sh
```

Sample output:

```
╔══════════════════════════════════════════════════════════════╗
║     🔍 SELF-DIAGNOSTIC — NeuralCline EDGECASE               ║
╚══════════════════════════════════════════════════════════════╝

✅ [PASS] state_engine.py exists + executable
✅ [PASS] state_engine.py has 9 commands
✅ [PASS] pre-tool-guard.sh exists
✅ [PASS] post-tool-state.sh exists
✅ [PASS] generate-handoff.sh exists
✅ [PASS] diagnose.sh self-reference
✅ [PASS] current-state.json readable
✅ [PASS] crash-log.ndjson readable
✅ [PASS] auto-init.sh exists + uses state_engine.py
✅ [PASS] .clinerules has Protocol G
⚠️  [WARN] Non-interactive shell (expected in code-server)
ℹ️  [INFO] Checkpoint exists
ℹ️  [INFO] Recovery protocols file has 7 protocols
ℹ️  [INFO] Master profile available

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 VERDICT: SYSTEM STABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Use `--quiet` for machine-readable output or `--json` for data pipeline integration:

```bash
bash /root/NeuralCline/hooks/diagnose.sh --quiet
# diagnose_checks=14  diagnose_pass=9  diagnose_warn=1
# diagnose_fail=1     diagnose_info=3  diagnose_verdict=STABLE

bash /root/NeuralCline/hooks/diagnose.sh --json
```

**Auto-detection:** The pre-tool guard automatically runs `diagnose.sh --quiet` whenever state is stale >15 minutes, logging results to the crash log before any proximity check.

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

## 🧠 EDGECASE — The Mission

NeuralCline is the first release from **EDGECASE**, a project dedicated to documenting and fixing the unanticipated failure modes of AI coding tools.

We're building a **Glitchware Library** — a catalog of known model glitches, their root causes, and production-ready patches. The `python3 -c` crash is Cline Glitch #1.

---

## 📄 License

- **Core library** (`state_engine.py`, hooks, rules): MIT License  
- **Patches and commercial extensions**: Proprietary, available via Patch Pack

---

## 🔗 Links

- **Repository:** [github.com/null-parse/NeuralCline](https://github.com/null-parse/NeuralCline)
- **Install:** `curl -fsSL https://raw.githubusercontent.com/null-parse/NeuralCline/main/install.sh | bash`
- **Recovery:** `source /root/rehydration.md`
- **Diagnostic:** `bash /root/NeuralCline/hooks/diagnose.sh`
- **Project roadmap:** [`docs/TIMELINE.md`](docs/TIMELINE.md)

---

*Built by EDGECASE — the boundary no system anticipates.*