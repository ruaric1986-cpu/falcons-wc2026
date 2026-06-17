import json, os
import scripts.digest as digest
from scripts.digest import compose

FIXTURES = [
    {"number": 1, "stage": "GROUP", "group": "A", "kickoff": "2026-06-11T19:00:00Z", "home": "Mexico", "away": "South Africa", "api_id": 1},
    {"number": 2, "stage": "GROUP", "group": "A", "kickoff": "2026-06-12T16:00:00Z", "home": "Czechia", "away": "South Korea", "api_id": 2},
]
LB = [
    {"player": "Ruari", "total": 3, "exact": 1, "result": 0, "rank": 1, "movement": 2, "group_pts": 3, "knockout_pts": 0},
    {"player": "Dave F", "total": 1, "exact": 0, "result": 1, "rank": 2, "movement": -1, "group_pts": 1, "knockout_pts": 0},
]

def test_compose_full_digest():
    msg = compose(fixtures=FIXTURES, results={"1": {"home": 2, "away": 1}},
                  points={"1": {"Ruari": 3, "Dave F": 1}}, leaderboard=LB,
                  reported=[], today="2026-06-12")
    assert "Mexico 2-1 South Africa" in msg
    assert "Ruari" in msg and "🎯" in msg            # exact-score callout
    assert "1. Ruari — 3" in msg                      # leaderboard line
    assert "⬆2" in msg                                # movement
    assert "Czechia v South Korea" in msg             # today's fixture
    assert "17:00" in msg                             # 16:00 UTC -> 17:00 UK (BST)
    assert digest.SITE_URL in msg                     # link to the table on the site

def test_compose_skips_when_nothing_to_say():
    msg = compose(fixtures=FIXTURES, results={"1": {"home": 2, "away": 1}},
                  points={"1": {}}, leaderboard=LB,
                  reported=["1"], today="2026-07-01")  # result already reported, no games today
    assert msg is None

def test_dry_run_does_not_advance_reported_state(tmp_path, monkeypatch):
    monkeypatch.setattr(digest, "DATA", str(tmp_path))
    monkeypatch.setenv("DRY_RUN", "1")
    (tmp_path / "fixtures.json").write_text(json.dumps(FIXTURES))
    (tmp_path / "results.json").write_text(json.dumps({"1": {"home": 2, "away": 1}}))
    (tmp_path / "points.json").write_text(json.dumps({"1": {"Ruari": 3}}))
    (tmp_path / "leaderboard.json").write_text(json.dumps(LB))
    (tmp_path / "digest_state.json").write_text(json.dumps({"reported": []}))
    digest.main()
    # state must be untouched so the real send still reports these results
    assert json.loads((tmp_path / "digest_state.json").read_text()) == {"reported": []}

def test_real_send_records_last_sent(tmp_path, monkeypatch):
    import datetime
    from zoneinfo import ZoneInfo
    import scripts.send_whatsapp as sw
    monkeypatch.setattr(sw, "send", lambda msg: None)        # don't actually POST
    monkeypatch.setattr(digest, "DATA", str(tmp_path))
    monkeypatch.delenv("DRY_RUN", raising=False)
    (tmp_path / "fixtures.json").write_text(json.dumps(FIXTURES))
    (tmp_path / "results.json").write_text(json.dumps({"1": {"home": 2, "away": 1}}))
    (tmp_path / "points.json").write_text(json.dumps({"1": {"Ruari": 3}}))
    (tmp_path / "leaderboard.json").write_text(json.dumps(LB))
    (tmp_path / "digest_state.json").write_text(json.dumps({"reported": []}))
    digest.main()
    state = json.loads((tmp_path / "digest_state.json").read_text())
    today = datetime.datetime.now(ZoneInfo("Europe/London")).date().isoformat()
    assert state["reported"] == ["1"]      # result recorded
    assert state["last_sent"] == today     # morning-send marker the gate uses
