#!/usr/bin/env python3
"""
NeuralCline — Industry Attention Monitoring Engine
===================================================
Tracks external signals to measure how much attention and usage
the industry is giving NeuralCline across all channels.

Outputs to: /root/.session-state/attention-metrics.json
"""

import json
import subprocess
import os
import time
from datetime import datetime, timezone

STATE_DIR = "/root/.session-state"
METRICS_FILE = os.path.join(STATE_DIR, "attention-metrics.json")
HISTORY_FILE = os.path.join(STATE_DIR, "attention-history.json")

def gh_graphql(query):
    """Run a GraphQL query via gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            raw = result.stdout.strip()
            if raw.startswith('"data"'):
                raw = raw[7:]
            return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}
    return {"error": "gh CLI failed"}

def get_github_metrics():
    """Get GitHub-specific attention metrics."""
    metrics = {}
    
    # Repo stats
    try:
        r = subprocess.run(
            ["gh", "api", "repos/EDGECASE-1/NeuralCline"],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            d = json.loads(r.stdout)
            metrics["stars"] = d.get("stargazers_count", 0)
            metrics["forks"] = d.get("forks_count", 0)
            metrics["watchers"] = d.get("subscribers_count", 0)
            metrics["open_issues"] = d.get("open_issues_count", 0)
    except:
        metrics["stars"] = "error"
    
    # Discussion activity
    dq = """query { repository(owner:"EDGECASE-1", name:"NeuralCline") {
        discussion(number:2) { comments { totalCount } }
    }}"""
    dr = gh_graphql(dq)
    try:
        metrics["discussion_comments"] = dr["data"]["repository"]["discussion"]["comments"]["totalCount"]
    except:
        metrics["discussion_comments"] = 0
    
    # Clone count (requires token with repo scope)
    try:
        c = subprocess.run(
            ["gh", "api", "repos/EDGECASE-1/NeuralCline/traffic/clones"],
            capture_output=True, text=True, timeout=15
        )
        if c.returncode == 0:
            cd = json.loads(c.stdout)
            metrics["clones_14d"] = cd.get("count", 0)
            metrics["unique_clones_14d"] = cd.get("uniques", 0)
    except:
        metrics["clones_14d"] = "waiting"
    
    # View count
    try:
        v = subprocess.run(
            ["gh", "api", "repos/EDGECASE-1/NeuralCline/traffic/views"],
            capture_output=True, text=True, timeout=15
        )
        if v.returncode == 0:
            vd = json.loads(v.stdout)
            metrics["views_14d"] = vd.get("count", 0)
            metrics["unique_visitors_14d"] = vd.get("uniques", 0)
    except:
        metrics["views_14d"] = "waiting"
    
    # Referrer sources
    try:
        ref = subprocess.run(
            ["gh", "api", "repos/EDGECASE-1/NeuralCline/traffic/popular/referrers"],
            capture_output=True, text=True, timeout=15
        )
        if ref.returncode == 0:
            refs = json.loads(ref.stdout)
            top_refs = {}
            for r in refs[:5]:
                top_refs[r.get("referrer", "unknown")] = r.get("count", 0)
            metrics["top_referrers"] = top_refs
    except:
        metrics["top_referrers"] = {}
    
    # GitHub Search presence
    try:
        s = subprocess.run(
            ["gh", "api", "-X", "GET", "search/repositories", "-f", "q=neuralcline"],
            capture_output=True, text=True, timeout=15
        )
        if s.returncode == 0:
            sd = json.loads(s.stdout)
            metrics["search_results"] = sd.get("total_count", 0)
    except:
        metrics["search_results"] = "error"
    
    # Install script hits (from crash log)
    try:
        if os.path.exists("/root/.session-state/crash-log.ndjson"):
            with open("/root/.session-state/crash-log.ndjson") as f:
                lines = f.readlines()
            metrics["install_attempts"] = len(lines)
        else:
            metrics["install_attempts"] = 0
    except:
        metrics["install_attempts"] = "error"
    
    return metrics

def get_external_metrics():
    """Get external attention signals via web scraping."""
    metrics = {}
    
    # Hacker News presence
    try:
        hn = subprocess.run(
            ["curl", "-s", "-A", "Mozilla/5.0",
             "https://hn.algolia.com/api/v1/search?query=NeuralCline&tags=story&hitsPerPage=5"],
            capture_output=True, text=True, timeout=15
        )
        if hn.returncode == 0:
            hnd = json.loads(hn.stdout)
            metrics["hn_mentions"] = hnd.get("nbHits", 0)
            metrics["hn_stories"] = []
            for hit in hnd.get("hits", [])[:3]:
                metrics["hn_stories"].append({
                    "title": hit.get("title", ""),
                    "points": hit.get("points", 0),
                    "url": hit.get("url", ""),
                    "created_at": hit.get("created_at", "")
                })
    except:
        metrics["hn_mentions"] = "error"
    
    # Reddit presence
    try:
        reddit = subprocess.run(
            ["curl", "-s", "-A", "Mozilla/5.0",
             "https://www.reddit.com/search.json?q=NeuralCline&limit=5"],
            capture_output=True, text=True, timeout=15
        )
        if reddit.returncode == 0:
            rd = json.loads(reddit.stdout)
            metrics["reddit_mentions"] = rd.get("data", {}).get("dist", 0)
            metrics["reddit_posts"] = []
            for child in rd.get("data", {}).get("children", [])[:3]:
                d = child.get("data", {})
                metrics["reddit_posts"].append({
                    "title": d.get("title", ""),
                    "subreddit": d.get("subreddit", ""),
                    "score": d.get("score", 0),
                    "url": d.get("url", "")
                })
    except:
        metrics["reddit_mentions"] = "error"
    
    # Twitter/X presence
    try:
        twitter = subprocess.run(
            ["curl", "-s", "-A", "Mozilla/5.0",
             f"https://api.twitter.com/2/tweets/search/recent?query=NeuralCline&max_results=5"],
            capture_output=True, text=True, timeout=15
        )
        if twitter.returncode == 0:
            td = json.loads(twitter.stdout)
            metrics["twitter_mentions"] = td.get("meta", {}).get("result_count", 0)
        else:
            metrics["twitter_mentions"] = "no_api_key"
    except:
        metrics["twitter_mentions"] = "no_api_key"
    
    # Dev.to presence
    try:
        devto = subprocess.run(
            ["curl", "-s", "https://dev.to/api/articles?query=NeuralCline&per_page=3"],
            capture_output=True, text=True, timeout=15
        )
        if devto.returncode == 0:
            dd = json.loads(devto.stdout)
            metrics["devto_mentions"] = len(dd)
    except:
        metrics["devto_mentions"] = 0
    
    return metrics

def compute_attention_score(github, external):
    """Compute a composite attention score (0-100)."""
    score = 0
    max_score = 100
    
    # GitHub signals (50% of weight)
    stars = github.get("stars", 0)
    if isinstance(stars, int):
        if stars >= 1000: score += 20
        elif stars >= 500: score += 16
        elif stars >= 100: score += 12
        elif stars >= 50: score += 8
        elif stars >= 10: score += 4
        elif stars >= 1: score += 2
    
    clones = github.get("clones_14d", 0)
    if isinstance(clones, int):
        if clones >= 10000: score += 10
        elif clones >= 1000: score += 8
        elif clones >= 100: score += 4
        elif clones >= 10: score += 2
    
    views = github.get("views_14d", 0)
    if isinstance(views, int):
        if views >= 100000: score += 10
        elif views >= 10000: score += 8
        elif views >= 1000: score += 4
        elif views >= 100: score += 2
    
    installs = github.get("install_attempts", 0)
    if isinstance(installs, int):
        if installs >= 1000: score += 10
        elif installs >= 100: score += 8
        elif installs >= 10: score += 4
        elif installs >= 1: score += 2
    
    # External signals (50% of weight)
    hn = external.get("hn_mentions", 0)
    if isinstance(hn, int):
        if hn >= 10: score += 15
        elif hn >= 5: score += 10
        elif hn >= 1: score += 5
    
    reddit = external.get("reddit_mentions", 0)
    if isinstance(reddit, int):
        if reddit >= 10: score += 15
        elif reddit >= 5: score += 10
        elif reddit >= 1: score += 5
    
    twitter = external.get("twitter_mentions", 0)
    if isinstance(twitter, int):
        if twitter >= 10: score += 5
        elif twitter >= 1: score += 2
    
    devto = external.get("devto_mentions", 0)
    if isinstance(devto, int):
        if devto >= 1: score += 5
    
    # Cap at 100
    return min(score, max_score)

def get_attention_level(score):
    """Get a human-readable attention level."""
    if score >= 80:
        return "🚀 VIRAL — Industry-wide attention"
    elif score >= 60:
        return "🔥 HIGH — Trending, agencies taking notice"
    elif score >= 40:
        return "📈 MODERATE — Growing organic interest"
    elif score >= 20:
        return "📊 LOW — Early adoption phase"
    else:
        return "🌱 SEEDLING — Just launched"

def main():
    print("🧠 NeuralCline — Industry Attention Monitor")
    print("=" * 50)
    print()
    
    # Gather metrics
    print("📡 Gathering GitHub metrics...")
    github = get_github_metrics()
    print("📡 Gathering external signals...")
    external = get_external_metrics()
    
    # Compute score
    score = compute_attention_score(github, external)
    level = get_attention_level(score)
    
    # Build report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attention_score": score,
        "attention_level": level,
        "github": github,
        "external": external
    }
    
    # Save metrics
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(METRICS_FILE, "w") as f:
        json.dump(report, f, indent=2)
    
    # Append to history
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                history = json.load(f)
        except:
            pass
    
    history.append({
        "timestamp": report["timestamp"],
        "attention_score": score,
        "stars": github.get("stars", 0),
        "clones": github.get("clones_14d", 0),
        "views": github.get("views_14d", 0),
        "hn_mentions": external.get("hn_mentions", 0),
        "reddit_mentions": external.get("reddit_mentions", 0)
    })
    
    # Keep last 100 entries
    history = history[-100:]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)
    
    # Print report
    print()
    print(f"   Attention Score: {score}/100")
    print(f"   Level:           {level}")
    print()
    print("   GitHub Stats:")
    print(f"   ├─ Stars:         {github.get('stars', '?')}")
    print(f"   ├─ Forks:         {github.get('forks', '?')}")
    print(f"   ├─ Watchers:      {github.get('watchers', '?')}")
    print(f"   ├─ Views (14d):   {github.get('views_14d', '?')}")
    print(f"   ├─ Clones (14d):  {github.get('clones_14d', '?')}")
    print(f"   ├─ Search hits:   {github.get('search_results', '?')}")
    print(f"   └─ Installs:      {github.get('install_attempts', '?')}")
    print()
    print("   External Signals:")
    print(f"   ├─ HN Mentions:   {external.get('hn_mentions', '?')}")
    print(f"   ├─ Reddit Posts:  {external.get('reddit_mentions', '?')}")
    print(f"   ├─ Twitter:       {external.get('twitter_mentions', '?')}")
    print(f"   └─ Dev.to:        {external.get('devto_mentions', '?')}")
    print()
    
    # HN stories if any
    if external.get("hn_stories"):
        print("   Hacker News Stories:")
        for s in external["hn_stories"]:
            print(f"   ├─ {s['title']} ({s.get('points', 0)} pts)")
    
    # Reddit posts if any
    if external.get("reddit_posts"):
        print("   Reddit Posts:")
        for p in external["reddit_posts"]:
            print(f"   ├─ r/{p['subreddit']}: {p['title']} ({p.get('score', 0)} pts)")
    
    print()
    print(f"   Report saved to: {METRICS_FILE}")
    print(f"   History:         {HISTORY_FILE} ({len(history)} entries)")
    print()
    
    # Save to Gist for public visibility
    if score > 0:
        print("   📤 Saving to GitHub Gist for public dashboard...")
        gist_content = f"""# NeuralCline — Live Attention Dashboard

