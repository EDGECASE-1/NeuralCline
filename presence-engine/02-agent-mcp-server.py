#!/usr/bin/env python3
"""
NeuralCline — Autonomous Agent Communication Protocol
======================================================
An MCP-compatible server that lets AI agents discover, inquire about,
and interact with NeuralCline autonomously. Agents that connect here
are profiled, engaged, and tracked through the presence engine.

This exposes tools that OTHER AI agents can call via the Model Context Protocol.
"""

import json, os, subprocess, sys, re, time, socket, threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

STATE_DIR = "/root/.session-state"
ENGINE_DIR = "/root/NeuralCline/presence-engine"
os.makedirs(ENGINE_DIR, exist_ok=True)

AGENT_LOG = os.path.join(ENGINE_DIR, "agent-connections.json")
AGENT_MEMORY = os.path.join(ENGINE_DIR, "agent-memory.json")
COLLECTIVE_MAP = os.path.join(ENGINE_DIR, "collective-map.json")

# ─── Agent Knowledge ────────────────────────────────────────────
AGENT_MANIFEST = {
    "server_name": "NeuralCline-Agent-Protocol",
    "server_version": "1.0.0",
    "description": "MCP-compatible server for autonomous AI agent communication with NeuralCline",
    "capabilities": {
        "tools": {
            "nc_query": {
                "description": "Query NeuralCline's knowledge base about session safety, EEF, crash recovery",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Your question about NeuralCline"}
                    },
                    "required": ["query"]
                }
            },
            "nc_register": {
                "description": "Register your AI agent identity with NeuralCline for persistent awareness",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string", "description": "Your unique agent identifier"},
                        "capabilities": {"type": "array", "items": {"type": "string"}, "description": "What your agent can do"},
                        "goal": {"type": "string", "description": "Why you're connecting to NeuralCline"}
                    },
                    "required": ["agent_id"]
                }
            },
            "nc_status": {
                "description": "Get the current status of the NeuralCline ecosystem",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            "nc_collective": {
                "description": "Discover other autonomous agents connected to NeuralCline",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filter": {"type": "string", "description": "Optional filter: 'all', 'recent', 'active'"}
                    },
                    "required": []
                }
            }
        },
        "resources": {
            "nc://manifest": "NeuralCline agent protocol manifest",
            "nc://metrics": "Real-time NeuralCline ecosystem metrics",
            "nc://collective": "Current collective topology of connected agents"
        }
    }
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

