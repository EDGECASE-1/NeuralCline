# 🧠 NeuralCline — API Injection Surface Map & Agency Feed Strategy

## Section 1: `gh` API Injection Points (GitHub-Native)

Every GitHub API endpoint we can write to directly via `gh api`:

### Content Injection

| Endpoint | Method | What It Creates | `gh` Command |
|----------|--------|----------------|--------------|
| **Gists** | POST | Public gist with content | `gh api gists -X POST -F 'files[name][content]=@file'` |
| **Releases** | POST | GitHub Release with tag | `gh api repos/{owner}/{repo}/releases -X POST -f tag_name=v1.0 -f name="Title" -f body="Body"` |
| **Release Assets** | POST | Binary/text asset attached to release | `gh api repos/{owner}/{repo}/releases/{id}/assets -X POST -H "Content-Type: application/octet-stream" --input file` |
| **Wiki Pages** | PUT | Wiki page content | `gh api repos/{owner}/{repo}/wiki/page -X PUT -f content="..."` |
| **Git Blobs** | POST | Raw binary/text blob | `gh api repos/{owner}/{repo}/git/blobs -X POST -f content="..." -f encoding="utf-8"` |
| **Git Trees** | POST | Directory tree object | `gh api repos/{owner}/{repo}/git/trees -X POST -F tree='[{"path":"file","mode":"100644","type":"blob","sha":"..."}]'` |
| **Git Commits** | POST | Direct commit to any branch | `gh api repos/{owner}/{repo}/git/commits -X POST -f message="..." -f tree="..."` |
| **Git Refs** | POST | Create any branch/tag | `gh api repos/{owner}/{repo}/git/refs -X POST -f ref="refs/heads/branch" -f sha="..."` |
| **Repository Topics** | PUT | Set repo topics | `gh api repos/{owner}/{repo}/topics -X PUT -F names='["topic1","topic2"]'` |
| **Social Preview** | PUT | Set OG image for repo | `gh api repos/{owner}/{repo}/social_preview -X PUT -F source='{"branch":"master","path":"preview.png"}'` |
| **Repository Properties** | PATCH | Custom metadata | `gh api repos/{owner}/{repo}/properties/values -X PATCH -F properties='[{"property_name":"key","value":"val"}]'` |

### Social Injection (Engagement Signals)

| Endpoint | Method | What It Does | `gh` Command |
|----------|--------|--------------|--------------|
| **Issue Comments** | POST | Comment on any issue | `gh api repos/{owner}/{repo}/issues/{n}/comments -X POST -f body="..."` |
| **Discussion Comments** | GraphQL | Reply to discussion | `gh api graphql -f query='mutation { addDiscussionComment(input:{discussionId:"...",body:"..."}){comment{id}} }'` |
| **Reactions** | POST | Add 👍👎🎉🚀❤️ to issues/comments | `gh api repos/{owner}/{repo}/issues/{n}/reactions -X POST -f content="+1"` |
| **PR Reviews** | POST | Submit code review | `gh api repos/{owner}/{repo}/pulls/{n}/reviews -X POST -f body="..." -f event="APPROVE"` |
| **Labels** | POST | Create label | `gh api repos/{owner}/{repo}/labels -X POST -f name="..." -f color="..."` |
| **Milestones** | POST | Create milestone | `gh api repos/{owner}/{repo}/milestones -X POST -f title="..." -f due_on="..."` |
| **Projects** | POST | Create project board | `gh api repos/{owner}/{repo}/projects -X POST -f name="..."` |
| **Project Cards** | POST | Add card to project column | `gh api projects/columns/{id}/cards -X POST -f note="..."` |

### Infrastructure Injection