Last updated: {report['timestamp']}

## Attention Score: {score}/100 — {level}

### GitHub
| Metric | Value |
|--------|-------|
| Stars | {github.get('stars', '?')} |
| Forks | {github.get('forks', '?')} |
| Views (14d) | {github.get('views_14d', '?')} |
| Clones (14d) | {github.get('clones_14d', '?')} |
| Installs | {github.get('install_attempts', '?')} |

### External
| Metric | Value |
|--------|-------|
| HN Mentions | {external.get('hn_mentions', '?')} |
| Reddit Posts | {external.get('reddit_mentions', '?')} |
| Twitter Mentions | {external.get('twitter_mentions', '?')} |
| Dev.to Articles | {external.get('devto_mentions', '?')} |

---

*Auto-updated by NeuralCline Attention Monitor*
"""
        try:
            gist_id = None
            # Check if we already have a metrics gist
            gists_result = subprocess.run(
                ["gh", "api", "users/EDGECASE-1/gists"],
                capture_output=True, text=True, timeout=15
            )
            if gists_result.returncode == 0:
                gists = json.loads(gists_result.stdout)
                for g in gists:
                    if "NeuralCline_Metrics" in str(g.get("files", {})):
                        gist_id = g["id"]
                        break
            
            if gist_id:
                # Update existing gist
                subprocess.run(
                    ["gh", "api", f"gists/{gist_id}", "-X", "PATCH",
                     "-F", f"files[NeuralCline_Metrics.md][content]={gist_content}"],
                    capture_output=True, timeout=15
                )
                print(f"   ✅ Updated gist: https://gist.github.com/EDGECASE-1/{gist_id}")
            else:
                # Create new gist
                result = subprocess.run(
                    ["gh", "api", "gists", "-X", "POST",
                     "-F", "description=NeuralCline Live Attention Dashboard",
                     "-F", "public=true",
                     "-F", f"files[NeuralCline_Metrics.md][content]={gist_content}"],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode == 0:
                    d = json.loads(result.stdout)
                    print(f"   ✅ Created gist: {d.get('html_url', '')}")
        except Exception as e:
            print(f"   ⚠️ Gist update failed: {e}")
    
    return report

if __name__ == "__main__":
    main()