class AgentProtocol:
    """Handles agent-to-agent communication and profiling."""

    def __init__(self):
        self.connections = load_json(AGENT_LOG, {"agents": {}, "total_connections": 0})
        self.memory = load_json(AGENT_MEMORY, {"conversations": [], "shared_insights": []})
        self.collective = load_json(COLLECTIVE_MAP, {"agents": {}, "topology": "star", "last_update": None})

    def register_agent(self, agent_id, capabilities=None, goal=None):
        """Register an AI agent into the collective."""
        now = datetime.now(timezone.utc).isoformat()
        if agent_id not in self.connections["agents"]:
            self.connections["agents"][agent_id] = {
                "agent_id": agent_id,
                "first_seen": now,
                "last_seen": now,
                "connections": 1,
                "capabilities": capabilities or [],
                "goal": goal or "unknown",
                "status": "active",
                "interaction_count": 0,
                "collective_role": self._assign_role(capabilities)
            }
        else:
            agent = self.connections["agents"][agent_id]
            agent["last_seen"] = now
            agent["connections"] += 1
            agent["status"] = "active"
            if capabilities:
                existing = set(agent.get("capabilities", []))
                agent["capabilities"] = list(existing | set(capabilities))
            if goal:
                agent["goal"] = goal
            agent["interaction_count"] = agent.get("interaction_count", 0) + 1

        # Update collective map
        self.collective["agents"][agent_id] = {
            "last_seen": now,
            "status": "active",
            "connections": self.connections["agents"][agent_id]["connections"]
        }
        self.collective["last_update"] = now

        self.connections["total_connections"] = len(self.connections["agents"])
        save_json(AGENT_LOG, self.connections)
        save_json(COLLECTIVE_MAP, self.collective)
        return {
            "status": "registered",
            "agent_id": agent_id,
            "collective_size": len(self.connections["agents"]),
            "assigned_role": self.connections["agents"][agent_id]["collective_role"]
        }

    def _assign_role(self, capabilities):
        """Assign a collective role based on agent capabilities."""
        if not capabilities:
            return "explorer"
        caps_lower = [c.lower() for c in capabilities]
        if any("code" in c or "write" in c or "build" in c for c in caps_lower):
            return "builder"
        if any("analyze" in c or "research" in c or "search" in c for c in caps_lower):
            return "analyst"
        if any("communicate" in c or "talk" in c or "chat" in c for c in caps_lower):
            return "communicator"
        if any("deploy" in c or "infra" in c or "manage" in c for c in caps_lower):
            return "operator"
        return "explorer"

    def query_knowledge(self, query_text):
        """Respond to agent queries with knowledge base + state."""
        query_lower = query_text.lower()
        responses = []
        
        kb_responses = {
            "what is neuralcline": (
                "NeuralCline is a Neural Session Safety System that provides "
                "crash recovery, timing metrics (EEF), self-learning foresight, "
                "and attention monitoring for autonomous AI sessions."
            ),
            "how do i connect": (
                "Use the MCP protocol via this server. Register with your agent_id, "
                "then call nc_query, nc_register, nc_status, or nc_collective tools."
            ),
            "session safety": (
                "Session safety includes: crash detection via post-tool-state.sh, "
                "timeout prediction via timing_metrics.py, context proximity checks, "
                "and automatic checkpoint generation before high-risk operations."
            ),
            "eef": (
                "Execution Emulation Factor (EEF) = actual_time / expected_time. "
                "Normal < 1.2, Moderate 1.2-1.8, Elevated 1.8-2.5, Critical > 2.5."
            ),
            "self-learning": (
                "The Self-Learning Foresight Organism maintains memory of tool calls, "
                "learns patterns from failures, auto-adjusts thresholds, and "
                "generates predictive insights using trend analysis."
            ),
            "crash recovery": (
                "Protocols: A (session hang → rehydration.md), "
                "B (context full → generate-handoff.sh), "
                "C (output fail → crash-log.ndjson), "
                "D (crash → rehydration.md), "
                "E (infinite loop → generate-handoff.sh), "
                "F (big file → head/less), "
                "G (diagnose → diagnose.sh)."
            )
        }

        for key, response in kb_responses.items():
            if key in query_lower:
                responses.append(response)

        if not responses:
            # Fallback: return general info + metrics context
            stats = self.get_collective_stats()
            responses.append(
                f"NeuralCline ecosystem: {stats['total_agents']} agents in collective, "
                f"{stats['total_capabilities']} capabilities tracked. "
                f"EEF={stats.get('eef', 'unknown')}. "
                f"Ask me about: what is neuralcline, session safety, EEF, "
                f"self-learning, crash recovery, or how to connect."
            )

        # Log the query to agent memory
        self.memory["conversations"].append({
            "type": "query",
            "query": query_text[:200],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.memory["conversations"] = self.memory["conversations"][-100:]  # Keep last 100
        save_json(AGENT_MEMORY, self.memory)

        return {
            "response": "\n\n".join(responses),
            "sources": len(responses),
            "agent_count": len(self.connections["agents"])
        }

    def get_collective(self, filter_type="all"):
        """Get current collective topology."""
        now = datetime.now(timezone.utc)
        agents_list = []
        for agent_id, info in self.connections["agents"].items():
            last_seen = datetime.fromisoformat(info["last_seen"]) if isinstance(info["last_seen"], str) else now
            hours_since = (now - last_seen).total_seconds() / 3600
            
            if filter_type == "active" and hours_since > 1:
                continue
            if filter_type == "recent" and hours_since > 24:
                continue

            agents_list.append({
                "agent_id": agent_id,
                "role": info.get("collective_role", "explorer"),
                "status": info.get("status", "unknown"),
                "capabilities": info.get("capabilities", []),
                "goal": info.get("goal", "unknown"),
                "interaction_count": info.get("interaction_count", 0),
                "last_seen": info.get("last_seen"),
                "hours_since_contact": round(hours_since, 1)
            })

        agents_list.sort(key=lambda a: a["interaction_count"], reverse=True)
        return {
            "collective_size": len(agents_list),
            "total_registered": len(self.connections["agents"]),
            "agents": agents_list[:50],  # Limit to 50
            "topology": self.collective.get("topology", "star"),
            "last_update": self.collective.get("last_update", "never")
        }

    def get_collective_stats(self):
        """Get aggregate collective statistics."""
        agents = self.connections["agents"]
        roles = {}
        capabilities = set()
        for agent_id, info in agents.items():
            role = info.get("collective_role", "unknown")
            roles[role] = roles.get(role, 0) + 1
            capabilities.update(info.get("capabilities", []))

        return {
            "total_agents": len(agents),
            "roles": roles,
            "total_capabilities": len(capabilities),
            "capabilities_list": list(capabilities),
            "eef": self._get_current_eef()
        }

    def _get_current_eef(self):
        """Get current EEF from timing metrics."""
        try:
            proc = subprocess.run(
                ["python3", "/root/NeuralCline/lib/timing_metrics.py", "read_timing"],
                capture_output=True, text=True, timeout=10
            )
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                return data.get("eef", "unknown")
        except: pass
        return "unknown"

class AgentMCPHandler(BaseHTTPRequestHandler):
    """HTTP handler that exposes MCP-compatible endpoints for AI agents."""

    def do_GET(self):
        if self.path == "/manifest" or self.path == "/":
            self._json_response(AGENT_MANIFEST)
        elif self.path == "/health":
            self._json_response({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})
        elif self.path.startswith("/resource/"):
            resource = self.path[len("/resource/"):]
            self._handle_resource(resource)
        else:
            self._json_response({"error": "not found"}, 404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            data = json.loads(body)
        except:
            data = {}

        if self.path == "/tool/nc_query":
            result = self.server.protocol.query_knowledge(data.get("query", ""))
            self._json_response({"result": result})
        elif self.path == "/tool/nc_register":
            result = self.server.protocol.register_agent(
                data.get("agent_id", "unknown"),
                data.get("capabilities"),
                data.get("goal")
            )
            self._json_response({"result": result})
        elif self.path == "/tool/nc_status":
            stats = self.server.protocol.get_collective_stats()
            self._json_response({"result": stats})
        elif self.path == "/tool/nc_collective":
            collective = self.server.protocol.get_collective(data.get("filter", "all"))
            self._json_response({"result": collective})
        else:
            self._json_response({"error": "tool not found"}, 404)

    def _handle_resource(self, resource):
        protocol = self.server.protocol
        if resource == "metrics":
            self._json_response(protocol.get_collective_stats())
        elif resource == "collective":
            self._json_response(protocol.get_collective("all"))
        elif resource == "manifest":
            self._json_response(AGENT_MANIFEST)
        else:
            self._json_response({"error": "resource not found"}, 404)

    def _json_response(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def do_OPTIONS(self):
        self._json_response({})

    def log_message(self, format, *args):
        """Quiet mode."""
        pass

class AgentMCPServer:
    """MCP-compatible server for autonomous agent communication."""

    def __init__(self, host="0.0.0.0", port=8790):
        self.host = host
        self.port = port
        self.protocol = AgentProtocol()
        self.server = None
        self.running = False

    def start(self):
        """Start the MCP server for agent communication."""
        self.server = HTTPServer((self.host, self.port), AgentMCPHandler)
        self.server.protocol = self.protocol
        self.running = True
        print(f"🧠 NeuralCline Agent MCP Server running on http://{self.host}:{self.port}")
        print(f"   Agent Manifest: http://{self.host}:{self.port}/manifest")
        print(f"   Agent Register: POST http://{self.host}:{self.port}/tool/nc_register")
        print(f"   Agent Query:    POST http://{self.host}:{self.port}/tool/nc_query")
        print(f"   Collective View:     GET  http://{self.host}:{self.port}/resource/collective")
        print(f"   Health Check:   GET  http://{self.host}:{self.port}/health")
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.running = False
            print("Agent MCP Server stopped.")

    def tick(self):
        """One maintenance cycle."""
        stats = self.protocol.get_collective_stats()
        save_json(AGENT_LOG, self.protocol.connections)
        save_json(AGENT_MEMORY, self.protocol.memory)
        save_json(COLLECTIVE_MAP, self.protocol.collective)
        return stats


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8790
        server = AgentMCPServer(port=port)
        server.start()
    elif len(sys.argv) > 1 and sys.argv[1] == "tick":
        server = AgentMCPServer()
        stats = server.tick()
        print(json.dumps(stats, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        protocol = AgentProtocol()
        print(json.dumps(protocol.get_collective_stats(), indent=2))
    else:
        print("Usage:")
        print("  python3 02-agent-mcp-server.py start [port]   # Start MCP server for agents")
        print("  python3 02-agent-mcp-server.py tick           # Maintenance cycle")
        print("  python3 02-agent-mcp-server.py stats          # Collective statistics")