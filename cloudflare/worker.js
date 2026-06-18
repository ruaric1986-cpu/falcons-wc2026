// Cloudflare Worker: reliably triggers the GitHub "Daily update" workflow at 07:30 UK.
//
// GitHub's own scheduled cron is unreliable (often hours late). Cloudflare Cron
// Triggers are dependable, so this Worker fires in the morning and calls the
// workflow via the GitHub API. All the real work (fetch results, build leaderboard,
// compose + send the WhatsApp digest, deploy the site) still runs in GitHub Actions.
//
// The cron fires at 06:30 and 07:30 UTC; only the tick that is 07:30 in London
// actually dispatches (07:30 BST = 06:30 UTC; 07:30 GMT = 07:30 UTC), so it lands at
// 07:30 UK year-round. The workflow also guards against duplicate sends per day.

const DISPATCH_URL =
  "https://api.github.com/repos/ruaric1986-cpu/falcons-wc2026/actions/workflows/daily.yml/dispatches";

async function dispatch(env) {
  const res = await fetch(DISPATCH_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "falcons-morning-trigger",
    },
    body: JSON.stringify({ ref: "main" }),
  });
  console.log("dispatch ->", res.status, await res.text());
  return res;
}

function londonHour(d = new Date()) {
  return Number(
    new Intl.DateTimeFormat("en-GB", {
      timeZone: "Europe/London",
      hour: "2-digit",
      hour12: false,
    }).format(d)
  );
}

export default {
  async scheduled(event, env, ctx) {
    if (londonHour() === 7) {
      ctx.waitUntil(dispatch(env));
    } else {
      console.log("Not the 07:00 London hour; skipping. London hour =", londonHour());
    }
  },

  // Manual test: GET https://<worker-url>/?key=YOUR_TRIGGER_KEY  -> dispatches the workflow now.
  async fetch(req, env) {
    const url = new URL(req.url);
    if (env.TRIGGER_KEY && url.searchParams.get("key") === env.TRIGGER_KEY) {
      const r = await dispatch(env);
      return new Response(`dispatched: HTTP ${r.status}\n`);
    }
    return new Response("Falcons morning trigger is alive. Append ?key=... to dispatch.\n");
  },
};