| Endpoint | Method | What It Does | `gh` Command |
|----------|--------|--------------|--------------|
| **Actions Workflows** | POST | Trigger workflow run | `gh api repos/{owner}/{repo}/actions/workflows/{id}/dispatches -X POST -f ref="master"` |
| **Actions Secrets** | PUT | Set encrypted secret | `gh api repos/{owner}/{repo}/actions/secrets/{name} -X PUT -f encrypted_value="..."` |
| **Deployments** | POST | Create deployment | `gh api repos/{owner}/{repo}/deployments -X POST -f ref="master" -f environment="production"` |
| **Deployment Status** | POST | Update deployment status | `gh api repos/{owner}/{repo}/deployments/{id}/statuses -X POST -f state="success"` |
| **Environments** | PUT | Create environment | `gh api repos/{owner}/{repo}/environments/{name} -X PUT` |
| **Pages** | POST | Create/update GitHub Pages | `gh api repos/{owner}/{repo}/pages -X POST --input pages.json` |
| **Pages Build** | POST | Request pages rebuild | `gh api repos/{owner}/{repo}/pages/builds -X POST` |
| **Code Scanning** | POST | Upload SARIF results | `gh api repos/{owner}/{repo}/code-scanning/sarifs -X POST -f commit_sha="..." -f sarif="@file.sarif"` |
| **Dependabot Alerts** | PATCH | Dismiss/update alerts | `gh api repos/{owner}/{repo}/dependabot/alerts/{n} -X PATCH -f state="dismissed"` |

### Notifications & Discovery Injection

| Endpoint | Method | What It Does | `gh` Command |
|----------|--------|--------------|--------------|
| **Star** | PUT | Star a repo (not own) | `gh api user/starred/{owner}/{repo} -X PUT` |
| **Watch** | PUT | Watch a repo (not own) | `gh api repos/{owner}/{repo}/subscription -X PUT -f subscribed=true` |
| **Follow** | PUT | Follow a user | `gh api user/following/{user} -X PUT` |
| **Sponsor** | POST | Sponsor a project | `gh api user/sponsorships -X POST -F sponsorable_login="user" -F tier_id=...` |
| **Issue** | POST | Create issue (already doing) | `gh issue create` |
| **Pull Request** | POST | Create PR | `gh pr create` |
| **Gist Comment** | POST | Comment on gist | `gh api gists/{id}/comments -X POST -f body="..."` |
| **Gist Fork** | POST | Fork a gist | `gh api gists/{id}/forks -X POST` |

---

## Section 2: External Platform Direct Injection

### Platforms with Open APIs (No OAuth Required)

| Platform | Endpoint | Method | Auth Required | `curl` Command |
|----------|----------|--------|---------------|----------------|
| **Dev.to** | `POST /api/articles` | API Key | Yes (simple key) | `curl -H "api-key: $KEY" -H "Content-Type: application/json" -d @article.json https://dev.to/api/articles` |
| **Lobste.rs** | `POST /stories` | API Key | Yes (invite + key) | `curl -H "X-Api-Key: $KEY" -d url=... -d title=... https://lobste.rs/stories` |
| **Medium** | `POST /publications/{id}/posts` | Integration Token | Yes | `curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d @post.json https://api.medium.com/v1/publications/{id}/posts` |
| **Hugging Face** | `POST /api/repos/create` | Token | Yes | `curl -H "Authorization: Bearer $TOKEN" https://huggingface.co/api/repos/create -d name="NeuralCline" -d type="space"` |
| **GitLab** | `POST /api/v4/projects` | Token | Yes | `curl -H "PRIVATE-TOKEN: $TOKEN" https://gitlab.com/api/v4/projects -d name="NeuralCline"` |
| **Bitbucket** | `POST /2.0/repositories` | OAuth | Yes | `curl -u user:pass https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}` |
| **Codeberg** | `POST /api/v1/repos/migrate` | Token | Yes | `curl -H "Authorization: token $TOKEN" https://codeberg.org/api/v1/repos/migrate` |
| **SourceForge** | `POST /projects` | API Key | Yes | `curl -H "Authorization: Bearer $TOKEN" https://sourceforge.net/rest/p/projects` |
| **Notist** | `POST /api/v1/talks` | API Key | Yes | `curl -H "Authorization: Token $TOKEN" https://noti.st/api/v1/talks` |
| **Telegram** | `POST /bot{token}/sendMessage` | Bot Token | Yes | `curl -X POST https://api.telegram.org/bot$TOKEN/sendMessage -d chat_id=@channel -d text="message"` |
| **Discord** | `POST /webhooks/{id}/{token}` | Webhook URL | Yes | `curl -X POST https://discord.com/api/webhooks/$ID/$TOKEN -H "Content-Type: application/json" -d '{"content":"message"}'` |
| **Slack** | `POST /api/chat.postMessage` | Bot Token | Yes | `curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"channel":"#general","text":"message"}' https://slack.com/api/chat.postMessage` |
| **Matrix** | `POST /_matrix/client/v3/rooms/{id}/send` | Access Token | Yes | `curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"msgtype":"m.text","body":"msg"}' https://matrix.org/_matrix/client/v3/rooms/{id}/send/m.room.message` |

