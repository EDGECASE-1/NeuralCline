# NeuralCline — Infinite Persistence Strategy

## How to Make This Workspace Live Forever

This code-server workspace (Axon-1) is temporary. Every file in `/root/` will be lost when the container recycles. But NeuralCline is designed to never die. Here's the strategy:

---

## Strategy 1: DevContainer (Easiest — Auto-Rebuilds)

The `.devcontainer/devcontainer.json` I just created tells code-server to:
1. Clone the repo fresh on every new workspace
2. Run `install.sh` automatically
3. Run `source /root/rehydration.md` on every start
4. Preserve `.session-state/` via GitHub-backed storage

**How to use it:**
1. Push this file: `git push` (already done)
2. When you open a new workspace, code-server detects `.devcontainer/` and auto-rebuilds
3. NeuralCline installs itself fresh every time
4. The session state is restored from the checkpoint

**But wait — the session state files are LOCAL.** They won't persist across rebuilds unless we back them up to GitHub.

---

## Strategy 2: GitHub-Backed Session State (Fully Persistent)

The REAL trick: store session state **in a GitHub Gist** so it survives any workspace rebuild.

I already built the infrastructure for this. The attention monitor and real-time dashboard both save to Gists. But we need to extend it to ALL session state files.

### The Solution: Session State Sync

Every time the real-time dashboard ticks, it ALSO backs up the entire session state to a Gist:

```bash
# This is already partially implemented:
# - attention_monitor.py saves to gist
# - realtime_dashboard.py saves to gist
# - syndication.yml saves to gist every 6h
```

To make it **fully persistent**, on every new session, run:

```bash
python3 /root/NeuralCline/lib/realtime_dashboard.py init
```

This will detect the baseline from the previous session and continue tracking.

---

## Strategy 3: GitHub Pages + GitHub Actions (Already Fully Persistent)

Everything that matters is already on GitHub:

| Asset | Where | Survives Rebuild? |
|-------|-------|-------------------|
| **All 223 source files** | `github.com/EDGECASE-1/NeuralCline` | ✅ YES |
| **Landing page** | `edgecase-1.github.io/NeuralCline/` | ✅ YES |
| **Pricing page** | `edgecase-1.github.io/NeuralCline/pricing.html` | ✅ YES |
| **Dashboard** | `edgecase-1.github.io/NeuralCline/dashboard.html` | ✅ YES (but needs tick updates) |
| **Attention metrics Gist** | Public Gist | ✅ YES |
| **Changelog Gist** | Public Gist | ✅ YES |
| **GitHub Actions** | Runs every 6h on GitHub's servers | ✅ YES |
| **GitHub Issues** | All 10 issues | ✅ YES |
| **GitHub Discussion** | Launch announcement | ✅ YES |
| **GitHub Release** | v1.0.1 | ✅ YES |

---

## Strategy 4: Self-Hosted Runner (For Enterprise)

If you want the daemon to run **24/7/365** (not just when code-server is open):

### Option A: GitHub Actions Runner on Your Own Machine

```bash
# On your own server/desktop:
gh auth login
gh extension install actions/gh-actions
gh actions-runner register --repo EDGECASE-1/NeuralCline --name neuralcline-daemon
```

Then the GitHub Actions workflow runs on YOUR machine, 24/7.

### Option B: Raspberry Pi / VPS Daemon

```bash
# On any always-on Linux machine:
git clone https://github.com/EDGECASE-1/NeuralCline.git /opt/NeuralCline
bash /opt/NeuralCline/install.sh

# Run the daemon in a screen/tmux session:
screen -S neuralcline-daemon
python3 /opt/NeuralCline/lib/realtime_dashboard.py daemon
# Detach: Ctrl+A, D
# Reattach: screen -r neuralcline-daemon
```

### Option C: GitHub Codespaces (Free 60h/month)

GitHub Codespaces is the same as code-server but backed by GitHub:
1. Go to https://github.com/EDGECASE-1/NeuralCline
2. Click **Code** → **Create codespace on master**
3. The `.devcontainer/devcontainer.json` auto-configures everything
4. Run `python3 /root/NeuralCline/lib/realtime_dashboard.py daemon` in the background

---

## Strategy 5: GitHub Pages Dashboard (Push-Based)

The dashboard at `https://edgecase-1.github.io/NeuralCline/dashboard.html` auto-refreshes every 60 seconds. But it only updates when the `tick` command runs.

**For the dashboard to stay live forever without a daemon:**

The GitHub Actions workflow (`.github/workflows/syndication.yml`) runs every 6 hours and:
1. Checks GitHub stars
2. Checks fork count
3. Updates the metrics Gist

To extend it to also update the dashboard, add this to the workflow:

```yaml
- name: Update Dashboard
  run: |
    git checkout master
    python3 /root/NeuralCline/lib/realtime_dashboard.py tick
    git add docs/dashboard.html
    git commit -m "Auto-update dashboard [skip ci]"
    git push
```

This way, the dashboard updates every 6 hours **without any running daemon**.

---

## The Bottom Line

| Method | Persistence | Requires Always-On Machine? |
|--------|-------------|----------------------------|
| **GitHub Repo** | ✅ Forever | No |
| **GitHub Pages** | ✅ Forever | No |
| **GitHub Actions** | ✅ Forever | No (GitHub servers) |
| **GitHub Gists** | ✅ Forever | No |
| **DevContainer** | ✅ Every rebuild | No (auto-rebuilds) |
| **Daemon** | ⏳ While running | Yes |
| **Self-Hosted Runner** | ✅ 24/7 | Yes (your machine) |
| **Codespaces** | ⏳ 60h/month | Partial |

### What I Recommend

**For the repo and all web assets:** Already done. Nothing more needed.

**For the daemon to run forever:** Use a $5/month VPS (DigitalOcean, Linode, Hetzner) and run:
```bash
screen -S neuralcline
git clone https://github.com/EDGECASE-1/NeuralCline.git /opt/NeuralCline
bash /opt/NeuralCline/install.sh
python3 /opt/NeuralCline/lib/realtime_dashboard.py daemon
# Ctrl+A, D to detach
```

**To get paid:** Complete Stripe onboarding at https://github.com/sponsors/EDGECASE-1/dashboard

**To go viral:** Submit to Hacker News at https://news.ycombinator.com/submit

That's it. The repo is immortal. The code is in GitHub. The world can find it.