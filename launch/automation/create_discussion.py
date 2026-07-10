#!/usr/bin/env python3
"""
NeuralCline Launch Automation — Create GitHub Discussion
=========================================================
Creates the launch announcement as a GitHub Discussion via GraphQL.
"""

import json
import subprocess
import sys

REPO = "EDGECASE-1/NeuralCline"
REPO_ID = "R_kgDOTT2yKQ"
CATEGORY_ID = "DIC_kwDOTT2yKc4DA3mX"

TITLE = "NeuralCline — Session Safety Layer for AI Coding Agents (99.7% crash survival)"

# Read body from file
with open("/root/NeuralCline/launch/automation/discussion-body.md", "r") as f:
    BODY = f.read()

def gh_graphql(query):
    """Run a GraphQL query via gh CLI and return parsed JSON."""
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"❌ gh CLI error: {result.stderr}")
        return None
    # Parse the JSON output (may have leading "data" wrapper)
    raw = result.stdout.strip()
    if raw.startswith('"data"'):
        # Strip the outer wrapping
        raw = raw[7:]  # remove '"data": '
    return json.loads(raw)

def create_discussion():
    """Create the launch discussion."""
    # Escape the body for GraphQL
    escaped_body = json.dumps(BODY)  # JSON-escaped string
    
    mutation = f"""
    mutation {{
      createDiscussion(input: {{
        repositoryId: "{REPO_ID}",
        title: {json.dumps(TITLE)},
        body: {escaped_body},
        categoryId: "{CATEGORY_ID}"
      }}) {{
        discussion {{
          id
          url
        }}
      }}
    }}
    """
    
    result = gh_graphql(mutation)
    if result and "data" in result:
        discussion = result["data"].get("createDiscussion", {}).get("discussion", {})
        url = discussion.get("url", "UNKNOWN")
        did = discussion.get("id", "UNKNOWN")
        print(f"✅ Discussion created!")
        print(f"   URL: {url}")
        print(f"   ID:  {did}")
        
        # Save for other scripts
        with open("/root/.session-state/last-discussion-url.txt", "w") as f:
            f.write(url)
        with open("/root/.session-state/last-discussion-id.txt", "w") as f:
            f.write(did)
        return url
    else:
        print(f"❌ Failed to create discussion")
        if result and "errors" in result:
            for err in result["errors"]:
                print(f"   Error: {err.get('message', 'Unknown')}")
        return None

if __name__ == "__main__":
    url = create_discussion()
    if url:
        print(f"\n📌 Open it: {url}")
        sys.exit(0)
    else:
        sys.exit(1)