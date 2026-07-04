"""Merge a player's knockout score predictions submitted from the website.

Invoked by the `Submit predictions` GitHub workflow, which is fired by the
Cloudflare Worker when a player submits on the site. Reads the submission from
env vars PLAYER and PICKS (PICKS is a JSON object of match-number -> "H-A"), and
merges accepted picks into data/predictions.json.

Integrity rules enforced here (client-side UI is just a convenience, this is the
real guard):
  * player must be a known player
  * score must look like "<int>-<int>"
  * the fixture must exist and not be a placeholder (no "TBD" sides)
  * kickoff must not have passed (deadline)
  * a pick a player has ALREADY made is locked and cannot be amended
Anything that fails a rule is skipped and reported; the rest are saved.
"""
import json, os, re, datetime
from zoneinfo import ZoneInfo

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
UK = ZoneInfo("Europe/London")
SCORE_RE = re.compile(r"^\s*(\d{1,2})\s*-\s*(\d{1,2})\s*$")


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def merge(player, picks, players, fixtures, predictions, now=None):
    """Return (updated_predictions, accepted, rejected). Pure — no I/O."""
    now = now or _now()
    fx_by_num = {str(f["number"]): f for f in fixtures}
    accepted, rejected = {}, {}
    if player not in players:
        return predictions, {}, {"_player": f"unknown player {player!r}"}
    for mid, raw in picks.items():
        mid = str(mid)
        f = fx_by_num.get(mid)
        if not f:
            rejected[mid] = "no such fixture"
            continue
        if f.get("home") == "TBD" or f.get("away") == "TBD":
            rejected[mid] = "fixture not drawn yet"
            continue
        ko = f.get("kickoff")
        if ko and "T" in str(ko):
            kickoff = datetime.datetime.fromisoformat(str(ko).replace("Z", "+00:00"))
            if now >= kickoff:
                rejected[mid] = "kicked off (deadline passed)"
                continue
        if predictions.get(mid, {}).get(player):
            rejected[mid] = "already submitted (locked)"
            continue
        m = SCORE_RE.match(str(raw))
        if not m:
            rejected[mid] = f"bad score {raw!r}"
            continue
        score = f"{int(m.group(1))}-{int(m.group(2))}"
        predictions.setdefault(mid, {})[player] = score
        accepted[mid] = score
    return predictions, accepted, rejected


def main():
    player = (os.environ.get("PLAYER") or "").strip()
    try:
        picks = json.loads(os.environ.get("PICKS") or "{}")
    except json.JSONDecodeError:
        picks = {}
    if not isinstance(picks, dict):
        picks = {}

    def load(name):
        with open(os.path.join(DATA, name)) as fh:
            return json.load(fh)

    players, fixtures, predictions = load("players.json"), load("fixtures.json"), load("predictions.json")
    predictions, accepted, rejected = merge(player, picks, players, fixtures, predictions)
    if accepted:
        with open(os.path.join(DATA, "predictions.json"), "w") as fh:
            json.dump(predictions, fh, indent=1)
    print(f"player={player!r} accepted={accepted} rejected={rejected}")
    # Signal to the workflow whether anything changed (so it can skip an empty commit).
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as fh:
            fh.write(f"changed={'1' if accepted else ''}\n")


if __name__ == "__main__":
    main()
