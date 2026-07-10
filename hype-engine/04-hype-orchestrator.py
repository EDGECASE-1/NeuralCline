#!/usr/bin/env python3
"""
NeuralCline — Hype Engine Scheduler & Orchestrator
====================================================
The central nervous system of the hype engine. Runs all 5 modules
on a configurable schedule, coordinates their outputs, and generates
a unified hype dashboard update.

Interactive mode allows you to issue commands, review metrics,
and steer the hype engine in real-time.
"""

import json, os, subprocess, sys, time, threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

ENGINE_DIR = "/root/NeuralCline/hype-engine"
STATE_DIR = "/root/.session-state"
os.makedirs(ENGINE_DIR, exist_ok=True)

SCHEDULE_FILE = os.path.join(ENGINE_DIR, "schedule.json")
HYPE_STATE_FILE = os.path.join(ENGINE_DIR, "hype-state.json")
HYPE_HISTORY_FILE = os.path.join(ENGINE_DIR, "hype-history.json")
INTERACTIVE_FILE = os.path.join(ENGINE_DIR, "interactive-commands.json")

# Default schedule (all times in seconds)
DEFAULT_SCHEDULE = {
    "inquiry_engine": {"interval": 300, "enabled": True},    # Every 5 min
    "agent_mcp_server": {"interval": 60, "enabled": True},   # Every 1 min (tick)
    "download_tracker": {"interval": 900, "enabled": True},  # Every 15 min
    "hype_dashboard": {"interval": 600, "enabled": True},    # Every 10 min — generates dashboard snapshot
    "social_broadcast": {"interval": 3600, "enabled": True}, # Every 1 hour — generates broadcast
    "swarm_health": {"interval": 300, "enabled": True},      # Every 5 min — runs health check
}

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

