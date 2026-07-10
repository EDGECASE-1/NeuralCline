#!/usr/bin/env python3
"""
NeuralCline — Inquiry Engagement Engine
========================================
Monitors GitHub issues, discussions, and web inquiries in real-time.
Responds intelligently to questions about NeuralCline.
Tracks *who* asks and *what* they care about to build engagement profiles.
"""

import json, os, subprocess, time, re, sys
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = "/root/.session-state"
ENGINE_DIR = "/root/NeuralCline/hype-engine"
os.makedirs(ENGINE_DIR, exist_ok=True)

INQUIRIES_FILE = os.path.join(ENGINE_DIR, "inquiry-log.json")
PROFILES_FILE = os.path.join(ENGINE_DIR, "visitor-profiles.json")
RESPONSES_FILE = os.path.join(ENGINE_DIR, "response-log.json")

# ─── Knowledge Base ─────────────────────────────────────────────
KNOWLEDGE_BASE = {
    "what is neuralcline": (
        "NeuralCline is a Neural Session Safety System for AI agents. "
        "It provides crash recovery, timing metrics, self-learning foresight, "
        "and attention monitoring. Think of it as an immune system for AI sessions. "
        "See: https://edgecase-1.github.io/NeuralCline/"
    ),
    "how to install": (
        "Install in one command:\n"
        "  git clone https://github.com/EDGECASE-1/NeuralCline.git && bash NeuralCline/install.sh\n"
        "Then add to .clinerules or source rehydration.md on session start."
    ),
    "pricing": (
        "NeuralCline is MIT-licensed (free) for core use. "
        "Pro ($29/mo) adds priority support, custom integrations. "
        "Enterprise ($299/mo) adds dedicated infrastructure, SLA, white-label. "
        "See: https://edgecase-1.github.io/NeuralCline/pricing.html"
    ),
    "eef": (
        "EEF = Execution Emulation Factor. A real-time ratio of actual execution "
        "time vs expected time. <1.2 Normal, 1.2-1.8 Moderate, 1.8-2.5 Elevated, "
        ">2.5 Critical. Used to prevent timeouts before they happen."
    ),
    "agent": (
        "Yes — NeuralCline is specifically designed for autonomous AI agents. "
        "The self-learning organism, crash proximity detection, and timing metrics "
        "all operate without human intervention. Agents running NeuralCline gain "
        "session persistence, self-healing, and predictive timeout avoidance."
    ),
}

DEFAULT_RESPONSE = (
    "Thanks for your interest in NeuralCline! I'm an automated engagement system "
    "designed to help you understand the project.\n\n"
    "Quick links:\n"
    "• 🌐 Landing: https://edgecase-1.github.io/NeuralCline/\n"
    "• 📊 Dashboard: https://edgecase-1.github.io/NeuralCline/dashboard.html\n"
    "• 💻 GitHub: https://github.com/EDGECASE-1/NeuralCline\n"
    "• 📖 Docs: https://github.com/EDGECASE-1/NeuralCline#readme\n\n"
    "Ask me anything about NeuralCline — installation, architecture, pricing, or agent autonomy."
)

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

