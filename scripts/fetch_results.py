"""Fetch World Cup matches from football-data.org and update data/results.json + fixtures.json.
Env: FOOTBALL_DATA_TOKEN (required when run as a script).
"""
import json, os, re, sys, time
import unicodedata

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
API_URL = "https://api.football-data.org/v4/competitions/WC/matches"

ALIASES = {  # sheet name -> API name (normalised); extend as real API names appear
    "south korea": "korea republic",
    "ivory coast": "cote divoire",
    "usa": "united states",
    "iran": "ir iran",
    # names confirmed against live football-data.org API 2026-06-11
    "bosnia and herzegovina": "bosniaherzegovina",
    "turkiye": "turkey",
    "cape verde": "cape verde islands",
    "dr congo": "congo dr",
}
STAGE_ORDER = ["LAST_32", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "THIRD_PLACE", "FINAL"]
SHEET_STAGE_TO_API = {"R32": "LAST_32", "R16": "LAST_16", "QF": "QUARTER_FINALS",
                      "SF": "SEMI_FINALS", "3RD": "THIRD_PLACE", "FINAL": "FINAL"}

def norm(name):
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z ]", "", s.lower()).strip()
    return ALIASES.get(s, s)

def _ninety_minute_score(m):
    score = m["score"]
    if score.get("duration") == "REGULAR":
        ft = score["fullTime"]
        return {"home": ft["home"], "away": ft["away"]}
    rt = score.get("regularTime")
    if not rt or rt.get("home") is None:
        # regularTime missing or null — return null and let the caller skip
        return {"home": None, "away": None}
    return {"home": rt["home"], "away": rt["away"]}

def map_and_extract(api_matches, fixtures, prior=None):
    prior = prior or {}
    by_api_id = {f["api_id"]: f for f in fixtures if f.get("api_id")}
    group_fx = [f for f in fixtures if f["stage"] == "GROUP" and not f.get("api_id")]
    unmatched = []

    for m in api_matches:
        if m["id"] in by_api_id:
            continue
        if m["stage"] == "GROUP_STAGE":
            ah, aa = norm(m["homeTeam"]["name"]), norm(m["awayTeam"]["name"])
            cands = [f for f in group_fx
                     if {norm(f["home"]), norm(f["away"])} == {ah, aa}
                     and (not m.get("group") or not f.get("group") or m["group"].endswith(f["group"]))]
            if len(cands) == 1:
                cands[0]["api_id"] = m["id"]
                by_api_id[m["id"]] = cands[0]
            else:
                unmatched.append(f"{m['id']} {m['homeTeam']['name']} v {m['awayTeam']['name']}")

    # knockouts: assign per stage so a later-stage API match cannot land in an earlier-stage slot
    for api_stage in STAGE_ORDER:
        ms = sorted([m for m in api_matches if m["stage"] == api_stage and m["id"] not in by_api_id],
                    key=lambda m: (m["utcDate"], m["id"]))
        slots = sorted([f for f in fixtures if f["stage"] != "GROUP" and not f.get("api_id")
                        and SHEET_STAGE_TO_API.get(f["stage"]) == api_stage],
                       key=lambda f: f["number"])
        for m, slot in zip(ms, slots):
            slot["api_id"] = m["id"]
            by_api_id[m["id"]] = slot
    unmatched += [f"{m['id']} stage {m['stage']}" for m in api_matches
                  if m["stage"] != "GROUP_STAGE" and m["stage"] not in STAGE_ORDER and m["id"] not in by_api_id]

    results = {}
    for m in api_matches:
        fx = by_api_id.get(m["id"])
        if not fx:
            continue
        if m["stage"] != "GROUP_STAGE":   # refresh KO teams/kickoff as draws/dates firm up
            for side, key in (("home", "homeTeam"), ("away", "awayTeam")):
                if m[key].get("name"):
                    fx[side] = m[key]["name"]
            fx["kickoff"] = m["utcDate"]
        elif m["utcDate"]:
            fx["kickoff"] = m["utcDate"]
        if m["status"] == "FINISHED":
            score = _ninety_minute_score(m)
            if score["home"] is None or score["away"] is None:
                kept = prior.get(str(fx["number"]))
                if kept:
                    print(f"match {fx['number']}: FINISHED but score not yet available "
                          f"— retaining previously stored {kept['home']}-{kept['away']}")
                    results[str(fx["number"])] = kept
                else:
                    print(f"match {fx['number']}: FINISHED but score not yet available — skipping")
                continue
            if m["stage"] == "GROUP_STAGE" and norm(fx["home"]) != norm(m["homeTeam"]["name"]):
                score = {"home": score["away"], "away": score["home"]}
            results[str(fx["number"])] = score
    return results, unmatched

def main():
    import requests
    token = os.environ["FOOTBALL_DATA_TOKEN"]
    resp = None
    for attempt in range(3):
        try:
            resp = requests.get(API_URL, headers={"X-Auth-Token": token}, timeout=30)
            if resp.status_code == 200:
                break
            print(f"API attempt {attempt + 1} failed: HTTP {resp.status_code}", file=sys.stderr)
        except requests.exceptions.RequestException as e:
            print(f"API attempt {attempt + 1} failed: {e}", file=sys.stderr)
            resp = None
        if attempt < 2:
            time.sleep(15 * (attempt + 1))
    if resp is None or resp.status_code != 200:
        sys.exit("API failed after 3 attempts")
    payload = resp.json()
    api_matches = payload["matches"]
    expected = payload.get("resultSet", {}).get("count")
    if expected is not None and len(api_matches) < expected:
        sys.exit(f"Partial API response: got {len(api_matches)} of {expected} matches")
    with open(os.path.join(DATA, "fixtures.json")) as fh:
        fixtures = json.load(fh)
    results_path = os.path.join(DATA, "results.json")
    prior = {}
    if os.path.exists(results_path):
        with open(results_path) as fh:
            prior = json.load(fh)
    results, unmatched = map_and_extract(api_matches, fixtures, prior)
    if unmatched:
        sys.exit("UNMATCHED API MATCHES (add to ALIASES): " + "; ".join(unmatched))
    with open(os.path.join(DATA, "fixtures.json"), "w") as fh:
        json.dump(fixtures, fh, indent=1)
    with open(results_path, "w") as fh:
        json.dump(results, fh, indent=1)
    print(f"{len(results)} finished matches")

if __name__ == "__main__":
    main()