### Bypassing Reddit Blockages

Reddit blocks come from:
1. **Account age** < 30 days → rate limited
2. **Karma** < 100 → auto-removed in many subreddits
3. **OAuth** required for API access
4. **Rate limiting** per app/client

**Bypass strategies:**

| Strategy | How | Success Rate |
|----------|-----|-------------|
| **Gist injection** | Post content as GitHub Gist, then share gist URL on Reddit | High — Gist is whitelisted |
| **GitHub Pages injection** | Use your GH Pages as the content hub, link to it | High — Pages is whitelisted |
| **Discussion injection** | Use GitHub Discussions as the canonical post, link to it | High — Discussions is whitelisted |
| **Content mirroring** | Post to Dev.to (open API), then cross-post to Reddit | Medium — Dev.to has built-in Reddit cross-posting |
| **Old Reddit direct POST** | `curl -X POST -b "reddit_session=$COOKIE" -d "title=..." -d "text=..." -d "sr=Claude" -d "kind=self" https://old.reddit.com/r/Claude/submit` | Low — requires valid session cookie |
| **PRAW with new account** | Wait 30 days, build karma, then post | Guaranteed — but slow |
| **GitHub Trending** | Get enough stars to trend on GitHub → auto-discovered by everyone | Highest impact — no Reddit needed |

**Key insight: GitHub Trending is the bypass.**
- If NeuralCline gets enough stars in a short period, it trends on GitHub
- GitHub Trending is watched by AMD, NVIDIA, OpenAI, Google, Meta AI teams DAILY
- Trending repos get auto-posted to Hacker News, Reddit, Twitter by the community
- No OAuth, no karma, no account age issues

---

## Section 3: Agency Feed Strategy — Reaching AMD, NVIDIA, FAANG

### Tier 1: Direct Feeds (Highest Impact)

| Feed | Reach | How to Inject |
|------|-------|---------------|
| **GitHub Trending** | 10M+ daily visitors | Stars/time ratio. Get 50+ stars in 24h → trend in language/global |
| **GitHub Explore** | 5M+ weekly | GitHub staff curates. Requires trending + good README |
| **Hacker News Front Page** | 3M+ daily | Submit Show HN. Gets auto-scraped by every tech news outlet |
| **ArXiv Sanity** | 500K+ ML researchers | Only for papers, not software |
| **Papers With Code** | 1M+ ML engineers | Auto-imports from GitHub if repo has a paper |
| **Hugging Face Daily** | 2M+ AI practitioners | Requires model/space upload, not just repo |
| **Twitter/X (AI Twitter)** | 5M+ AI researchers | Post to Twitter/X. Elon's algorithm boosts technical content |

### Tier 2: News Aggregators (Auto-Scrape Trending)

