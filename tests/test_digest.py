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

def test_karim_watch_always_included_and_ribbed_when_last():
    lb = [
        {"player": "Ruari", "total": 10, "exact": 3, "result": 1, "rank": 1, "movement": 0, "group_pts": 10, "knockout_pts": 0},
        {"player": "Daisy", "total": 6, "exact": 1, "result": 3, "rank": 2, "movement": 0, "group_pts": 6, "knockout_pts": 0},
        {"player": "Karim", "total": 1, "exact": 0, "result": 1, "rank": 3, "movement": 0, "group_pts": 1, "knockout_pts": 0},
    ]
    msg = compose(fixtures=FIXTURES, results={"1": {"home": 2, "away": 1}},
                  points={"1": {"Ruari": 3}}, leaderboard=lb, reported=[], today="2026-06-12")
    assert "Karim watch" in msg          # named in every update (main() then garbles the spelling)
    assert "dead last" in msg            # ribbed when bottom

def test_karim_line_bands():
    bottom = [{"player": "X", "rank": 1, "total": 9}, {"player": "Karim", "rank": 2, "total": 2}]
    assert "dead last" in digest.karim_line(bottom)
    assert digest.karim_line([{"player": "X", "rank": 1, "total": 9}]) is None  # no Karim -> nothing

def test_garble_karim_replaces_with_a_typo():
    import random
    out, pick = digest.garble_karim("1. Karim — 12\n🎯 Exact: Karim", rng=random.Random(1))
    assert pick in digest.KARIM_TYPOS
    assert "Karim" not in out          # the real name is gone
    assert out.count(pick) == 2        # both occurrences swapped, same typo

def test_garble_karim_noop_without_karim():
    out, pick = digest.garble_karim("1. Ruari — 9")
    assert out == "1. Ruari — 9" and pick is None

def test_garble_karim_avoids_immediate_repeat():
    import random
    prev = digest.KARIM_TYPOS[0]
    for seed in range(25):
        _, pick = digest.garble_karim("Karim", exclude=prev, rng=random.Random(seed))
        assert pick != prev

def test_skips_when_already_sent_today(tmp_path, monkeypatch):
    import datetime
    from zoneinfo import ZoneInfo
    import scripts.send_whatsapp as sw
    sent = []
    monkeypatch.setattr(sw, "send", lambda msg: sent.append(msg))
    monkeypatch.setattr(digest, "DATA", str(tmp_path))
    monkeypatch.delenv("DRY_RUN", raising=False)
    monkeypatch.delenv("FORCE_SEND", raising=False)
    today = datetime.datetime.now(ZoneInfo("Europe/London")).date().isoformat()
    (tmp_path / "fixtures.json").write_text(json.dumps(FIXTURES))
    (tmp_path / "results.json").write_text(json.dumps({"1": {"home": 2, "away": 1}}))
    (tmp_path / "points.json").write_text(json.dumps({"1": {"Ruari": 3}}))
    (tmp_path / "leaderboard.json").write_text(json.dumps(LB))
    (tmp_path / "digest_state.json").write_text(json.dumps({"reported": ["1"], "last_sent": today}))
    digest.main()
    assert sent == []   # already sent today -> no second message

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
