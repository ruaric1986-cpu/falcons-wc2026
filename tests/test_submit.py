import datetime
from scripts.submit_predictions import merge

NOW = datetime.datetime(2026, 7, 5, 12, 0, tzinfo=datetime.timezone.utc)
PLAYERS = ["Ruari", "Karim"]
FIXTURES = [
    {"number": 89, "stage": "R16", "home": "Canada", "away": "Morocco", "kickoff": "2026-07-06T17:00:00Z"},
    {"number": 90, "stage": "R16", "home": "Paraguay", "away": "France", "kickoff": "2026-07-04T21:00:00Z"},  # past
    {"number": 93, "stage": "R16", "home": "TBD", "away": "TBD", "kickoff": "2026-07-06T19:00:00Z"},
]


def test_accepts_valid_and_normalises():
    preds = {}
    preds, ok, bad = merge("Ruari", {"89": "2 - 1"}, PLAYERS, FIXTURES, preds, now=NOW)
    assert ok == {"89": "2-1"} and bad == {}
    assert preds["89"]["Ruari"] == "2-1"


def test_rejects_past_kickoff():
    preds, ok, bad = merge("Ruari", {"90": "1-0"}, PLAYERS, FIXTURES, {}, now=NOW)
    assert ok == {} and "deadline" in bad["90"]


def test_rejects_tbd_and_unknown_fixture():
    preds, ok, bad = merge("Ruari", {"93": "1-0", "999": "1-0"}, PLAYERS, FIXTURES, {}, now=NOW)
    assert ok == {} and "93" in bad and "999" in bad


def test_lock_prevents_amend():
    preds = {"89": {"Ruari": "2-1"}}
    preds, ok, bad = merge("Ruari", {"89": "0-0"}, PLAYERS, FIXTURES, preds, now=NOW)
    assert ok == {} and "locked" in bad["89"]
    assert preds["89"]["Ruari"] == "2-1"  # unchanged


def test_unknown_player_rejected():
    preds, ok, bad = merge("Hacker", {"89": "1-0"}, PLAYERS, FIXTURES, {}, now=NOW)
    assert ok == {} and "_player" in bad


def test_bad_score_rejected():
    preds, ok, bad = merge("Ruari", {"89": "one-nil"}, PLAYERS, FIXTURES, {}, now=NOW)
    assert ok == {} and "bad score" in bad["89"]


def test_other_player_pick_does_not_block():
    preds = {"89": {"Karim": "1-1"}}
    preds, ok, bad = merge("Ruari", {"89": "2-0"}, PLAYERS, FIXTURES, preds, now=NOW)
    assert ok == {"89": "2-0"}
    assert preds["89"] == {"Karim": "1-1", "Ruari": "2-0"}
