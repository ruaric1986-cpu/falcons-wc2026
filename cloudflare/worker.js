// Cloudflare Worker for the Falcons WC2026 predictor. Two jobs:
//
//   1. Cron: reliably trigger the GitHub "Daily update" workflow at 07:30 UK.
//      GitHub's own scheduled cron is unreliable (often hours late), so this
//      Worker fires in the morning and calls the workflow via the GitHub API.
//
//   2. POST /submit: accept a player's knockout score predictions from the
//      website and fire the "Submit predictions" workflow, which validates and
//      merges them into the repo and redeploys the site. The site is a static
//      GitHub Pages site with no backend of its own, so this Worker is what
//      lets the "enter scores on the page" form actually save.
//
// All the real work still runs in GitHub Actions.

const REPO = "ruaric1986-cpu/falcons-wc2026";
const DAILY_URL = `https://api.github.com/repos/${REPO}/actions/workflows/daily.yml/dispatches`;
const SUBMIT_URL = `https://api.github.com/repos/${REPO}/actions/workflows/submit.yml/dispatches`;

async function ghDispatch(url, env, inputs) {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "falcons-worker",
    },
    body: JSON.stringify(inputs ? { ref: "main", inputs } : { ref: "main" }),
  });
  console.log("dispatch ->", url, res.status, await res.text());
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

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...CORS },
  });
}

// Validate + normalise the submission before spending a workflow run on it.
// The GitHub workflow re-checks everything server-side (lock, deadline, etc.);
// this is just a cheap first filter and shape check.
function cleanPicks(picks) {
  const out = {};
  if (picks && typeof picks === "object") {
    for (const [k, v] of Object.entries(picks)) {
      const m = /^\s*(\d{1,2})\s*-\s*(\d{1,2})\s*$/.exec(String(v));
      if (/^\d+$/.test(String(k)) && m) out[k] = `${+m[1]}-${+m[2]}`;
    }
  }
  return out;
}

async function handleSubmit(req, env) {
  // Optional shared key: if SUBMIT_KEY is set, the site must send it. Keeps
  // random bots off the endpoint (the per-fixture lock is the real integrity guard).
  let body;
  try {
    body = await req.json();
  } catch {
    return json({ ok: false, error: "invalid JSON" }, 400);
  }
  if (env.SUBMIT_KEY && body.key !== env.SUBMIT_KEY) {
    return json({ ok: false, error: "unauthorised" }, 401);
  }
  const player = String(body.player || "").trim();
  const picks = cleanPicks(body.picks);
  if (!player) return json({ ok: false, error: "no player" }, 400);
  if (!Object.keys(picks).length) return json({ ok: false, error: "no valid scores" }, 400);
  const r = await ghDispatch(SUBMIT_URL, env, { player, picks: JSON.stringify(picks) });
  if (r.status === 204) return json({ ok: true, count: Object.keys(picks).length });
  return json({ ok: false, error: `github ${r.status}` }, 502);
}

export default {
  async scheduled(event, env, ctx) {
    if (londonHour() === 7) {
      ctx.waitUntil(ghDispatch(DAILY_URL, env));
    } else {
      console.log("Not the 07:00 London hour; skipping. London hour =", londonHour());
    }
  },

  async fetch(req, env) {
    const url = new URL(req.url);
    if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (url.pathname === "/submit" && req.method === "POST") return handleSubmit(req, env);
    // Manual test: GET /?key=YOUR_TRIGGER_KEY -> dispatches the daily workflow now.
    if (env.TRIGGER_KEY && url.searchParams.get("key") === env.TRIGGER_KEY) {
      const r = await ghDispatch(DAILY_URL, env);
      return new Response(`dispatched: HTTP ${r.status}\n`, { headers: CORS });
    }
    return new Response("Falcons worker is alive. POST /submit to send picks.\n", { headers: CORS });
  },
};