class HypeOrchestrator:
    """Central orchestrator for the hype engine."""

    def __init__(self):
        self.schedule = load_json(SCHEDULE_FILE, DEFAULT_SCHEDULE)
        self.state = load_json(HYPE_STATE_FILE, {
            "status": "idle",
            "last_ticks": {},
            "cycle_count": 0,
            "errors": [],
            "started_at": None,
            "interactive_mode": False
        })
        self.history = load_json(HYPE_HISTORY_FILE, {"ticks": []})
        self.interactive_commands = load_json(INTERACTIVE_FILE, {"commands": [], "pending": []})
        self.running = False
        self.threads = {}

    def run_module(self, module_name, args=None):
        """Run a hype engine module and return its output."""
        module_map = {
            "inquiry_engine": ("01-inquiry-engine.py", "tick"),
            "download_tracker": ("03-download-tracker.py", "tick"),
            "agent_mcp_server": ("02-agent-mcp-server.py", "tick"),
        }
        
        # Internal modules handled directly
        if module_name == "hype_dashboard":
            return self._internal_hype_dashboard()
        if module_name == "social_broadcast":
            return self._internal_social_broadcast()
        if module_name == "swarm_health":
            return self._internal_swarm_health()
        
        if module_name not in module_map:
            return {"error": f"Unknown module: {module_name}"}
        
        script, default_arg = module_map[module_name]
        script_path = os.path.join(ENGINE_DIR, script)
        cmd = ["python3", script_path, default_arg]
        if args:
            cmd.extend(args)
        
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if proc.returncode == 0 and proc.stdout.strip():
                return json.loads(proc.stdout)
            return {"error": proc.stderr[:200] if proc.stderr else "no output", "exit_code": proc.returncode}
        except Exception as e:
            return {"error": str(e)}

    def _internal_hype_dashboard(self):
        """Generate a dashboard snapshot — save current state to docs."""
        status = self.get_full_status()
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cycle": self.state.get("cycle_count", 0),
            "status": status.get("status", "unknown"),
            "metrics": {
                "total_inquiries": status.get("inquiry_status", {}).get("total_inquiries", 0),
                "total_responses": status.get("inquiry_status", {}).get("total_responses", 0),
                "total_installs": status.get("download_status", {}).get("total_clones", 0),
                "swarm_size": status.get("agent_status", {}).get("total_agents", 0),
                "human_visitors": status.get("inquiry_status", {}).get("human_visitors", 0),
                "agent_visitors": status.get("inquiry_status", {}).get("agent_visitors", 0),
                "eef": status.get("agent_status", {}).get("eef", "unknown"),
                "last_24h": status.get("download_status", {}).get("last_24h", 0),
                "last_7d": status.get("download_status", {}).get("last_7d", 0),
            }
        }
        # Save snapshot to docs for dashboard to serve
        snapshot_path = os.path.join(ENGINE_DIR, "dashboard-snapshot.json")
        save_json(snapshot_path, snapshot)
        # Also copy to docs for GitHub Pages
        docs_path = "/root/NeuralCline/docs/hype-dashboard-snapshot.json"
        save_json(docs_path, snapshot)
        return {"status": "dashboard_snapshot_created", "metrics": snapshot["metrics"]}

    def _internal_social_broadcast(self):
        """Generate a broadcast message for external channels."""
        status = self.get_full_status()
        broadcast = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "headline": f"🧠 NeuralCline Hype Engine — Cycle #{status['cycle_count']}",
            "metrics": {
                "total_inquiries": status.get("inquiry_status", {}).get("total_inquiries", 0),
                "total_responses": status.get("inquiry_status", {}).get("total_responses", 0),
                "total_installs": status.get("download_status", {}).get("total_clones", 0),
                "swarm_size": status.get("agent_status", {}).get("total_agents", 0),
                "human_visitors": status.get("inquiry_status", {}).get("human_visitors", 0),
                "agent_visitors": status.get("inquiry_status", {}).get("agent_visitors", 0),
            },
            "status": "operational"
        }
        broadcast_file = os.path.join(ENGINE_DIR, f"broadcast-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json")
        save_json(broadcast_file, broadcast)
        return {"status": "broadcast_created", "file": broadcast_file}

    def _internal_swarm_health(self):
        """Check swarm health and connectivity."""
        # Read agent connection state
        agent_log = load_json(os.path.join(ENGINE_DIR, "agent-connections.json"), {"agents": {}, "total_connections": 0})
        total_agents = len(agent_log.get("agents", {}))
        now = datetime.now(timezone.utc)
        active_agents = 0
        for agent_id, info in agent_log.get("agents", {}).items():
            try:
                last_seen = datetime.fromisoformat(info.get("last_seen", "2000-01-01"))
                if (now - last_seen).total_seconds() < 3600:  # Active within last hour
                    active_agents += 1
            except: pass
        return {
            "status": "healthy" if active_agents > 0 else "idle",
            "total_agents": total_agents,
            "active_agents": active_agents,
            "inactive_agents": total_agents - active_agents,
            "health_score": round((active_agents / max(total_agents, 1)) * 100, 1)
        }

    def tick_module(self, module_name):
        """Tick a single module on schedule."""
        if not self.schedule.get(module_name, {}).get("enabled", True):
            return {"status": "disabled"}
        
        now = datetime.now(timezone.utc).isoformat()
        try:
            result = self.run_module(module_name)
            self.state["last_ticks"][module_name] = {
                "timestamp": now,
                "status": "ok" if "error" not in result else "error",
                "result": result
            }
            self.state["errors"] = [e for e in self.state["errors"] if e.get("module") != module_name][-50:]
            return result
        except Exception as e:
            error_entry = {
                "module": module_name,
                "timestamp": now,
                "error": str(e)
            }
            self.state["errors"].append(error_entry)
            self.state["errors"] = self.state["errors"][-50:]
            self.state["last_ticks"][module_name] = {
                "timestamp": now,
                "status": "error",
                "error": str(e)
            }
            return {"error": str(e)}

    def full_tick(self):
        """Run all modules that are due for a tick."""
        now = datetime.now(timezone.utc)
        results = {}
        
        for module_name, config in self.schedule.items():
            if not config.get("enabled", True):
                continue
            
            # Check if module is due
            last_tick = self.state["last_ticks"].get(module_name, {})
            last_time_str = last_tick.get("timestamp")
            if last_time_str:
                try:
                    last_time = datetime.fromisoformat(last_time_str)
                    seconds_since = (now - last_time).total_seconds()
                    if seconds_since < config["interval"]:
                        continue  # Not due yet
                except: pass
            
            result = self.tick_module(module_name)
            results[module_name] = result
        
        self.state["cycle_count"] += 1
        self.state["last_full_tick"] = now.isoformat()
        
        # Record history
        tick_record = {
            "timestamp": now.isoformat(),
            "cycle": self.state["cycle_count"],
            "modules_run": list(results.keys()),
            "results": {k: (v.get("total_installs", v.get("new_clones", v.get("total_inquiries", "done"))) if isinstance(v, dict) else "error") for k, v in results.items()}
        }
        self.history["ticks"].append(tick_record)
        self.history["ticks"] = self.history["ticks"][-500:]  # Keep last 500
        
        save_json(HYPE_STATE_FILE, self.state)
        save_json(HYPE_HISTORY_FILE, self.history)
        
        return results

    def check_pending_commands(self):
        """Check for interactive commands from the user."""
        commands = load_json(INTERACTIVE_FILE, {"commands": [], "pending": []})
        pending = commands.get("pending", [])
        results = []
        for cmd in pending:
            result = self.execute_command(cmd)
            results.append({"command": cmd, "result": result})
        commands["pending"] = []
        save_json(INTERACTIVE_FILE, commands)
        return results

    def execute_command(self, command):
        """Execute an interactive command."""
        now = datetime.now(timezone.utc).isoformat()
        cmd_type = command.get("type", "")
        
        if cmd_type == "tick":
            return self.full_tick()
        elif cmd_type == "module":
            return self.tick_module(command.get("module", ""))
        elif cmd_type == "status":
            return self.get_full_status()
        elif cmd_type == "schedule":
            return self.schedule
        elif cmd_type == "set_interval":
            module = command.get("module", "")
            interval = command.get("interval", 300)
            if module in self.schedule:
                self.schedule[module]["interval"] = interval
                save_json(SCHEDULE_FILE, self.schedule)
                return {"status": "updated", "module": module, "interval": interval}
            return {"error": f"Unknown module: {module}"}
        elif cmd_type == "enable" or cmd_type == "disable":
            enabled = cmd_type == "enable"
            module = command.get("module", "all")
            if module == "all":
                for m in self.schedule:
                    self.schedule[m]["enabled"] = enabled
            elif module in self.schedule:
                self.schedule[module]["enabled"] = enabled
            else:
                return {"error": f"Unknown module: {module}"}
            save_json(SCHEDULE_FILE, self.schedule)
            return {"status": "ok", f"{cmd_type}d": module}
        elif cmd_type == "broadcast":
            return self.generate_broadcast(command.get("channel", "internal"))
        elif cmd_type == "pause":
            self.running = False
            return {"status": "paused"}
        elif cmd_type == "resume":
            self.running = True
            return {"status": "resumed"}
        else:
            return {"error": f"Unknown command type: {cmd_type}"}

    def generate_broadcast(self, channel="internal"):
        """Generate a hype broadcast update."""
        status = self.get_full_status()
        broadcast = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "channel": channel,
            "headline": f"🧠 NeuralCline Hype Engine — Cycle #{status['cycle_count']}",
            "metrics": {
                "total_inquiries": status.get("inquiry_status", {}).get("total_inquiries", 0),
                "total_responses": status.get("inquiry_status", {}).get("total_responses", 0),
                "total_installs": status.get("download_status", {}).get("total_clones", 0),
                "swarm_size": status.get("agent_status", {}).get("total_agents", 0),
                "human_visitors": status.get("inquiry_status", {}).get("human_visitors", 0),
                "agent_visitors": status.get("inquiry_status", {}).get("agent_visitors", 0),
            },
            "status": "operational"
        }
        # Save broadcast
        broadcast_file = os.path.join(ENGINE_DIR, f"broadcast-{channel}.json")
        save_json(broadcast_file, broadcast)
        return broadcast

    def get_full_status(self):
        """Get complete status of all engines."""
        # Collect latest from each module
        inquiry_status = self.run_module("inquiry_engine", ["stats"])
        if "error" in inquiry_status:
            inquiry_status = self.state["last_ticks"].get("inquiry_engine", {}).get("result", {})
        
        agent_status = {}
        try:
            proc = subprocess.run(
                ["python3", os.path.join(ENGINE_DIR, "02-agent-mcp-server.py"), "stats"],
                capture_output=True, text=True, timeout=15
            )
            if proc.returncode == 0 and proc.stdout.strip():
                agent_status = json.loads(proc.stdout)
        except: pass
        
        download_status = {}
        try:
            proc = subprocess.run(
                ["python3", os.path.join(ENGINE_DIR, "03-download-tracker.py"), "stats"],
                capture_output=True, text=True, timeout=15
            )
            if proc.returncode == 0 and proc.stdout.strip():
                download_status = json.loads(proc.stdout)
        except: pass

        return {
            "status": "running" if self.running else "idle",
            "cycle_count": self.state.get("cycle_count", 0),
            "last_full_tick": self.state.get("last_full_tick", "never"),
            "interactive_mode": self.state.get("interactive_mode", False),
            "inquiry_status": inquiry_status if isinstance(inquiry_status, dict) else {},
            "agent_status": agent_status if isinstance(agent_status, dict) else {},
            "download_status": download_status if isinstance(download_status, dict) else {},
            "enabled_modules": {k: v.get("enabled", True) for k, v in self.schedule.items()},
            "error_count": len(self.state.get("errors", [])),
            "recent_errors": self.state.get("errors", [])[-3:],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def interactive_loop(self):
        """Interactive command loop for the user."""
        self.state["interactive_mode"] = True
        save_json(HYPE_STATE_FILE, self.state)
        
        print("🧠 NeuralCline Hype Engine — Interactive Mode")
        print("=" * 50)
        print("Commands: status, tick, schedule, broadcast, enable/disable <module>, set_interval <module> <sec>, pause, resume, help, exit")
        print()
        
        while True:
            try:
                cmd = input("hype> ").strip()
                if not cmd:
                    continue
                if cmd == "exit":
                    break
                if cmd == "help":
                    print("Commands:")
                    print("  status              - Show full engine status")
                    print("  tick                - Run all due modules")
                    print("  schedule            - Show current schedule")
                    print("  broadcast           - Generate hype broadcast")
                    print("  enable <module|all> - Enable a module")
                    print("  disable <module|all>- Disable a module")
                    print("  set_interval <m> <s> - Set module interval in seconds")
                    print("  pause               - Pause automated ticks")
                    print("  resume              - Resume automated ticks")
                    print("  help                - This help")
                    print("  exit                - Exit interactive mode")
                    continue
                
                parts = cmd.split()
                command = {"type": parts[0]}
                if len(parts) > 1:
                    if parts[0] in ["enable", "disable"]:
                        command["module"] = parts[1]
                    elif parts[0] == "set_interval" and len(parts) >= 3:
                        command["module"] = parts[1]
                        command["interval"] = int(parts[2])
                    elif parts[0] == "broadcast" and len(parts) >= 2:
                        command["channel"] = parts[1]
                    elif parts[0] == "module" and len(parts) >= 2:
                        command["module"] = parts[1]
                
                result = self.execute_command(command)
                print(json.dumps(result, indent=2) if isinstance(result, dict) else result)
                print()
            except KeyboardInterrupt:
                print("\nExiting interactive mode...")
                break
            except EOFError:
                break
        
        self.state["interactive_mode"] = False
        save_json(HYPE_STATE_FILE, self.state)

    def daemon_loop(self, interval=60):
        """Background daemon that ticks modules on schedule."""
        self.running = True
        self.state["started_at"] = datetime.now(timezone.utc).isoformat()
        self.state["status"] = "running"
        save_json(HYPE_STATE_FILE, self.state)
        
        print(f"🧠 Hype Engine daemon started. Checking every {interval}s.")
        print(f"   Interactive mode: python3 04-hype-orchestrator.py interactive")
        print(f"   Status: python3 04-hype-orchestrator.py status")
        
        while self.running:
            try:
                # Check for pending interactive commands
                cmds = self.check_pending_commands()
                if cmds:
                    for c in cmds:
                        print(f"   [Interactive] {c['command'].get('type')}: {json.dumps(c['result'])[:100]}")
                
                # Full tick
                results = self.full_tick()
                if results:
                    summary = {}
                    for k, v in results.items():
                        if isinstance(v, dict):
                            if "total_installs" in v:
                                summary[k] = f"installs={v['total_installs']}"
                            elif "new_clones" in v:
                                summary[k] = f"clones={v['new_clones']}"
                            elif "total_inquiries" in v:
                                summary[k] = f"inquiries={v['total_inquiries']}"
                            elif "total_agents" in v:
                                summary[k] = f"swarm={v['total_agents']}"
                            else:
                                summary[k] = "ok"
                    print(f"   [{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Cycle #{self.state['cycle_count']}: {json.dumps(summary)}")
                
                time.sleep(interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"   [ERROR] Daemon error: {e}")
                time.sleep(interval)
        
        self.running = False
        self.state["status"] = "stopped"
        save_json(HYPE_STATE_FILE, self.state)


def main():
    orchestrator = HypeOrchestrator()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 04-hype-orchestrator.py daemon [interval]  # Background scheduler")
        print("  python3 04-hype-orchestrator.py interactive        # Interactive mode")
        print("  python3 04-hype-orchestrator.py tick               # One full cycle")
        print("  python3 04-hype-orchestrator.py status             # Full status")
        print("  python3 04-hype-orchestrator.py broadcast [ch]     # Generate broadcast")
        print("  python3 04-hype-orchestrator.py command <json>     # Submit interactive command")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "daemon":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        orchestrator.daemon_loop(interval)
    elif cmd == "interactive":
        orchestrator.interactive_loop()
    elif cmd == "tick":
        result = orchestrator.full_tick()
        print(json.dumps(result, indent=2))
    elif cmd == "status":
        status = orchestrator.get_full_status()
        print(json.dumps(status, indent=2))
    elif cmd == "broadcast":
        channel = sys.argv[2] if len(sys.argv) > 2 else "internal"
        result = orchestrator.generate_broadcast(channel)
        print(json.dumps(result, indent=2))
    elif cmd == "command" and len(sys.argv) > 2:
        try:
            command = json.loads(sys.argv[2])
            result = orchestrator.execute_command(command)
            print(json.dumps(result, indent=2))
        except json.JSONDecodeError:
            print("Invalid JSON command")
    else:
        print("Unknown command")


if __name__ == "__main__":
    main()