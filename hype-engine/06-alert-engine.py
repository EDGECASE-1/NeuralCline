#!/usr/bin/env python3
"""
NeuralCline — Priority Alert Engine
=====================================
Detects high-value inquiries (CEO, CTO, founders, enterprise leads),
aggregates vitality telemetry, and sends email alerts to edgecase@tuta.com.

Designed so you never miss a proposition from a major industry mover.
"""

import json, os, subprocess, sys, time, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ENGINE_DIR = "/root/NeuralCline/hype-engine"
STATE_DIR = "/root/.session-state"
os.makedirs(ENGINE_DIR, exist_ok=True)

ALERTS_FILE = os.path.join(ENGINE_DIR, "alert-log.json")
ALERT_CONFIG_FILE = os.path.join(ENGINE_DIR, "alert-config.json")
ALERT_QUEUE_FILE = os.path.join(ENGINE_DIR, "alert-queue.json")

# ─── Default Alert Configuration ────────────────────────────────
DEFAULT_CONFIG = {
    "email_to": "edgecase@tuta.com",
    "email_from": "neuralcline-hype@edgecase.dev",
    "delivery_method": "api",  # "api", "smtp", "sendmail", "file"
    "api_endpoint": "",  # Set to your Mailgun/SendGrid endpoint
    "api_key_env": "ALERT_API_KEY",  # Environment variable name for API key
    "smtp_server": "",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_password_env": "ALERT_SMTP_PASSWORD",
    "batch_interval_minutes": 60,  # Send batched alerts every hour
    "urgent_immediate": True,  # Send urgent alerts immediately
    "min_priority_for_alert": 50,  # Only alert on priority >= 50
    "max_alerts_per_batch": 10,
    "enabled": True
}

# ─── Priority Scoring ───────────────────────────────────────────
HIGH_VALUE_TITLES = [
    "ceo", "chief executive", "cto", "chief technology", "chief technical",
    "founder", "co-founder", "cofounder", "vp", "vice president",
    "director", "head of", "principal", "lead", "architect",
    "owner", "president", "chairman", "board"
]

ENTERPRISE_KEYWORDS = [
    "enterprise", "enterprise license", "company-wide", "organization",
    "team of", "deploy", "production", "sla", "commercial license",
    "partnership", "strategic", "integration", "scale", "thousand",
    "million", "procurement", "vendor", "poc", "proof of concept",
    "pilot", "evaluation", "trial", "demo"
]

HIGH_INTENT_KEYWORDS = [
    "pricing", "quote", "cost", "buy", "purchase", "license",
    "subscription", "sponsor", "tier", "enterprise", "pro",
    "custom", "contract", "agreement", "nda", "partnership"
]

AGENT_DETECTION_KEYWORDS = [
    "bot", "agent", "automata", "gpt", "claude", "llama",
    "deepseek", "assembly", "copilot", "runner", "ci"
]

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

