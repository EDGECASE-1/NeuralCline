const puppeteer = require('puppeteer');
const args = process.argv.slice(2);
const action = args[0];

async function postToGitHub(body, repo, title, type) {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  const token = process.env.GH_TOKEN || process.env.GITHUB_TOKEN;
  if (!token) {
    console.log(JSON.stringify({ error: 'No GitHub token found. Set GH_TOKEN env var.' }));
    await browser.close();
    process.exit(1);
  }
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

async function postToReddit(body, subreddit, title) {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  const username = process.env.REDDIT_USER;
  const password = process.env.REDDIT_PASS;
  const clientId = process.env.REDDIT_CLIENT_ID;
  const clientSecret = process.env.REDDIT_CLIENT_SECRET;
  const userAgent = 'NeuralCline-Poster/1.0';
  if (!username || !password || !clientId || !clientSecret) {
    console.log(JSON.stringify({ error: 'Reddit creds not set. Need REDDIT_USER, REDDIT_PASS, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET' }));
    await browser.close();
    process.exit(1);
  }
  // Get access token
  const authRes = await fetch('https://www.reddit.com/api/v1/access_token', {
    method: 'POST',
    headers: {
      'Authorization': 'Basic ' + Buffer.from(clientId + ':' + clientSecret).toString('base64'),
      'Content-Type': 'application/x-www-form-urlencoded',
      'User-Agent': userAgent
    },
    body: 'grant_type=password&username=' + encodeURIComponent(username) + '&password=' + encodeURIComponent(password)
  });
  const authData = await authRes.json();
  const token = authData.access_token;
  if (!token) {
    console.log(JSON.stringify({ error: 'Reddit auth failed', data: authData }));
    await browser.close();
    process.exit(1);
  }
  // Submit post
  const postRes = await fetch(`https://oauth.reddit.com/r/${subreddit}/submit`, {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer ' + token,
      'Content-Type': 'application/x-www-form-urlencoded',
      'User-Agent': userAgent
    },
    body: 'kind=self&sr=' + subreddit + '&title=' + encodeURIComponent(title) + '&text=' + encodeURIComponent(body)
  });
  const postData = await postRes.json();
  console.log(JSON.stringify({ status: postRes.status, data: postData }));
  await browser.close();
}

async function postToTwitter(body) {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  const apiKey = process.env.TWITTER_API_KEY;
  const apiSecret = process.env.TWITTER_API_SECRET;
  const accessToken = process.env.TWITTER_ACCESS_TOKEN;
  const accessSecret = process.env.TWITTER_ACCESS_SECRET;
  if (!apiKey || !apiSecret || !accessToken || !accessSecret) {
    console.log(JSON.stringify({ error: 'Twitter creds not set. Need TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET' }));
    await browser.close();
    process.exit(1);
  }
  // Use Twitter API v2 via OAuth 1.0a
  const OAuth = require('oauth-1.0a');
  const crypto = require('crypto');
  const oauth = OAuth({ consumer: { key: apiKey, secret: apiSecret }, signature_method: 'HMAC-SHA1', hash_function(base_string, key) { return crypto.createHmac('sha1', key).update(base_string).digest('base64'); } });
  const token = { key: accessToken, secret: accessSecret };
  const requestData = { url: 'https://api.twitter.com/2/tweets', method: 'POST' };
  const headers = oauth.toHeader(oauth.authorize(requestData, token));
  const response = await fetch('https://api.twitter.com/2/tweets', {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json', 'User-Agent': 'NeuralCline-Poster/1.0' },
    body: JSON.stringify({ text: body })
  });
  const result = await response.json();
  console.log(JSON.stringify({ status: response.status, data: result }));
  await browser.close();
}

async function postToDiscord(body, webhookUrl) {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  const url = webhookUrl || process.env.DISCORD_WEBHOOK;
  if (!url) {
    console.log(JSON.stringify({ error: 'Discord webhook not set. Pass URL or set DISCORD_WEBHOOK env var.' }));
    await browser.close();
    process.exit(1);
  }
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'User-Agent': 'NeuralCline-Poster/1.0' },
    body: JSON.stringify({ content: body })
  });
  console.log(JSON.stringify({ status: response.status }));
  await browser.close();
}

async function status() {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  await page.goto('https://httpbin.org/get', { waitUntil: 'networkidle2' });
  const body = await page.evaluate(() => document.body.innerText);
  console.log(JSON.stringify({ status: 'ok', browser: 'chromium', mode: 'headless', test: body.substring(0, 60) }));
  await browser.close();
}

(async () => {
  try {
    if (action === 'github-issue') {
      const body = args[1] || '';
      const repo = args.find((a,i) => a === '--repo' ? args[i+1] : null) || 'EDGECASE-1/NeuralCline';
      const title = args.find((a,i) => a === '--title' ? args[i+1] : null) || 'NeuralCline Update';
      await postToGitHub(body, repo, title, 'issue');
    } else if (action === 'reddit') {
      const body = args[1] || '';
      const subreddit = args.find((a,i) => a === '--subreddit' ? args[i+1] : null) || 'artificial';
      const title = args.find((a,i) => a === '--title' ? args[i+1] : null) || 'NeuralCline Update';
      await postToReddit(body, subreddit, title);
    } else if (action === 'twitter') {
      const body = args[1] || '';
      await postToTwitter(body);
    } else if (action === 'discord') {
      const body = args[1] || '';
      const webhook = args.find((a,i) => a === '--webhook' ? args[i+1] : null);
      await postToDiscord(body, webhook);
    } else if (action === 'status') {
      await status();
    } else {
      console.log(JSON.stringify({ error: 'Unknown action', usage: 'github-issue|reddit|twitter|discord|status' }));
      process.exit(1);
    }
  } catch(e) {
    console.log(JSON.stringify({ error: e.message }));
    process.exit(1);
  }
})();