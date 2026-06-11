import json, os
from scripts.score import build_leaderboard, points

DATA = os.path.join(os.path.dirname(__file__), "..", "data")

def build(data_dir=DATA):
    def load(name):
        with open(os.path.join(data_dir, name)) as fh:
            return json.load(fh)
    players, fixtures = load("players.json"), load("fixtures.json")
    predictions, results = load("predictions.json"), load("results.json")
    prev = {}
    lb_path = os.path.join(data_dir, "leaderboard.json")
    if os.path.exists(lb_path):
        with open(lb_path) as fh:
            prev = {r["player"]: r["rank"] for r in json.load(fh)}
    lb = build_leaderboard(players, fixtures, predictions, results)
    for r in lb:
        r["movement"] = (prev.get(r["player"], r["rank"])) - r["rank"]
    with open(lb_path, "w") as fh:
        json.dump(lb, fh, indent=1)
    match_pts = {mid: {p: points(predictions.get(mid, {}).get(p), (res["home"], res["away"]))
                       for p in players}
                 for mid, res in results.items()
                 if res.get("home") is not None and res.get("away") is not None}
    with open(os.path.join(data_dir, "points.json"), "w") as fh:
        json.dump(match_pts, fh, indent=1)
    top = ", ".join(f"{r['rank']}. {r['player']} {r['total']}" for r in lb[:3])
    print(f"Leaderboard: {top}")

if __name__ == "__main__":
    build()
