import json
from scripts.fetch_results import map_and_extract, norm

API = {"matches": [
    {"id": 9001, "stage": "GROUP_STAGE", "group": "Group A", "utcDate": "2026-06-11T19:00:00Z",
     "status": "FINISHED", "homeTeam": {"name": "Mexico"}, "awayTeam": {"name": "South Africa"},
     "score": {"duration": "REGULAR", "fullTime": {"home": 2, "away": 1}}},
    {"id": 9002, "stage": "GROUP_STAGE", "group": "Group A", "utcDate": "2026-06-12T19:00:00Z",
     "status": "TIMED", "homeTeam": {"name": "Korea Republic"}, "awayTeam": {"name": "Czechia"},
     "score": {"duration": "REGULAR", "fullTime": {"home": None, "away": None}}},
    {"id": 9100, "stage": "LAST_32", "group": None, "utcDate": "2026-06-29T19:00:00Z",
     "status": "FINISHED", "homeTeam": {"name": "Brazil"}, "awayTeam": {"name": "Chile"},
     "score": {"duration": "PENALTY_SHOOTOUT", "fullTime": {"home": 3, "away": 2},
               "regularTime": {"home": 1, "away": 1}}},
]}

FIXTURES = [
    {"number": 1, "stage": "GROUP", "group": "A", "kickoff": "2026-06-11", "home": "Mexico", "away": "South Africa", "api_id": None},
    {"number": 2, "stage": "GROUP", "group": "A", "kickoff": "2026-06-12", "home": "South Korea", "away": "Czechia", "api_id": None},
    {"number": 73, "stage": "R32", "group": None, "kickoff": None, "home": "TBD", "away": "TBD", "api_id": None},
]

def test_norm_aliases():
    assert norm("Korea Republic") == norm("South Korea")
    assert norm("Côte d'Ivoire") == norm("Ivory Coast")

def test_map_and_extract():
    fixtures = json.loads(json.dumps(FIXTURES))
    results, unmatched = map_and_extract(API["matches"], fixtures)
    assert results["1"] == {"home": 2, "away": 1}            # group, regular time
    assert "2" not in results                                  # not finished
    assert results["73"] == {"home": 1, "away": 1}            # KO: 90-min score, not pens
    assert fixtures[0]["api_id"] == 9001
    assert fixtures[1]["api_id"] == 9002                       # matched via alias despite TIMED
    ko = fixtures[2]
    assert ko["api_id"] == 9100 and ko["home"] == "Brazil" and ko["away"] == "Chile"
    assert ko["kickoff"] == "2026-06-29T19:00:00Z"
    assert unmatched == []

def test_reversed_fixture_result_swapped_into_sheet_orientation():
    fixtures = [{"number": 5, "stage": "GROUP", "group": "C", "kickoff": "2026-06-13",
                 "home": "Morocco", "away": "Brazil", "api_id": None}]  # sheet reversed vs API
    api = [{"id": 9005, "stage": "GROUP_STAGE", "group": "Group C", "utcDate": "2026-06-13T19:00:00Z",
            "status": "FINISHED", "homeTeam": {"name": "Brazil"}, "awayTeam": {"name": "Morocco"},
            "score": {"duration": "REGULAR", "fullTime": {"home": 3, "away": 1}}}]
    results, unmatched = map_and_extract(api, fixtures)
    assert unmatched == []
    assert fixtures[0]["api_id"] == 9005
    assert results["5"] == {"home": 1, "away": 3}  # sheet home is Morocco -> 1-3

def test_ko_assignment_is_per_stage():
    fixtures = [
        {"number": 73, "stage": "R32", "group": None, "kickoff": None, "home": "TBD", "away": "TBD", "api_id": None},
        {"number": 74, "stage": "R32", "group": None, "kickoff": None, "home": "TBD", "away": "TBD", "api_id": None},
        {"number": 89, "stage": "R16", "group": None, "kickoff": None, "home": "TBD", "away": "TBD", "api_id": None},
    ]
    # only ONE R32 match drawn so far, but an R16 match already scheduled in the API
    api = [
        {"id": 9100, "stage": "LAST_32", "group": None, "utcDate": "2026-06-29T19:00:00Z",
         "status": "TIMED", "homeTeam": {"name": "Brazil"}, "awayTeam": {"name": "Chile"},
         "score": {"duration": "REGULAR", "fullTime": {"home": None, "away": None}}},
        {"id": 9200, "stage": "LAST_16", "group": None, "utcDate": "2026-07-03T19:00:00Z",
         "status": "TIMED", "homeTeam": {"name": "TBD"}, "awayTeam": {"name": "TBD"},
         "score": {"duration": "REGULAR", "fullTime": {"home": None, "away": None}}},
    ]
    map_and_extract(api, fixtures)
    assert fixtures[0]["api_id"] == 9100           # R32 match -> first R32 slot
    assert fixtures[1]["api_id"] is None           # second R32 slot stays empty
    assert fixtures[2]["api_id"] == 9200           # R16 match -> R16 slot, NOT slot 74


def test_reversed_fixture_swapped_when_api_id_already_set():
    fixtures = [{"number": 5, "stage": "GROUP", "group": "C", "kickoff": "2026-06-13",
                 "home": "Morocco", "away": "Brazil", "api_id": 9005}]
    api = [{"id": 9005, "stage": "GROUP_STAGE", "group": "Group C", "utcDate": "2026-06-13T19:00:00Z",
            "status": "FINISHED", "homeTeam": {"name": "Brazil"}, "awayTeam": {"name": "Morocco"},
            "score": {"duration": "REGULAR", "fullTime": {"home": 3, "away": 1}}}]
    results, _ = map_and_extract(api, fixtures)
    assert results["5"] == {"home": 1, "away": 3}


def test_finished_match_with_null_score_skipped():
    fixtures = [{"number": 1, "stage": "GROUP", "group": "A", "kickoff": "2026-06-11",
                 "home": "Mexico", "away": "South Africa", "api_id": None}]
    api = [{"id": 9001, "stage": "GROUP_STAGE", "group": "Group A", "utcDate": "2026-06-11T19:00:00Z",
            "status": "FINISHED", "homeTeam": {"name": "Mexico"}, "awayTeam": {"name": "South Africa"},
            "score": {"winner": None, "duration": "REGULAR", "fullTime": {"home": None, "away": None}}}]
    results, unmatched = map_and_extract(api, fixtures)
    assert results == {} and unmatched == []


def test_finished_match_with_null_score_retains_prior():
    # API transiently drops the 90-min score for a match we already scored —
    # keep the previously stored result instead of losing it.
    fixtures = [{"number": 1, "stage": "GROUP", "group": "A", "kickoff": "2026-06-11",
                 "home": "Mexico", "away": "South Africa", "api_id": None}]
    api = [{"id": 9001, "stage": "GROUP_STAGE", "group": "Group A", "utcDate": "2026-06-11T19:00:00Z",
            "status": "FINISHED", "homeTeam": {"name": "Mexico"}, "awayTeam": {"name": "South Africa"},
            "score": {"winner": None, "duration": "REGULAR", "fullTime": {"home": None, "away": None}}}]
    results, unmatched = map_and_extract(api, fixtures, prior={"1": {"home": 2, "away": 0}})
    assert results == {"1": {"home": 2, "away": 0}} and unmatched == []
