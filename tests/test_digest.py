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

def test_karim_always_in_movers_no_commentary():
    def row(player, total, rank, movement):
        return {"player": player, "total": total, "exact": 0, "result": 0,
                "rank": rank, "movement": movement, "group_pts": total, "knockout_pts": 0}
    lb = [row(f"P{i}", 30 - i, i + 1, 0) for i in range(5)] + [row("Karim", 3, 14, 0)]
    msg = compose(fixtures=FIXTURES, results={"1": {"home": 2, "away": 1}},
                  points={"1": {"P0": 3}}, leaderboard=lb, reported=[], today="2026-06-12")
    assert "➡️ Karim 14th" in msg          # featured even with no movement
    assert msg.count("Karim") == 1          # once, not duplicated
    for w in ("watch", "dead last", "midtable", "stragglers"):
        assert w not in msg                 # no commentary

def test_karim_mover_directions():
    base = [{"player": f"P{i}", "rank": i + 1, "movement": 0, "total": 9} for i in range(5)]
    up = digest._karim_mover(base + [{"player": "Karim", "rank": 9, "movement": 4, "total": 3}])
    dn = digest._karim_mover(base + [{"player": "Karim", "rank": 12, "movement": -2, "total": 3}])
    assert up == "📈 Karim up 4 to 9" and dn == "📉 Karim down 2 to 12"

def test_drift_sequence_worsens_and_ends_at_steve():
    assert digest.KARIM_DRIFT[-1] == "Steve"
    assert digest.drift_karim("Karim", 0) == ("Kareem", True)   # day 1: still close
    assert digest.drift_karim("Karim", 1)[0] == "Kareen"        # drifting
    assert digest.drift_karim("Karim", 999)[0] == "Steve"       # clamps at the end

def test_drift_noop_without_karim():
    assert digest.drift_karim("1. Ruari — 9", 0) == ("1. Ruari — 9", False)

def test_drift_applied_on_send_and_advances(tmp_path, monkeypatch):
    import scripts.send_whatsapp as sw
    sent = []
    monkeypatch.setattr(sw, "send", lambda m: sent.append(m))
    monkeypatch.setattr(digest, "DATA", str(tmp_path))
    monkeypatch.delenv("DRY_RUN", raising=False)
    monkeypatch.delenv("FORCE_SEND", raising=False)
    lb = [{"player": "Karim", "total": 6, "exact": 1, "result": 0, "rank": 1, "movement": 0, "group_pts": 6, "knockout_pts": 0}]
    (tmp_path / "fixtures.json").write_text(json.dumps(FIXTURES))
    (tmp_path / "results.json").write_text(json.dumps({"1": {"home": 2, "away": 1}}))
    (tmp_path / "points.json").write_text(json.dumps({"1": {"Karim": 3}}))
    (tmp_path / "leaderboard.json").write_text(json.dumps(lb))
    (tmp_path / "digest_state.json").write_text(json.dumps({"reported": []}))
    digest.main()
    assert sent and "Kareem" in sent[0] and "Karim" not in sent[0]   # drift applied everywhere, incl. exact section
    assert json.loads((tmp_path / "digest_state.json").read_text())["karim_step"] == 1  # advances for next time

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