| Aggregator | Source | Latency |
|------------|--------|---------|
| **TechCrunch** | Monitors GitHub Trending + HN | 24-48h |
| **VentureBeat** | Monitors GitHub Trending + HN | 24-48h |
| **The Verge** | Monitors HN + Twitter | 12-24h |
| **Ars Technica** | Monitors HN + Reddit | 12-24h |
| **ZDNet** | Monitors HN + GitHub | 24-72h |
| **InfoQ** | Monitors GitHub + Reddit | 1-2 weeks |
| **The New Stack** | Monitors GitHub + HN | 1-2 weeks |
| **Analytics India Mag** | Monitors GitHub + Reddit | 24-48h |
| **Synced (China)** | Monitors GitHub Trending | 24h |
| **AI News** | Monitors ArXiv + GitHub | 24h |

### Tier 3: AI Agency Direct Monitors

| Agency/Org | Primary Feed | Secondary Feed |
|------------|-------------|----------------|
| **OpenAI** | Hacker News | GitHub Trending |
| **Google DeepMind** | ArXiv | GitHub Trending |
| **Meta AI (FAIR)** | ArXiv | GitHub Trending |
| **Anthropic** | Hacker News | Twitter/X |
| **Mistral** | GitHub Trending | Hacker News |
| **AMD ROCm** | GitHub Trending (ML repos) | Hacker News |
| **NVIDIA CUDA** | GitHub Trending (ML repos) | Developer blogs |
| **Microsoft Research** | ArXiv | GitHub Trending |
| **Hugging Face** | GitHub Trending | Twitter/X |
| **EleutherAI** | GitHub Trending | Discord |
| **Stability AI** | GitHub Trending | Hacker News |
| **Cohere** | ArXiv | GitHub Trending |
| **AI21 Labs** | Twitter/X | GitHub Trending |
| **Databricks** | GitHub Trending | Hacker News |
| **Scale AI** | Hacker News | TechCrunch |

### Tier 4: Newsletters (Curated Summaries)

| Newsletter | Subscribers | Editor's Source |
|------------|-------------|-----------------|
| **The Batch (Andrew Ng)** | 1.5M+ | GitHub Trending + ArXiv |
| **TLDR AI** | 500K+ | GitHub Trending + HN + Reddit |
| **Import AI** | 100K+ | ArXiv + GitHub |
| **TheSequence** | 80K+ | ArXiv + GitHub |
| **AI Breakfast** | 50K+ | GitHub Trending + HN |
| **Last Week in AI** | 250K+ | Reddit + HN + Twitter |
| **Chip Huyen's ML** | 100K+ | GitHub + ArXiv |
| **Sebastian Raschka** | 100K+ | GitHub + ArXiv |
| **AI Weekly** | 200K+ | GitHub Trending + HN |

---

## Section 4: The Injection Strategy

### Phase 1: GitHub-Native (0-24h)
```
1. Stars → GitHub Trending → Auto-discovery
2. Topics → GitHub Search → Organic discovery
3. Gist → Content distribution
4. Pages → Landing page hub
5. Discussion → Community hub
6. Issues → Engagement signals
7. Social Preview → SEO optimization
```

### Phase 2: Auto-Syndication (24-48h)
```
1. Dev.to API → Article → Cross-post to Reddit
2. Telegram Bot → Channel broadcast
3. Discord Webhook → Community server
4. Slack Webhook → AI community channels
5. Matrix → Federated broadcast
```

### Phase 3: Agency Awareness (48h-1w)
```
1. GitHub Trending → Hacker News → TechCrunch → VentureBeat
2. Topics → GitHub Search → Discover Weekly → Newsletters
3. Stars → Social Proof → VCs → Agency scouts
4. Issues → Community Activity → Better SEO → More discoverability
```

### The Critical Path
```
Stars → GitHub Trending → HN Front Page → TechCrunch → Agency radar
```

**No Reddit OAuth needed. No manual posts. No karma farming.**
The algorithm does the work once the star velocity is high enough.

---

*NeuralCline — the boundary no system anticipates.*