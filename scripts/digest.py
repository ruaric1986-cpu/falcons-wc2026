import json, os, datetime
from zoneinfo import ZoneInfo

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
UK = ZoneInfo("Europe/London")
SITE_URL = "https://ruaric1986-cpu.github.io/falcons-wc2026/"

def _uk(dt_str):
    return datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(UK)

def compose(fixtures, results, points, leaderboard, reported, today):
    fx_by_num = {str(f["number"]): f for f in fixtures}
    new = [mid for mid in results if mid not in reported and mid in fx_by_num]
    new.sort(key=lambda m: fx_by_num[m]["kickoff"] or "")
    todays = [f for f in fixtures
              if f["kickoff"] and "T" in str(f["kickoff"]) and _uk(f["kickoff"]).date().isoformat() == today
              and str(f["number"]) not in results]
    if not new and not todays:
        return None
    lines = ["⚽ *Falcons WC2026 — Morning Update*", ""]
    if new:
        lines.append("*Results:*")
        for mid in new:
            f, r = fx_by_num[mid], results[mid]
            lines.append(f"{f['home']} {r['home']}-{r['away']} {f['away']}")
            exact = sorted(p for p, v in points.get(mid, {}).items() if v == 3)
            if exact:
                lines.append(f"  🎯 Exact: {', '.join(exact)}")
        lines.append("")
        lines.append("*Leaderboard:*")
        for r in leaderboard[:5]:
            arrow = f" ⬆{r['movement']}" if r["movement"] > 0 else (f" ⬇{-r['movement']}" if r["movement"] < 0 else "")
            lines.append(f"{r['rank']}. {r['player']} — {r['total']}{arrow}")
        climbers = [r for r in leaderboard[5:] if r["movement"] >= 3]
        for r in climbers[:2]:
            lines.append(f"📈 {r['player']} up {r['movement']} to {r['rank']}")
        lines.append("")
    if todays:
        lines.append("*Today:*")
        for f in todays:
            lines.append(f"{_uk(f['kickoff']).strftime('%H:%M')} {f['home']} v {f['away']}")
    lines += ["", f"📊 Full table: {SITE_URL}"]
    return "\n".join(lines).strip()

def main():
    def load(name, default):
        path = os.path.join(DATA, name)
        if not os.path.exists(path):
            return default
        with open(path) as fh:
            return json.load(fh)
    state = load("digest_state.json", {"reported": []})
    results = load("results.json", {})
    today = datetime.datetime.now(UK).date().isoformat()
    if state.get("last_sent") == today and not os.environ.get("DRY_RUN") and not os.environ.get("FORCE_SEND"):
        print(f"Morning update already sent today ({today}); skipping to avoid a duplicate.")
        return
    msg = compose(load("fixtures.json", []), results, load("points.json", {}),
                  load("leaderboard.json", []), state.get("reported", []), today)
    if msg is None:
        print("Nothing to send today.")
        return
    from scripts.send_whatsapp import send
    send(msg)
    if os.environ.get("DRY_RUN"):
        return  # don't advance state on a dry run, or the real send would skip these
    state["reported"] = sorted(set(state.get("reported", [])) | set(results))
    state["last_sent"] = today  # the workflow gate reads this to fire the morning send once per day
    with open(os.path.join(DATA, "digest_state.json"), "w") as fh:
        json.dump(state, fh, indent=1)

if __name__ == "__main__":
    main()