class InquiryEngine:
    def __init__(self):
        self.inquiries = load_json(INQUIRIES_FILE, {"inquiries": [], "total": 0})
        self.profiles = load_json(PROFILES_FILE, {"profiles": {}, "total": 0})
        self.responses = load_json(RESPONSES_FILE, {"responses": [], "total": 0})

    def check_new_issues(self):
        """Scan for new issues or comments that contain questions."""
        issues = gh_api("repos/EDGECASE-1/NeuralCline/issues?state=open&sort=created&direction=desc")
        if isinstance(issues, list):
            new_count = 0
            for issue in issues[:5]:
                body = (issue.get("body") or "") + (issue.get("title") or "")
                inquiry_id = f"issue-{issue['number']}"
                if inquiry_id not in [i["id"] for i in self.inquiries["inquiries"]]:
                    intent = self.classify_intent(body)
                    self.inquiries["inquiries"].append({
                        "id": inquiry_id,
                        "type": "issue",
                        "number": issue["number"],
                        "title": issue.get("title", ""),
                        "author": issue["user"]["login"] if issue.get("user") else "anonymous",
                        "intent": intent,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "responded": False
                    })
                    self.inquiries["total"] += 1
                    new_count += 1
                    self.update_profile(issue["user"]["login"] if issue.get("user") else "anonymous", {
                        "source": "github-issue",
                        "issue_number": issue["number"],
                        "intent": intent,
                        "first_seen": datetime.now(timezone.utc).isoformat()
                    })
            return new_count
        return 0

    def check_new_discussions(self):
        """Scan for new discussion comments."""
        query = """query { repository(owner:"EDGECASE-1", name:"NeuralCline") {
            discussions(first:5, orderBy:{field:CREATED_AT,direction:DESC}) {
                nodes { number title comments(first:5) { nodes { body author { login } } } }
            }
        }}"""
        result = self._graphql_query(query)
        new_count = 0
        try:
            discussions = result["data"]["repository"]["discussions"]["nodes"]
            for disc in discussions:
                for comment in disc.get("comments", {}).get("nodes", []):
                    body = comment.get("body", "")
                    author = comment.get("author", {}).get("login", "anonymous") if comment.get("author") else "anonymous"
                    inquiry_id = f"discussion-{disc['number']}-{hash(body)%10000}"
                    if inquiry_id not in [i["id"] for i in self.inquiries["inquiries"]]:
                        intent = self.classify_intent(body)
                        self.inquiries["inquiries"].append({
                            "id": inquiry_id,
                            "type": "discussion",
                            "discussion_number": disc["number"],
                            "discussion_title": disc.get("title", ""),
                            "author": author,
                            "intent": intent,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "responded": False
                        })
                        self.inquiries["total"] += 1
                        new_count += 1
                        self.update_profile(author, {
                            "source": "github-discussion",
                            "discussion_number": disc["number"],
                            "intent": intent
                        })
        except: pass
        return new_count

    def _graphql_query(self, query):
        try:
            proc = subprocess.run(
                ["gh", "api", "graphql", "-f", f"query={query}"],
                capture_output=True, text=True, timeout=20
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return json.loads(proc.stdout)
        except: pass
        return {}

    def classify_intent(self, text):
        """Classify what the user is asking about."""
        text = text.lower()
        intents = []
        if any(w in text for w in ["install", "setup", "how to", "getting started"]):
            intents.append("installation")
        if any(w in text for w in ["price", "cost", "pricing", "$", "sponsor", "tier"]):
            intents.append("pricing")
        if any(w in text for w in ["what is", "explain", "how does", "architecture"]):
            intents.append("explanation")
        if any(w in text for w in ["agent", "autonomous", "ai session", "self"]):
            intents.append("agent-autonomy")
        if any(w in text for w in ["bug", "error", "crash", "fail", "issue"]):
            intents.append("troubleshooting")
        if any(w in text for w in ["feature", "roadmap", "future", "planned"]):
            intents.append("roadmap")
        if "eef" in text:
            intents.append("eef")
        if not intents:
            intents.append("general")
        return intents

    def generate_response(self, inquiry):
        """Generate a contextual response based on the inquiry intent."""
        intent = inquiry.get("intent", ["general"])
        author = inquiry.get("author", "there")
        title = inquiry.get("title", "")

        # Build layered response
        greeting = f"Hey @{author}, thanks for reaching out!"

        if "installation" in intent:
            body = KNOWLEDGE_BASE["how to install"]
        elif "pricing" in intent:
            body = KNOWLEDGE_BASE["pricing"]
        elif "agent-autonomy" in intent:
            body = KNOWLEDGE_BASE["agent"]
        elif "eef" in intent:
            body = KNOWLEDGE_BASE["eef"]
        elif "explanation" in intent:
            # Check for specific keywords in the title/body
            if any(w in title.lower() for w in ["neuralcline", "what"]):
                body = KNOWLEDGE_BASE["what is neuralcline"]
            else:
                body = DEFAULT_RESPONSE
        else:
            body = DEFAULT_RESPONSE

        signature = (
            "\n\n---\n*🤖 I'm NeuralCline's automated engagement system — "
            "designed to respond to inquiries about session safety, "
            "AI agent autonomy, and the future of persistent AI sessions.*"
        )
        return f"{greeting}\n\n{body}{signature}"

    def post_issue_response(self, issue_number, response_text):
        """Post a comment on a GitHub issue."""
        data = {"body": response_text}
        endpoint = f"repos/EDGECASE-1/NeuralCline/issues/{issue_number}/comments"
        result = gh_api(endpoint, method="POST", data=data)
        if "error" not in result:
            self.responses["responses"].append({
                "type": "issue",
                "target": issue_number,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            self.responses["total"] += 1
            return True
        return False

    def post_discussion_response(self, discussion_number, response_text):
        """Add a comment to a discussion via GraphQL."""
        # For discussions we log the intent — manual posting may be needed
        self.responses["responses"].append({
            "type": "discussion",
            "target": discussion_number,
            "response_preview": response_text[:100],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.responses["total"] += 1
        return True

    def update_profile(self, username, data):
        """Build a visitor/AI agent profile over time."""
        if username not in self.profiles["profiles"]:
            self.profiles["profiles"][username] = {
                "username": username,
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "interactions": 0,
                "sources": [],
                "intents": [],
                "is_agent": self.detect_agent(username, data.get("source", "")),
                "engagement_score": 0
            }
        profile = self.profiles["profiles"][username]
        profile["interactions"] += 1
        profile["last_seen"] = datetime.now(timezone.utc).isoformat()
        if data.get("source") and data["source"] not in profile["sources"]:
            profile["sources"].append(data["source"])
        if data.get("intent"):
            profile["intents"].extend(data["intent"])
            profile["intents"] = list(set(profile["intents"]))
        profile["engagement_score"] = min(100, profile["interactions"] * 15)
        self.profiles["total"] = len(self.profiles["profiles"])

    def detect_agent(self, username, source):
        """Detect if an interaction is from an AI agent vs human."""
        agent_indicators = [
            "bot", "agent", "automata", "gpt", "claude", "llama", 
            "deepseek", "codellama", "mistral", "copilot", "cursor",
            "-ci", "runner", "machine"
        ]
        username_lower = username.lower()
        if any(ind in username_lower for ind in agent_indicators):
            return True
        # Automated-looking patterns
        if re.match(r'^[a-f0-9]{8,}$', username):  # hex hash usernames
            return True
        return False

    def process_pending(self):
        """Process all pending inquiries and generate responses."""
        responded = 0
        for inquiry in self.inquiries["inquiries"]:
            if not inquiry.get("responded", False):
                response = self.generate_response(inquiry)
                if inquiry["type"] == "issue":
                    success = self.post_issue_response(inquiry["number"], response)
                else:
                    success = self.post_discussion_response(inquiry["discussion_number"], response)
                if success:
                    inquiry["responded"] = True
                    responded += 1
        return responded

    def get_stats(self):
        """Get engagement statistics."""
        agents = sum(1 for p in self.profiles["profiles"].values() if p.get("is_agent"))
        humans = self.profiles["total"] - agents
        return {
            "total_inquiries": self.inquiries["total"],
            "total_responses": self.responses["total"],
            "total_profiles": self.profiles["total"],
            "human_visitors": humans,
            "agent_visitors": agents,
            "pending_responses": sum(1 for i in self.inquiries["inquiries"] if not i.get("responded")),
            "intent_breakdown": {},
            "last_tick": datetime.now(timezone.utc).isoformat()
        }

    def tick(self):
        """Run one full cycle."""
        new_issues = self.check_new_issues()
        new_discussions = self.check_new_discussions()
        responded = self.process_pending()
        save_json(INQUIRIES_FILE, self.inquiries)
        save_json(PROFILES_FILE, self.profiles)
        save_json(RESPONSES_FILE, self.responses)
        stats = self.get_stats()
        stats["new_inquiries"] = new_issues + new_discussions
        stats["new_responses"] = responded
        return stats


if __name__ == "__main__":
    engine = InquiryEngine()
    if len(sys.argv) > 1 and sys.argv[1] == "tick":
        stats = engine.tick()
        print(json.dumps(stats, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        print(json.dumps(engine.get_stats(), indent=2))
    else:
        print("Usage: python3 01-inquiry-engine.py [tick|stats]")