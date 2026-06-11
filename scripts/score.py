import re

SCORE_RE = re.compile(r"^\s*(\d{1,2})\s*-\s*(\d{1,2})\s*$")

def parse_score(s):
    if not s or not isinstance(s, str):
        return None
    s = s.replace("–", "-").replace("—", "-")
    m = SCORE_RE.match(s)
    return (int(m.group(1)), int(m.group(2))) if m else None

def _outcome(h, a):
    return "H" if h > a else ("A" if h < a else "D")

def points(prediction, result):
    pred = parse_score(prediction)
    if pred is None:
        return 0
    if pred == tuple(result):
        return 3
    return 1 if _outcome(*pred) == _outcome(*result) else 0

def build_leaderboard(players, fixtures, predictions, results):
    rows = []
    for player in players:
        total = exact = result_only = group_pts = knockout_pts = 0
        for fx in fixtures:
            mid = str(fx["number"])
            rec = results.get(mid) or {}
            if rec.get("home") is None or rec.get("away") is None:
                continue
            res = (rec["home"], rec["away"])
            pts = points(predictions.get(mid, {}).get(player), res)
            total += pts
            exact += pts == 3
            result_only += pts == 1
            if fx["stage"] == "GROUP":
                group_pts += pts
            else:
                knockout_pts += pts
        rows.append({"player": player, "total": total, "exact": exact, "result": result_only,
                     "group_pts": group_pts, "knockout_pts": knockout_pts})
    rows.sort(key=lambda r: (-r["total"], -r["exact"], -r["result"], r["player"].lower()))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows
