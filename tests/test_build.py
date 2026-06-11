import json
from scripts.build_leaderboard import build

def test_build_with_movement(tmp_path):
    d = tmp_path
    json.dump(["A", "B"], open(d / "players.json", "w"))
    json.dump([{"number": 1, "stage": "GROUP", "group": "A", "kickoff": "2026-06-11",
                "home": "X", "away": "Y", "api_id": 1}], open(d / "fixtures.json", "w"))
    json.dump({"1": {"A": "2-1", "B": "0-1"}}, open(d / "predictions.json", "w"))
    json.dump({"1": {"home": 2, "away": 1}}, open(d / "results.json", "w"))
    # previous standings had B first
    json.dump([{"player": "B", "rank": 1}, {"player": "A", "rank": 2}], open(d / "leaderboard.json", "w"))
    build(str(d))
    lb = json.load(open(d / "leaderboard.json"))
    assert lb[0]["player"] == "A" and lb[0]["movement"] == 1   # climbed 1
    assert lb[1]["player"] == "B" and lb[1]["movement"] == -1
    pts = json.load(open(d / "points.json"))
    assert pts == {"1": {"A": 3, "B": 0}}
