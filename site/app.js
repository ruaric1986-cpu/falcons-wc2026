// Cloudflare Worker endpoint that saves submitted picks. Replace YOUR-SUBDOMAIN
// with the subdomain from your `wrangler deploy` URL (e.g. falcons-morning-trigger.jsmith.workers.dev).
const SUBMIT_ENDPOINT = "https://falcons-morning-trigger.YOUR-SUBDOMAIN.workers.dev/submit";

const state = {};
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

async function load() {
  const names = ["players", "fixtures", "predictions", "results", "leaderboard", "points"];
  const loaded = await Promise.all(names.map(async (n) => {
    const r = await fetch(`data/${n}.json`, { cache: "no-store" });
    return r.ok ? r.json() : null;
  }));
  names.forEach((n, i) => (state[n] = loaded[i] ?? (n === "fixtures" || n === "leaderboard" ? [] : {})));
  render("leaderboard");
}

function kicked(fx) {
  return fx.kickoff && String(fx.kickoff).includes("T") && new Date(fx.kickoff) < new Date() && fx.home !== "TBD" && fx.away !== "TBD";
}
function ukTime(iso) {
  return new Date(iso).toLocaleString("en-GB", { timeZone: "Europe/London", weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function renderLeaderboard() {
  const rows = state.leaderboard.map((r) => {
    const mv = r.movement > 0 ? `<span class="up">▲${r.movement}</span>` : r.movement < 0 ? `<span class="down">▼${-r.movement}</span>` : "·";
    return `<tr><td>${r.rank}</td><td>${esc(r.player)}</td><td>${mv}</td><td>${r.exact}</td><td>${r.result}</td><td>${r.group_pts}</td><td>${r.knockout_pts}</td><td><strong>${r.total}</strong></td></tr>`;
  }).join("");
  return `<table><tr><th>#</th><th>Player</th><th></th><th>Exact (3)</th><th>Result (1)</th><th>Group</th><th>KO</th><th>Total</th></tr>${rows}</table>`;
}

function matchCard(fx) {
  const mid = String(fx.number);
  const res = state.results[mid];
  const score = res ? `${res.home}-${res.away}` : kicked(fx) ? "in play / awaiting result" : fx.kickoff && String(fx.kickoff).includes("T") ? ukTime(fx.kickoff) : "TBC";
  let preds = "";
  const mp = state.predictions[mid] || {};
  if (Object.keys(mp).length) {
    const pts = state.points[mid] || {};
    preds = `<div class="preds">` + state.players.map((p) => {
      const v = mp[p];
      if (!v) return `<span class="pred">${esc(p)} —</span>`;
      const cls = res ? ` p${pts[p] ?? 0}` : "";
      return `<span class="pred${cls}">${esc(p)} ${esc(v)}</span>`;
    }).join("") + `</div>`;
  }
  const label = fx.stage === "GROUP" ? `Group ${esc(fx.group)} · Match ${fx.number}` : `${esc(fx.stage)} · Match ${fx.number}`;
  return `<div class="match"><div class="meta">${label}</div><h3><span>${esc(fx.home)} v ${esc(fx.away)}</span><span>${score}</span></h3>${preds}</div>`;
}

function renderMatches() {
  const fx = state.fixtures.filter((f) => f.stage === "GROUP");
  const done = fx.filter((f) => state.results[String(f.number)]).sort((a, b) => String(b.kickoff || "").localeCompare(String(a.kickoff || "")));
  const upcoming = fx.filter((f) => !state.results[String(f.number)]).sort((a, b) => String(a.kickoff || "").localeCompare(String(b.kickoff || "")));
  return `<div class="section-title">Upcoming</div>${upcoming.map(matchCard).join("")}<div class="section-title">Played</div>${done.map(matchCard).join("") || "<p class='loading'>None yet</p>"}`;
}

function renderKnockouts() {
  const fx = state.fixtures.filter((f) => f.stage !== "GROUP").sort((a, b) => a.number - b.number);
  return fx.map(matchCard).join("") || "<p class='loading'>Knockout draw not made yet</p>";
}

function renderResults() {
  const played = state.fixtures
    .filter((f) => state.results[String(f.number)])
    .sort((a, b) => String(b.kickoff || "").localeCompare(String(a.kickoff || "")) || b.number - a.number);
  if (!played.length) return "<p class='loading'>No results yet</p>";
  const players = state.players;
  const head = `<tr><th>Match</th><th>Score</th>${players.map((p) => `<th>${esc(p)}</th>`).join("")}</tr>`;
  const rows = played.map((f) => {
    const mid = String(f.number);
    const res = state.results[mid];
    const pts = state.points[mid] || {};
    const cells = players.map((p) => {
      const v = (state.predictions[mid] || {})[p];
      if (!v) return `<td>—</td>`;
      const pt = pts[p] ?? 0;
      return `<td class="p${pt}" title="${pt} pt${pt === 1 ? "" : "s"}">${esc(v)}</td>`;
    }).join("");
    return `<tr><td class="mname">${esc(f.home)} v ${esc(f.away)}</td><td class="score">${res.home}-${res.away}</td>${cells}</tr>`;
  }).join("");
  const totals = players.map((p) => {
    const sum = played.reduce((s, f) => s + ((state.points[String(f.number)] || {})[p] ?? 0), 0);
    return `<td><strong>${sum}</strong></td>`;
  }).join("");
  const totalRow = `<tr class="totals"><td class="mname">Total</td><td></td>${totals}</tr>`;
  const legend = `<p class="legend"><span class="pred p3">exact 3</span><span class="pred p1">result 1</span><span class="pred p0">miss 0</span></p>`;
  return `<div class="grid-wrap"><table class="grid">${head}${rows}${totalRow}</table></div>${legend}`;
}

// Knockout fixtures that are open for entry: drawn (no TBD) and not yet kicked off.
function openKnockouts() {
  return state.fixtures
    .filter((f) => f.stage !== "GROUP" && f.home !== "TBD" && f.away !== "TBD" && f.kickoff && String(f.kickoff).includes("T") && !kicked(f))
    .sort((a, b) => a.number - b.number);
}

function scoreSelect(name) {
  const opts = ['<option value="">–</option>'].concat([...Array(10).keys()].map((n) => `<option value="${n}">${n}</option>`)).join("");
  return `<select class="goals" data-side="${name}">${opts}</select>`;
}

function renderSubmit() {
  if (SUBMIT_ENDPOINT.includes("YOUR-SUBDOMAIN"))
    return `<div class="notice">Score entry isn't wired up yet — the site owner needs to set the Cloudflare Worker address in <code>app.js</code>.</div>`;
  const open = openKnockouts();
  const playerOpts = ['<option value="">— choose your name —</option>'].concat(state.players.map((p) => `<option value="${esc(p)}">${esc(p)}</option>`)).join("");
  const games = open.length
    ? open.map((f) => {
        const mid = String(f.number);
        return `<div class="entry" data-mid="${mid}"><div class="entry-meta">${esc(f.stage)} · ${ukTime(f.kickoff)}</div>
          <div class="entry-row"><span class="team home">${esc(f.home)}</span>${scoreSelect("home")}<span class="dash">–</span>${scoreSelect("away")}<span class="team away">${esc(f.away)}</span></div></div>`;
      }).join("")
    : `<p class="loading">No knockout games are open for entry right now.</p>`;
  return `<div class="submit-wrap">
    <p class="submit-intro">Pick your name, then enter a score for each game. Once you submit a game it's locked — you can't change it, so double-check before sending.</p>
    <label class="player-pick">Your name<br><select id="who">${playerOpts}</select></label>
    <div id="games" class="games-list" hidden>${games}</div>
    <div id="submit-area" hidden><button id="send" disabled>Submit my scores</button><p id="submit-msg" class="submit-msg"></p></div>
  </div>`;
}

function wireSubmit() {
  const who = $("#who"), gamesBox = $("#games"), area = $("#submit-area"), send = $("#send"), msg = $("#submit-msg");
  if (!who) return;

  function paint() {
    const player = who.value;
    gamesBox.hidden = area.hidden = !player;
    if (!player) return;
    let open = 0;
    gamesBox.querySelectorAll(".entry").forEach((el) => {
      const mid = el.dataset.mid;
      const existing = (state.predictions[mid] || {})[player];
      const row = el.querySelector(".entry-row");
      const oldTag = el.querySelector(".locked-tag");
      if (oldTag) oldTag.remove();
      if (existing) {
        el.classList.add("locked");
        row.querySelectorAll("select").forEach((s) => { s.disabled = true; s.value = ""; });
        const [h, a] = existing.split("-");
        const tag = document.createElement("span");
        tag.className = "locked-tag";
        tag.textContent = `submitted: ${h}–${a} ✓`;
        el.appendChild(tag);
      } else {
        el.classList.remove("locked");
        row.querySelectorAll("select").forEach((s) => (s.disabled = false));
        open++;
      }
    });
    refresh();
  }

  function collect() {
    const picks = {};
    gamesBox.querySelectorAll(".entry:not(.locked)").forEach((el) => {
      const h = el.querySelector('[data-side="home"]').value, a = el.querySelector('[data-side="away"]').value;
      if (h !== "" && a !== "") picks[el.dataset.mid] = `${h}-${a}`;
    });
    return picks;
  }

  function refresh() {
    const openCount = gamesBox.querySelectorAll(".entry:not(.locked)").length;
    const filled = Object.keys(collect()).length;
    send.disabled = openCount === 0 || filled !== openCount;
    if (openCount === 0) { msg.textContent = "You've submitted all the open games. 🎉"; msg.className = "submit-msg ok"; }
    else if (!send.disabled) { msg.textContent = ""; }
    else { msg.textContent = `Enter a score for all ${openCount} game${openCount === 1 ? "" : "s"} to submit (${filled}/${openCount} done).`; msg.className = "submit-msg"; }
  }

  who.addEventListener("change", paint);
  gamesBox.addEventListener("change", (e) => { if (e.target.classList.contains("goals")) refresh(); });
  send.addEventListener("click", async () => {
    const player = who.value, picks = collect();
    if (!player || !Object.keys(picks).length) return;
    send.disabled = true; msg.className = "submit-msg"; msg.textContent = "Sending…";
    try {
      const r = await fetch(SUBMIT_ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ player, picks }) });
      const data = await r.json().catch(() => ({}));
      if (r.ok && data.ok) {
        msg.className = "submit-msg ok";
        msg.textContent = "Locked in! ✅ Your scores are saved — they'll show on the site in a minute or two.";
        who.disabled = true;
        gamesBox.querySelectorAll("select").forEach((s) => (s.disabled = true));
      } else {
        msg.className = "submit-msg err";
        msg.textContent = `Couldn't save (${data.error || r.status}). Please try again or send your scores to Ruari.`;
        send.disabled = false;
      }
    } catch {
      msg.className = "submit-msg err";
      msg.textContent = "Network error — please try again, or send your scores to Ruari.";
      send.disabled = false;
    }
  });
}

function render(tab) {
  document.querySelectorAll("nav button").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  $("#content").innerHTML = { leaderboard: renderLeaderboard, matches: renderMatches, results: renderResults, knockouts: renderKnockouts, submit: renderSubmit }[tab]();
  if (tab === "submit") wireSubmit();
}

document.querySelector("nav").addEventListener("click", (e) => e.target.dataset.tab && render(e.target.dataset.tab));
load();
