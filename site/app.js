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
  if (kicked(fx)) {
    const pts = state.points[mid] || {};
    preds = `<div class="preds">` + state.players.map((p) => {
      const v = (state.predictions[mid] || {})[p];
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

function render(tab) {
  document.querySelectorAll("nav button").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  $("#content").innerHTML = { leaderboard: renderLeaderboard, matches: renderMatches, results: renderResults, knockouts: renderKnockouts }[tab]();
}

document.querySelector("nav").addEventListener("click", (e) => e.target.dataset.tab && render(e.target.dataset.tab));
load();
