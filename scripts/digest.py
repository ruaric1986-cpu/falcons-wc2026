import json, os, datetime
from zoneinfo import ZoneInfo

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
UK = ZoneInfo("Europe/London")
SITE_URL = "https://ruaric1986-cpu.github.io/falcons-wc2026/"

# Inside joke: Karim's name is "accidentally" mangled in every morning update, drifting
# one step further from reality each match-day and ending up as plain "Steve" for the
# final. Date-driven: one entry per match-day from now to the final, indexed by
# match-days remaining, so the final update always lands on "Steve" (and rest days get
# no update, hence no step, since the digest only sends on match days).
KARIM_DRIFT = [
    "Kareem", "Kareen", "Karen", "Karon", "Kaden", "Kaiden", "Kayden", "Hayden",
    "Aidan", "Aiden", "Aaron", "Darren", "Damian", "Damon", "Devon", "Devin",
    "Steven", "Steve",
]

def _fixture_date(kickoff):
    return _uk(kickoff).date() if kickoff and "T" in str(kickoff) else None

def karim_drift_name(fixtures, today_iso):
    """Today's drift name, indexed by match-days remaining to the final so the final
    match-day resolves to 'Steve' and earlier days walk back through the list."""
    today = datetime.date.fromisoformat(today_iso)
    days = sorted({d for d in (_fixture_date(f.get("kickoff")) for f in fixtures) if d})
    if not days:
        return KARIM_DRIFT[0]
    remaining = sum(1 for d in days if today <= d <= days[-1])
    idx = len(KARIM_DRIFT) - remaining
    return KARIM_DRIFT[max(0, min(idx, len(KARIM_DRIFT) - 1))]

def apply_karim(text, name):
    """Swap every 'Karim' for the given drift name. Returns (text, used)."""
    if "Karim" not in text:
        return text, False
    return text.replace("Karim", name), True


def _uk(dt_str):
    return datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(UK)

def _ordinal(n):
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"

def _karim_mover(leaderboard):
    """A plain movers-style line for Karim (no commentary), shown whether he moved or not."""
    e = next((r for r in leaderboard if r["player"] == "Karim"), None)
    if e is None:
        return None
    m, rank = e["movement"], e["rank"]
    if m > 0:
        return f"📈 Karim up {m} to {rank}"
    if m < 0:
        return f"📉 Karim down {-m} to {rank}"
    return f"➡️ Karim {_ordinal(rank)}"

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
        # Always feature Karim in the movers section (unless he's already shown above)
        if not any(r["player"] == "Karim" for r in leaderboard[:5] + climbers[:2]):
            km = _karim_mover(leaderboard)
            if km:
                lines.append(km)
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
    fixtures = load("fixtures.json", [])
    msg = compose(fixtures, results, load("points.json", {}),
                  load("leaderboard.json", []), state.get("reported", []), today)
    if msg is None:
        print("Nothing to send today.")
        return
    msg, _ = apply_karim(msg, karim_drift_name(fixtures, today))
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
