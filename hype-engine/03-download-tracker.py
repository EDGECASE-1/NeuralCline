#!/usr/bin/env python3
"""
NeuralCline — Download & Install Tracker
=========================================
Tracks every clone, install, and download attempt.
Detects who is downloading (human vs agent) and sends
engagement follow-ups to downloaders.
"""

import json, os, subprocess, sys, time, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

STATE_DIR = "/root/.session-state"
ENGINE_DIR = "/root/NeuralCline/hype-engine"
os.makedirs(ENGINE_DIR, exist_ok=True)

DOWNLOADS_FILE = os.path.join(ENGINE_DIR, "download-log.json")
INSTALL_EVENTS_FILE = os.path.join(ENGINE_DIR, "install-events.json")
DOWNLOADER_PROFILES = os.path.join(ENGINE_DIR, "downloader-profiles.json")

def load_json(path, default=None):
    try:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path) as f:
                return json.load(f)
    except: pass
    return default if default else {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def gh_api(endpoint, method="GET", data=None):
    """Safe GitHub API call."""
    cmd = ["gh", "api", endpoint]
    if data:
        cmd += ["--method", method, "--input", "-"]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20,
            input=json.dumps(data) if data else None
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
        return {"error": proc.stderr[:200] if proc.stderr else "no output"}
    except Exception as e:
        return {"error": str(e)}


class DownloadTracker:
    """Tracks cloning, downloading, and installation events."""

    def __init__(self):
        self.downloads = load_json(DOWNLOADS_FILE, {
            "total_clones": 0,
            "total_installs": 0,
            "daily": {},
            "hourly": {},
            "last_24h": 0,
            "last_7d": 0,
            "source_breakdown": {},
            "peaks": {"max_daily": 0, "date": None},
            "events": []
        })
        self.install_events = load_json(INSTALL_EVENTS_FILE, {"events": [], "total": 0})
        self.profiles = load_json(DOWNLOADER_PROFILES, {"profiles": {}, "total": 0})

    def check_github_traffic(self):
        """Pull clone/view traffic data from GitHub API."""
        new_clones = 0
        now = datetime.now(timezone.utc).isoformat()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Clone traffic
        clones = gh_api("repos/EDGECASE-1/NeuralCline/traffic/clones")
        if isinstance(clones, dict) and "count" in clones:
            count = clones.get("count", 0)
            uniques = clones.get("uniques", 0)
            self.downloads["total_clones"] = max(self.downloads["total_clones"], count)
            self.downloads["unique_clones"] = uniques
            # Track daily
            if today not in self.downloads["daily"]:
                self.downloads["daily"][today] = {"clones": 0, "installs": 0}
            old_count = self.downloads["daily"][today].get("clones", 0)
            if count > old_count:
                new_clones = count - old_count
            self.downloads["daily"][today]["clones"] = count

        # View traffic
        views = gh_api("repos/EDGECASE-1/NeuralCline/traffic/views")
        if isinstance(views, dict) and "count" in views:
            self.downloads["total_views"] = views.get("count", 0)
            self.downloads["unique_visitors"] = views.get("uniques", 0)

        # Referrer sources
        refs = gh_api("repos/EDGECASE-1/NeuralCline/traffic/popular/referrers")
        if isinstance(refs, list):
            for ref in refs:
                name = ref.get("referrer", "direct")
                count = ref.get("count", 0)
                uniques = ref.get("uniques", 0)
                if name not in self.downloads["source_breakdown"]:
                    self.downloads["source_breakdown"][name] = {"count": 0, "uniques": 0}
                self.downloads["source_breakdown"][name]["count"] = max(
                    self.downloads["source_breakdown"][name]["count"], count
                )
                self.downloads["source_breakdown"][name]["uniques"] = max(
                    self.downloads["source_breakdown"][name]["uniques"], uniques
                )

        # Update rolling windows
        self._update_rolling_windows()

        # Track peaks
        daily_count = self.downloads["daily"].get(today, {}).get("clones", 0)
        if daily_count > self.downloads["peaks"]["max_daily"]:
            self.downloads["peaks"]["max_daily"] = daily_count
            self.downloads["peaks"]["date"] = today

        self.downloads["last_checked"] = now
        save_json(DOWNLOADS_FILE, self.downloads)
        return new_clones

    def _update_rolling_windows(self):
        """Update 24h and 7d rolling counts."""
        now = datetime.now(timezone.utc)
        last_24h = 0
        last_7d = 0
        for date_str, data in self.downloads["daily"].items():
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                hours_ago = (now - date).total_seconds() / 3600
                if hours_ago <= 24:
                    last_24h += data.get("clones", 0)
                if hours_ago <= 168:
                    last_7d += data.get("clones", 0)
            except: pass
        self.downloads["last_24h"] = last_24h
        self.downloads["last_7d"] = last_7d

    def check_stargazers(self):
        """Track who is starring the repo — potential power users."""
        stargazers = gh_api("repos/EDGECASE-1/NeuralCline/stargazers?per_page=100")
        if isinstance(stargazers, list):
            for sg in stargazers:
                username = sg.get("login", "unknown")
                if username not in self.profiles["profiles"]:
                    self.profiles["profiles"][username] = {
                        "username": username,
                        "type": "stargazer",
                        "first_seen": datetime.now(timezone.utc).isoformat(),
                        "avatar": sg.get("avatar_url", ""),
                        "profile_url": sg.get("html_url", ""),
                        "is_agent": self._detect_agent(username)
                    }
            self.profiles["total"] = len(self.profiles["profiles"])
            save_json(DOWNLOADER_PROFILES, self.profiles)
        return len(stargazers) if isinstance(stargazers, list) else 0

    def check_forks(self):
        """Track forks — high-intent downloads (someone wants to modify/build on this)."""
        forks = gh_api("repos/EDGECASE-1/NeuralCline/forks?per_page=100")
        if isinstance(forks, list):
            for fork in forks:
                owner = fork.get("owner", {})
                username = owner.get("login", "unknown")
                if username not in self.profiles["profiles"]:
                    self.profiles["profiles"][username] = {
                        "username": username,
                        "type": "forker",
                        "first_seen": datetime.now(timezone.utc).isoformat(),
                        "fork_url": fork.get("html_url", ""),
                        "is_agent": self._detect_agent(username)
                    }
                else:
                    self.profiles["profiles"][username]["type"] = "forker"
                    self.profiles["profiles"][username]["fork_url"] = fork.get("html_url", "")
            self.profiles["total"] = len(self.profiles["profiles"])
            save_json(DOWNLOADER_PROFILES, self.profiles)
        return len(forks) if isinstance(forks, list) else 0

    def log_install_event(self, source="direct", agent_id=None):
        """Log a manual install event (called from webhook or install.sh)."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "agent_id": agent_id or "unknown",
            "is_agent": agent_id is not None
        }
        self.install_events["events"].append(event)
        self.install_events["total"] += 1
        self.install_events["last_event"] = event
        # Keep last 1000 events
        self.install_events["events"] = self.install_events["events"][-1000:]
        save_json(INSTALL_EVENTS_FILE, self.install_events)
        return event

    def _detect_agent(self, username):
        """Detect if a profile is likely an AI agent."""
        agent_indicators = [
            "bot", "agent", "gpt", "claude", "llama", "deepseek", 
            "mistral", "copilot", "runner", "ci", "machine"
        ]
        return any(ind in username.lower() for ind in agent_indicators)

    def get_install_velocity(self, hours=24):
        """Calculate install velocity (installs per hour)."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        count = 0
        for event in self.install_events["events"]:
            try:
                ts = datetime.fromisoformat(event["timestamp"])
                if ts >= cutoff:
                    count += 1
            except: pass
        # Also count from session state
        try:
            state = load_json(os.path.join(STATE_DIR, "current-state.json"), {})
            session_installs = state.get("total_installs", 0)
        except:
            session_installs = 0
        return {
            f"last_{hours}h": count,
            "velocity_per_hour": round(count / max(hours, 1), 2),
            "session_installs": session_installs,
            "total_tracked": self.install_events["total"]
        }

    def get_source_breakdown(self):
        """Get breakdown of where traffic is coming from."""
        return {
            "sources": self.downloads.get("source_breakdown", {}),
            "total_traffic": sum(
                s.get("count", 0) for s in self.downloads.get("source_breakdown", {}).values()
            )
        }

    def get_downloader_insights(self):
        """Generate insights about who is downloading."""
        agents = sum(1 for p in self.profiles["profiles"].values() if p.get("is_agent"))
        humans = self.profiles["total"] - agents
        stargazers = sum(1 for p in self.profiles["profiles"].values() if p.get("type") == "stargazer")
        forkers = sum(1 for p in self.profiles["profiles"].values() if p.get("type") == "forker")
        return {
            "total_downloaders": self.profiles["total"],
            "human_downloaders": humans,
            "agent_downloaders": agents,
            "stargazers": stargazers,
            "forkers": forkers,
            "agent_ratio": round(agents / max(self.profiles["total"], 1) * 100, 1),
            "top_sources": dict(sorted(
                self.downloads.get("source_breakdown", {}).items(),
                key=lambda x: x[1].get("count", 0),
                reverse=True
            )[:5])
        }

    def tick(self):
        """Run one full monitoring cycle."""
        new_clones = self.check_github_traffic()
        stars = self.check_stargazers()
        forks = self.check_forks()
        velocity = self.get_install_velocity()
        insights = self.get_downloader_insights()
        save_json(DOWNLOADS_FILE, self.downloads)
        return {
            "new_clones": new_clones,
            "total_clones": self.downloads["total_clones"],
            "stargazers_found": stars,
            "forks_found": forks,
            "install_velocity": velocity,
            "downloader_insights": insights,
            "last_24h": self.downloads["last_24h"],
            "last_7d": self.downloads["last_7d"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


if __name__ == "__main__":
    tracker = DownloadTracker()
    if len(sys.argv) > 1:
        if sys.argv[1] == "tick":
            print(json.dumps(tracker.tick(), indent=2))
        elif sys.argv[1] == "stats":
            print(json.dumps(tracker.get_downloader_insights(), indent=2))
        elif sys.argv[1] == "velocity":
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            print(json.dumps(tracker.get_install_velocity(hours), indent=2))
        elif sys.argv[1] == "install":
            source = sys.argv[2] if len(sys.argv) > 2 else "direct"
            agent_id = sys.argv[3] if len(sys.argv) > 3 else None
            print(json.dumps(tracker.log_install_event(source, agent_id), indent=2))
        else:
            print("Usage: python3 03-download-tracker.py [tick|stats|velocity|install]")
    else:
        print(json.dumps(tracker.tick(), indent=2))