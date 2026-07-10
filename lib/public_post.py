#!/usr/bin/env python3
"""
NeuralCline Public Engagement Poster
=====================================
Uses Puppeteer to post content to GitHub Discussions/Issues,
Reddit, Twitter/X, and other platforms from this environment.

Usage:
  python3 public_post.py github-issue "<body>" [--repo owner/repo] [--title "title"]
  python3 public_post.py github-discussion "<body>" [--repo owner/repo] [--title "title"]
  python3 public_post.py status
"""

import json
import os
import subprocess
import sys
import tempfile

PUPPETEER_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "node_scripts", "post_to_platform.js")
NODE = "/usr/bin/node"


def ensure_node_script():
    """Ensure the Puppeteer Node.js script exists."""
    os.makedirs(os.path.dirname(PUPPETEER_SCRIPT), exist_ok=True)
    if not os.path.exists(PUPPETEER_SCRIPT):
        with open(PUPPETEER_SCRIPT, 'w') as f:
            f.write(r'''const puppeteer = require('puppeteer');
const args = process.argv.slice(2);
const action = args[0];

async function postToGitHub(body, repo, title, type) {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  // Get token from env
  const token = process.env.GH_TOKEN || process.env.GITHUB_TOKEN;
  if (!token) {
    console.log('ERROR: No GitHub token found. Set GH_TOKEN env var.');
    await browser.close();
    process.exit(1);
  }
  // Use the GitHub API directly via fetch
  const url = type === 'issue'
    ? `https://api.github.com/repos/${repo}/issues`
    : `https://api.github.com/repos/${repo}/discussions`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      'User-Agent': 'NeuralCline-Poster/1.0'
    },
    body: JSON.stringify({ title, body })
  });
  const result = await response.json();
  console.log(JSON.stringify({ status: response.status, url: result.html_url || result.url, id: result.id }));
  await browser.close();
}

async function status() {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  console.log(JSON.stringify({ status: 'ok', browser: 'chromium', mode: 'headless' }));
  await browser.close();
}

(async () => {
  if (action === 'github-issue') {
    const body = args[1] || '';
    const repo = process.argv.find((a,i) => a === '--repo' ? process.argv[i+1] : null) || 'EDGECASE-1/NeuralCline';
    const title = process.argv.find((a,i) => a === '--title' ? process.argv[i+1] : null) || 'NeuralCline Update';
    await postToGitHub(body, repo, title, 'issue');
  } else if (action === 'status') {
    await status();
  } else {
    console.log(JSON.stringify({ error: 'Unknown action', usage: 'github-issue|status' }));
    process.exit(1);
  }
})();
''')
    return True


def cmd_github_issue(args):
    """Post to GitHub Issues via the API."""
    body = args[0] if args else ""
    repo = None
    title = None
    for i, a in enumerate(args):
        if a == "--repo" and i + 1 < len(args):
            repo = args[i + 1]
        elif a == "--title" and i + 1 < len(args):
            title = args[i + 1]
    if not repo:
        repo = "EDGECASE-1/NeuralCline"
    if not title:
        title = "NeuralCline Update"
    ensure_node_script()
    env = os.environ.copy()
    result = subprocess.run(
        [NODE, PUPPETEER_SCRIPT, "github-issue", body, "--repo", repo, "--title", title],
        capture_output=True, text=True, env=env, timeout=60
    )
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr[:500]}", file=sys.stderr)


def cmd_status(args):
    """Test the browser is working."""
    ensure_node_script()
    result = subprocess.run(
        [NODE, PUPPETEER_SCRIPT, "status"],
        capture_output=True, text=True, timeout=30
    )
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr[:500]}", file=sys.stderr)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "github-issue":
        cmd_github_issue(sys.argv[2:])
    elif cmd == "status":
        cmd_status(sys.argv[2:])
    else:
        print("Usage: python3 public_post.py [github-issue|status]")
        sys.exit(1)