# Cloudflare cron trigger (reliable 07:30 UK send)

A tiny Cloudflare Worker that fires every morning and triggers the GitHub
**Daily update** workflow via its API. This replaces GitHub's unreliable
scheduled cron; everything else (results fetch, leaderboard, WhatsApp digest,
site deploy) still runs in GitHub Actions unchanged.

## One-time setup

### 1. GitHub token
- GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate new token
- Repository access: **Only** `ruaric1986-cpu/falcons-wc2026`
- Permissions → Repository → **Actions: Read and write**
- Copy the token (`github_pat_…`)

### 2. Deploy the Worker
From this `cloudflare/` directory:

```sh
npm install -g wrangler        # or use: npx wrangler ...
wrangler login                 # opens your Cloudflare account in the browser
wrangler secret put GH_TOKEN   # paste the github_pat_… token
wrangler secret put TRIGGER_KEY  # optional: paste any random string (for manual test)
wrangler deploy
```

That's it — the Worker now fires the morning send at **07:30 UK** every day,
reliably.

### 3. Test it (optional)
If you set `TRIGGER_KEY`, visit (replacing the URL with the one `wrangler deploy`
printed, and the key you chose):

```
https://falcons-morning-trigger.<your-subdomain>.workers.dev/?key=YOUR_TRIGGER_KEY
```

It dispatches the workflow immediately. Check the repo's **Actions** tab for the
run. (The workflow still sends only once per day, so if it already went out, the
test run will no-op — that's expected.)

## Notes
- GitHub's own schedule is left in place as a harmless backstop; the workflow's
  once-per-day guard means you'll never get a duplicate even if both fire.
- To change the time, edit `crons` in `wrangler.toml` and the `londonHour() === 7`
  check in `worker.js`, then `wrangler deploy` again.
