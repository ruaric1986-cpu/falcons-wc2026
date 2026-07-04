# Cloudflare Worker (reliable 07:30 send + on-site score entry)

A tiny Cloudflare Worker with two jobs:

1. **Morning trigger** — fires every morning and triggers the GitHub **Daily
   update** workflow via its API, replacing GitHub's unreliable scheduled cron.
2. **`POST /submit`** — receives knockout score predictions from the website's
   *Enter Scores* tab and fires the **Submit predictions** workflow, which
   validates and merges them into the repo and redeploys the site. The site is
   a static GitHub Pages site with no backend, so this endpoint is what lets the
   on-page score form actually save.

Everything else (results fetch, leaderboard, WhatsApp digest, site deploy) still
runs in GitHub Actions unchanged.

## Making on-site score entry live

The score form and the `/submit` endpoint are already in the code. Two things
turn it on:

1. **Redeploy the Worker** with the current `worker.js` (paste it into the
   Cloudflare dashboard editor, or run `wrangler deploy` from this directory).
   No token change is needed — the existing `GH_TOKEN` (Actions: read/write)
   already covers dispatching the new workflow.
2. **Point the site at the Worker.** In `site/app.js`, set `SUBMIT_ENDPOINT` to
   your Worker URL with `/submit` on the end, e.g.
   `https://falcons-morning-trigger.<your-subdomain>.workers.dev/submit`
   (replace `YOUR-SUBDOMAIN`). Commit that one-line change.

Optional: set a `SUBMIT_KEY` secret on the Worker (`wrangler secret put
SUBMIT_KEY`) to keep random bots off the endpoint. If you do, add the same value
to the site's POST body. It's not strong security (it's visible in the page
source) — the real integrity guard is server-side in the workflow, which refuses
to change a pick a player has already made and rejects any game that has kicked
off.

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
