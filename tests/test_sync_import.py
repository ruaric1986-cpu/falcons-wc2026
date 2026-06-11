import json, openpyxl
from scripts.sync_import import import_results
from tests.test_sync import make_wb

def test_import_writes_results_and_ko_teams(tmp_path):
    xlsx = tmp_path / "wc.xlsx"; make_wb(xlsx)
    d = tmp_path / "data"; d.mkdir()
    with open(d / "results.json", "w") as fh:
        json.dump({"2": {"home": 0, "away": 2}}, fh)
    with open(d / "fixtures.json", "w") as fh:
        json.dump([{"number": 2, "stage": "GROUP", "kickoff": "2026-06-12", "home": "Czechia", "away": "South Korea", "api_id": 5},
                   {"number": 73, "stage": "R32", "kickoff": "2026-06-29T19:00:00Z", "home": "Brazil", "away": "Chile", "api_id": 9}], fh)
    import_results(str(xlsx), str(d))
    wb = openpyxl.load_workbook(xlsx)
    gs, ko = wb["Group Stage"], wb["Knockouts"]
    assert gs["F5"].value == 0 and gs["G5"].value == 2      # match 2 result written (row 5)
    assert gs["F4"].value == 2 and gs["G4"].value == 1      # existing result untouched (match 1)
    assert ko["D4"].value == "Brazil" and ko["E4"].value == "Chile"
    assert "2026-06-29" in str(ko["C4"].value)