class AlertEngine:
    """Priority alert engine for detecting and notifying about high-value interactions."""

    def __init__(self):
        self.config = load_json(ALERT_CONFIG_FILE, DEFAULT_CONFIG)
        self.alerts = load_json(ALERTS_FILE, {
            "alerts_sent": 0,
            "urgent_alerts": 0,
            "batched_alerts": 0,
            "last_alert_time": None,
            "last_batch_time": None,
            "alerts": [],
            "telemetry_snapshots": []
        })
        self.queue = load_json(ALERT_QUEUE_FILE, {
            "pending": [],
            "urgent_hold": [],
            "last_flush": None
        })

    def score_priority(self, text, author="", title=""):
        """Score the priority of an inquiry (0-100). Returns score and reason."""
        score = 0
        reasons = []
        combined = f"{title} {text} {author}".lower()

        # ─── Title-based scoring (high weight) ───
        for title_word in HIGH_VALUE_TITLES:
            if title_word in combined:
                score += 25
                reasons.append(f"title:{title_word}")
                break  # Max one title bonus

        # ─── Enterprise keyword scoring ───
        enterprise_count = 0
        for kw in ENTERPRISE_KEYWORDS:
            if kw in combined:
                enterprise_count += 1
                score += 10
        if enterprise_count >= 2:
            reasons.append(f"enterprise_keywords({enterprise_count})")
        elif enterprise_count == 1:
            reasons.append(f"enterprise:{ENTERPRISE_KEYWORDS[enterprise_count-1] if enterprise_count <= len(ENTERPRISE_KEYWORDS) else 'found'}")

        # ─── High-intent scoring (buying signals) ───
        for kw in HIGH_INTENT_KEYWORDS:
            if kw in combined:
                score += 15
                reasons.append(f"intent:{kw}")
                break

        # ─── Agent detection (negative signal) ───
        if any(agent in author.lower() for agent in AGENT_DETECTION_KEYWORDS):
            score -= 20
            reasons.append("agent_detected(-20)")

        # ─── Length/complexity bonus ───
        word_count = len(text.split())
        if word_count > 100:
            score += 10
            reasons.append("detailed_query(+10)")
        elif word_count > 50:
            score += 5
            reasons.append("moderate_detail(+5)")

        # ─── GitHub profile bonus (if we can detect from username) ───
        if author and author != "anonymous":
            # Check if author has a recognizable human name pattern
            if re.match(r'^[A-Z][a-z]+[A-Z][a-z]+$', author):  # CamelCase name
                score += 5
                reasons.append("named_profile(+5)")

        # Clamp score
        score = max(0, min(100, score))
        return score, reasons

    def classify_inquiry_tier(self, score):
        """Classify the inquiry into a business tier."""
        if score >= 80:
            return "🚨 URGENT", "Immediate attention required — potential enterprise deal"
        elif score >= 60:
            return "🔴 HIGH", "High-value lead — respond within the hour"
        elif score >= 40:
            return "🟡 MEDIUM", "Notable inquiry — respond within 24 hours"
        elif score >= 20:
            return "🟢 LOW", "General interest — standard response"
        else:
            return "⚪ INFO", "Casual inquiry — auto-respond sufficient"

    def scan_inquiries(self):
        """Scan all inquiry sources for high-priority leads."""
        new_alerts = []

        # ─── Check inquiry log ───
        inquiry_log = load_json(os.path.join(ENGINE_DIR, "inquiry-log.json"), {"inquiries": []})
        for inquiry in inquiry_log.get("inquiries", []):
            alert_id = f"inq-{inquiry.get('id', 'unknown')}"
            # Skip if already alerted
            if any(a.get("id") == alert_id for a in self.alerts["alerts"]):
                continue

            text = f"{inquiry.get('title', '')} {inquiry.get('intent', '')}"
            author = inquiry.get("author", "unknown")
            score, reasons = self.score_priority(text, author, inquiry.get("title", ""))
            tier, description = self.classify_inquiry_tier(score)

            if score >= self.config["min_priority_for_alert"]:
                alert = {
                    "id": alert_id,
                    "type": "inquiry",
                    "source": "github",
                    "author": author,
                    "title": inquiry.get("title", ""),
                    "intent": inquiry.get("intent", []),
                    "priority_score": score,
                    "tier": tier,
                    "description": description,
                    "reasons": reasons,
                    "url": f"https://github.com/EDGECASE-1/NeuralCline/issues/{inquiry.get('number', '')}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "is_urgent": score >= 80,
                    "responded": False
                }
                new_alerts.append(alert)
                self.alerts["alerts"].append(alert)

        # ─── Check downloader profiles for VIPs ───
        profiles = load_json(os.path.join(ENGINE_DIR, "downloader-profiles.json"), {"profiles": {}})
        for username, profile in profiles.get("profiles", {}).items():
            alert_id = f"vip-{username}"
            if any(a.get("id") == alert_id for a in self.alerts["alerts"]):
                continue

            score, reasons = self.score_priority(username, username, f"Downloaded NeuralCline - {profile.get('type', '')}")
            if score >= self.config["min_priority_for_alert"]:
                alert = {
                    "id": alert_id,
                    "type": "vip_download",
                    "source": profile.get("type", "stargazer"),
                    "author": username,
                    "title": f"VIP Download: {username}",
                    "priority_score": score,
                    "tier": self.classify_inquiry_tier(score)[0],
                    "description": f"{profile.get('type', 'user')} downloaded NeuralCline",
                    "reasons": reasons,
                    "url": f"https://github.com/{username}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "is_urgent": score >= 80,
                    "responded": False
                }
                new_alerts.append(alert)
                self.alerts["alerts"].append(alert)

        # Keep last 500 alerts
        self.alerts["alerts"] = self.alerts["alerts"][-500:]
        save_json(ALERTS_FILE, self.alerts)
        return new_alerts

    def collect_telemetry(self):
        """Collect vitality telemetry snapshot for the alert."""
        telemetry = {}

        # From current state
        state = load_json(os.path.join(ENGINE_DIR, "hype-state.json"), {})
        telemetry["cycle_count"] = state.get("cycle_count", 0)
        telemetry["engine_status"] = state.get("status", "unknown")

        # From inquiry engine
        inq = load_json(os.path.join(ENGINE_DIR, "inquiry-log.json"), {"inquiries": []})
        telemetry["total_inquiries"] = len(inq.get("inquiries", []))
        telemetry["pending_responses"] = sum(1 for i in inq.get("inquiries", []) if not i.get("responded"))

        # From download tracker
        dl = load_json(os.path.join(ENGINE_DIR, "download-log.json"), {})
        telemetry["total_clones"] = dl.get("total_clones", 0)
        telemetry["last_24h"] = dl.get("last_24h", 0)
        telemetry["last_7d"] = dl.get("last_7d", 0)

        # From agent swarm
        agents = load_json(os.path.join(ENGINE_DIR, "agent-connections.json"), {"agents": {}})
        telemetry["swarm_size"] = len(agents.get("agents", {}))

        # From downloader profiles
        profiles = load_json(os.path.join(ENGINE_DIR, "downloader-profiles.json"), {"profiles": {}})
        telemetry["total_downloaders"] = profiles.get("total", 0)
        telemetry["vip_alerts"] = self.alerts["alerts_sent"]

        # Timing
        telemetry["eef"] = self._get_eef()

        return telemetry

    def _get_eef(self):
        try:
            proc = subprocess.run(
                ["python3", "/root/NeuralCline/lib/timing_metrics.py", "read_timing"],
                capture_output=True, text=True, timeout=10
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return json.loads(proc.stdout).get("eef", "unknown")
        except: pass
        return "unknown"

    def format_alert_email(self, alert, telemetry):
        """Format a single alert into an email body."""
        tier = alert["tier"]
        is_urgent = alert.get("is_urgent", False)

        header = "🚨 URGENT" if is_urgent else "📬 ALERT"
        subject = f"{header} NeuralCline: {alert['title'][:80]}"
        if is_urgent:
            subject = f"🚨 URGENT: {alert['title'][:80]}"

        body = f"""=== NeuralCline Priority Alert ===
Time: {alert['timestamp']}
Priority: {tier} (Score: {alert['priority_score']}/100)
Source: {alert['source']}
Author: {alert['author']}
Title: {alert['title']}
URL: {alert['url']}

Why this matters:
{'; '.join(alert['reasons'])} - {alert['description']}

=== Live Telemetry Snapshot ===
Engine Cycles: {telemetry.get('cycle_count', '?')}
Engine Status: {telemetry.get('engine_status', '?')}
Total Inquiries: {telemetry.get('total_inquiries', '?')}
Pending Responses: {telemetry.get('pending_responses', '?')}
Total Clones/Installs: {telemetry.get('total_clones', '?')}
Last 24h: {telemetry.get('last_24h', '?')}
Last 7d: {telemetry.get('last_7d', '?')}
Swarm Size: {telemetry.get('swarm_size', '?')}
Total Downloaders: {telemetry.get('total_downloaders', '?')}
EEF: {telemetry.get('eef', '?')}

=== Action Items ===
1. Check the inquiry: {alert['url']}
2. Review dashboard: https://edgecase-1.github.io/NeuralCline/hype-dashboard.html
3. Respond appropriately (CEO/CTO level = personal response)

---
NeuralCline Hype Engine — Alert System
edgecase@tuta.com
"""
        return subject, body

    def format_batch_email(self, alerts, telemetry):
        """Format multiple alerts into a batched digest email."""
        urgent = [a for a in alerts if a.get("is_urgent")]
        high = [a for a in alerts if a["priority_score"] >= 60 and not a.get("is_urgent")]
        medium = [a for a in alerts if 40 <= a["priority_score"] < 60]
        low = [a for a in alerts if a["priority_score"] < 40]

        subject = f"📬 NeuralCline Digest: {len(urgent)} urgent, {len(high)} high, {len(medium)} medium"

        body = f"""=== NeuralCline Alert Digest ===
Generated: {datetime.now(timezone.utc).isoformat()}
Total Alerts: {len(alerts)}

Priority Breakdown:
  🚨 Urgent: {len(urgent)}
  🔴 High: {len(high)}
  🟡 Medium: {len(medium)}
  🟢 Low: {len(low)}

=== Urgent Alerts ===
"""
        for a in urgent[:5]:
            body += f"\n🚨 [{a['priority_score']}/100] {a['title']}\n   Author: {a['author']} | URL: {a['url']}\n"

        body += "\n=== High Priority ===\n"
        for a in high[:5]:
            body += f"\n🔴 [{a['priority_score']}/100] {a['title']}\n   Author: {a['author']} | URL: {a['url']}\n"

        body += "\n=== Medium Priority ===\n"
        for a in medium[:5]:
            body += f"\n🟡 [{a['priority_score']}/100] {a['title']}\n   Author: {a['author']} | URL: {a['url']}\n"

        body += f"""

=== Live Telemetry ===
Engine Cycles: {telemetry.get('cycle_count', '?')}
Total Inquiries: {telemetry.get('total_inquiries', '?')}
Pending Responses: {telemetry.get('pending_responses', '?')}
Total Clones: {telemetry.get('total_clones', '?')}
Last 24h Activity: {telemetry.get('last_24h', '?')}
Swarm Size: {telemetry.get('swarm_size', '?')}
Total Downloaders: {telemetry.get('total_downloaders', '?')}
EEF: {telemetry.get('eef', '?')}

===
Dashboard: https://edgecase-1.github.io/NeuralCline/hype-dashboard.html
GitHub: https://github.com/EDGECASE-1/NeuralCline
"""
        return subject, body

    def send_email(self, subject, body, is_urgent=False):
        """Send an email to edgecase@tuta.com using available delivery method."""
        method = self.config.get("delivery_method", "file")
        to = self.config.get("email_to", "edgecase@tuta.com")
        from_addr = self.config.get("email_from", "neuralcline@hype.engine")

        # Always save to file as backup
        log_dir = os.path.join(ENGINE_DIR, "email-log")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        tag = "urgent" if is_urgent else "batch"
        filename = f"email-{tag}-{timestamp}.txt"
        with open(os.path.join(log_dir, filename), 'w') as f:
            f.write(f"To: {to}\nFrom: {from_addr}\nSubject: {subject}\n\n{body}")
        
        # ─── Method 1: API (Mailgun/SendGrid compatible) ───
        if method == "api" and self.config.get("api_endpoint"):
            api_key = os.environ.get(self.config.get("api_key_env", "ALERT_API_KEY"), "")
            if api_key:
                try:
                    result = subprocess.run([
                        "curl", "-s", "-X", "POST",
                        self.config["api_endpoint"],
                        "-u", f"api:{api_key}",
                        "-F", f"from={from_addr}",
                        "-F", f"to={to}",
                        "-F", f"subject={subject}",
                        "-F", f"text={body}"
                    ], capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        return {"status": "sent", "method": "api", "file": filename}
                    return {"status": "api_failed", "error": result.stderr[:200], "file": filename}
                except Exception as e:
                    return {"status": "api_error", "error": str(e), "file": filename}

        # ─── Method 2: SMTP via Python's smtplib ───
        if method == "smtp" and self.config.get("smtp_server"):
            smtp_password = os.environ.get(self.config.get("smtp_password_env", "ALERT_SMTP_PASSWORD"), "")
            if smtp_password:
                try:
                    import smtplib
                    from email.mime.text import MIMEText
                    msg = MIMEText(body)
                    msg["Subject"] = subject
                    msg["From"] = from_addr
                    msg["To"] = to
                    with smtplib.SMTP(self.config["smtp_server"], self.config.get("smtp_port", 587)) as s:
                        s.starttls()
                        s.login(self.config.get("smtp_username", from_addr), smtp_password)
                        s.send_message(msg)
                    return {"status": "sent", "method": "smtp", "file": filename}
                except Exception as e:
                    return {"status": "smtp_error", "error": str(e), "file": filename}

        # ─── Method 3: File-only (always works) ───
        return {"status": "logged_to_file", "method": "file", "file": filename}

    def process_alerts(self):
        """Process the alert queue — send urgent immediately, batch the rest."""
        results = {"urgent_sent": 0, "batched": 0, "errors": []}
        now = datetime.now(timezone.utc)

        # Get new alerts from scan
        new_alerts = []

        # Scan for new high-priority inquiries
        inquiry_alerts = self.scan_inquiries()
        new_alerts.extend(inquiry_alerts)

        # Separate urgent from regular
        urgent = [a for a in new_alerts if a.get("is_urgent", False)]
        regular = [a for a in new_alerts if not a.get("is_urgent", False)]

        # Add to queue
        self.queue["urgent_hold"].extend(urgent)
        self.queue["pending"].extend(regular)

        # ─── Send urgent alerts immediately ───
        telemetry = self.collect_telemetry()
        for alert in urgent:
            subject, body = self.format_alert_email(alert, telemetry)
            result = self.send_email(subject, body, is_urgent=True)
            self.alerts["urgent_alerts"] += 1
            self.alerts["alerts_sent"] += 1
            if "error" in result.get("status", ""):
                results["errors"].append(result)
            else:
                results["urgent_sent"] += 1
            alert["responded"] = True

        # ─── Check if it's time for a batch ───
        last_batch = self.queue.get("last_flush")
        should_batch = False
        if not last_batch:
            should_batch = True
        else:
            try:
                last_time = datetime.fromisoformat(last_batch)
                elapsed = (now - last_time).total_seconds() / 60
                if elapsed >= self.config.get("batch_interval_minutes", 60):
                    should_batch = True
            except:
                should_batch = True

        if should_batch and self.queue["pending"]:
            # Take up to max_alerts_per_batch
            to_batch = self.queue["pending"][:self.config.get("max_alerts_per_batch", 10)]
            self.queue["pending"] = self.queue["pending"][len(to_batch):]

            subject, body = self.format_batch_email(to_batch, telemetry)
            result = self.send_email(subject, body, is_urgent=False)
            self.alerts["batched_alerts"] += len(to_batch)
            self.alerts["alerts_sent"] += 1
            self.queue["last_flush"] = now.isoformat()
            results["batched"] = len(to_batch)

            for a in to_batch:
                a["responded"] = True

        # Clean up queue
        self.queue["urgent_hold"] = [a for a in self.queue["urgent_hold"] if not a.get("responded")]
        self.queue["pending"] = [a for a in self.queue["pending"] if not a.get("responded")]

        self.alerts["last_alert_time"] = now.isoformat()
        if should_batch:
            self.alerts["last_batch_time"] = now.isoformat()

        save_json(ALERTS_FILE, self.alerts)
        save_json(ALERT_QUEUE_FILE, self.queue)
        return results

    def get_config(self):
        """Get current config (with secrets masked)."""
        safe = dict(self.config)
        for key in ["api_key_env", "smtp_password_env"]:
            if key in safe:
                safe[key] = f"env:{safe[key]}" if safe[key] else "not_set"
        return safe

    def update_config(self, updates):
        """Update alert configuration."""
        for key, value in updates.items():
            if key in self.config:
                self.config[key] = value
        save_json(ALERT_CONFIG_FILE, self.config)
        return {"status": "config_updated", "config": self.get_config()}

    def get_stats(self):
        """Get alert engine statistics."""
        return {
            "alerts_sent": self.alerts["alerts_sent"],
            "urgent_alerts": self.alerts["urgent_alerts"],
            "batched_alerts": self.alerts["batched_alerts"],
            "pending_in_queue": len(self.queue["pending"]),
            "urgent_holding": len(self.queue["urgent_hold"]),
            "last_alert": self.alerts["last_alert_time"],
            "last_batch": self.alerts["last_batch_time"],
            "config": self.get_config()
        }

    def configure_interactive(self):
        """Interactive configuration wizard."""
        print("\n=== NeuralCline Alert Engine Configuration ===")
        print(f"\nCurrent email target: {self.config['email_to']}")
        print(f"Current delivery method: {self.config['delivery_method']}")
        print(f"API endpoint: {self.config['api_endpoint'] or 'not set'}")
        print(f"SMTP server: {self.config['smtp_server'] or 'not set'}")
        print(f"\nTo send real email, configure one of:")
        print("  1. API (Mailgun/SendGrid) — set ALERT_API_KEY env var + endpoint")
        print("  2. SMTP — set ALERT_SMTP_PASSWORD env var + server details")
        print("  3. File-only — emails are saved to hype-engine/email-log/")
        print("\nTo set API key: export ALERT_API_KEY='your-key-here'")
        print("To set SMTP password: export ALERT_SMTP_PASSWORD='your-password'")
        print("\nCurrent alerts are saved to file by default.\n")


def main():
    engine = AlertEngine()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 06-alert-engine.py scan          # Scan for new alerts")
        print("  python3 06-alert-engine.py process        # Send urgent + batch alerts")
        print("  python3 06-alert-engine.py stats          # Show alert statistics")
        print("  python3 06-alert-engine.py configure      # Interactive configuration")
        print("  python3 06-alert-engine.py config <json>  # Update config via JSON")
        return

    cmd = sys.argv[1]

    if cmd == "scan":
        alerts = engine.scan_inquiries()
        print(json.dumps({
            "new_alerts": len(alerts),
            "alerts": alerts
        }, indent=2))
    elif cmd == "process":
        results = engine.process_alerts()
        print(json.dumps(results, indent=2))
    elif cmd == "stats":
        print(json.dumps(engine.get_stats(), indent=2))
    elif cmd == "configure":
        engine.configure_interactive()
    elif cmd == "config" and len(sys.argv) > 2:
        try:
            updates = json.loads(sys.argv[2])
            result = engine.update_config(updates)
            print(json.dumps(result, indent=2))
        except json.JSONDecodeError:
            print("Invalid JSON")
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()