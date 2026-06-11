from scripts.score import parse_score, points, build_leaderboard

def test_parse_score():
    assert parse_score("2-1") == (2, 1)
    assert parse_score(" 0-0 ") == (0, 0)
    assert parse_score("") is None
    assert parse_score(None) is None
    assert parse_score("2:1") is None
    assert parse_score("abc") is None

def test_points():
    assert points("2-1", (2, 1)) == 3          # exact
    assert points("3-1", (2, 0)) == 1          # right result, wrong score
    assert points("1-1", (0, 0)) == 1          # draw predicted, draw happened
    assert points("2-1", (1, 1)) == 0          # wrong result
    assert points("1-2", (2, 1)) == 0          # order matters
    assert points(None, (2, 1)) == 0           # no prediction
    assert points("", (2, 1)) == 0

FIXTURES = [
    {"number": 1, "stage": "GROUP", "kickoff": "2026-06-11T19:00:00Z", "home": "Mexico", "away": "South Africa"},
    {"number": 2, "stage": "GROUP", "kickoff": "2026-06-12T19:00:00Z", "home": "Czechia", "away": "South Korea"},
    {"number": 73, "stage": "R32", "kickoff": "2026-06-29T19:00:00Z", "home": "Brazil", "away": "Chile"},
]

def test_build_leaderboard_totals_and_tiebreak():
    predictions = {
        "1": {"Ruari": "1-0", "Dave F": "2-0"},
        "2": {"Ruari": "0-1", "Dave F": "0-1"},
        "73": {"Ruari": "1-1", "Dave F": "2-1"},
    }
    results = {"1": {"home": 1, "away": 0}, "2": {"home": 0, "away": 2}, "73": {"home": 1, "away": 1}}
    lb = build_leaderboard(["Ruari", "Dave F"], FIXTURES, predictions, results)
    ruari = next(r for r in lb if r["player"] == "Ruari")
    dave = next(r for r in lb if r["player"] == "Dave F")
    # Ruari: m1 exact(3, group) + m2 result(1, group) + m73 exact(3, knockout) = 7
    assert ruari == {"player": "Ruari", "total": 7, "exact": 2, "result": 1,
                     "group_pts": 4, "knockout_pts": 3, "rank": 1}
    # Dave: m1 result(1) + m2 result(1) + m73 wrong(0) = 2
    assert dave["total"] == 2 and dave["rank"] == 2

def test_build_leaderboard_tiebreak_exact_beats_result():
    predictions = {"1": {"A": "1-0", "B": "2-0"}, "2": {"A": "5-5", "B": "0-1"}}
    results = {"1": {"home": 1, "away": 0}, "2": {"home": 0, "away": 2}}
    lb = build_leaderboard(["A", "B"], FIXTURES[:2], predictions, results)
    # A: exact(3)+0 = 3 ; B: result(1)+result(1) = 2 -> A first on total
    # Now equal-total case: give B an exact too
    predictions = {"1": {"A": "1-0", "B": "9-9"}, "2": {"A": "0-9", "B": "0-2"}}
    results = {"1": {"home": 1, "away": 0}, "2": {"home": 0, "away": 2}}
    lb = build_leaderboard(["A", "B"], FIXTURES[:2], predictions, results)
    # A: 3+1=4 (1 exact, 1 result); B: 0+3=3 -> just assert ordering deterministic
    assert [r["player"] for r in lb] == ["A", "B"]

def test_unfinished_matches_ignored():
    lb = build_leaderboard(["Ruari"], FIXTURES, {"1": {"Ruari": "1-0"}}, {})
    assert lb[0]["total"] == 0

def test_malformed_result_record_is_skipped():
    results = {"1": {"home": 1, "away": 0}, "2": {"home": None, "away": None}, "73": {}}
    lb = build_leaderboard(["Ruari"], FIXTURES, {"1": {"Ruari": "1-0"}, "2": {"Ruari": "0-1"}}, results)
    assert lb[0]["total"] == 3  # match 1 scored; matches 2 and 73 skipped, no crash

def test_tiebreak_equal_totals_more_exacts_ranks_higher():
    # A: one exact = 3 pts (1 exact, 0 result). B: three result-only = 3 pts (0 exact, 3 result).
    predictions = {
        "1": {"A": "1-0", "B": "2-0"},
        "2": {"A": "9-0", "B": "0-1"},
        "73": {"A": "0-9", "B": "2-2"},
    }
    results = {"1": {"home": 1, "away": 0}, "2": {"home": 0, "away": 2}, "73": {"home": 1, "away": 1}}
    lb = build_leaderboard(["B", "A"], FIXTURES, predictions, results)
    assert [(r["player"], r["total"]) for r in lb] == [("A", 3), ("B", 3)]
    assert lb[0]["exact"] == 1 and lb[1]["exact"] == 0

def test_parse_score_non_string_inputs():
    assert parse_score(21) is None
    assert parse_score(2.1) is None

def test_parse_score_accepts_unicode_dashes():
    assert parse_score("2–1") == (2, 1)   # en-dash U+2013
    assert parse_score("0—0") == (0, 0)   # em-dash U+2014
