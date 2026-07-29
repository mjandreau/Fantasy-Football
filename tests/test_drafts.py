from pathlib import Path

import pytest

from build.drafts import build_drafts

ESPN_DIR = Path(__file__).resolve().parent.parent / "data" / "espn"


@pytest.fixture
def drafts():
    if not ESPN_DIR.exists() or not list(ESPN_DIR.glob("league_*.json")):
        pytest.skip("ESPN cache not present")
    return build_drafts(ESPN_DIR)


def test_all_years_present(drafts):
    assert sorted(int(y) for y in drafts["years"]) == list(range(2011, 2026))
    assert len(drafts["years"]["2025"]["picks"]) == 228
    assert len(drafts["years"]["2012"]["picks"]) == 200
    # overall pick numbers are 1..N contiguous
    p = drafts["years"]["2025"]["picks"]
    assert [x["overall"] for x in p] == list(range(1, 229))


def test_first_overall_gallery(drafts):
    fo = drafts["first_overall"]
    assert len(fo) == 15
    assert fo[0] == {"year": 2011, "player": "Michael Vick",
                     "owner": "Matt", "team_name": fo[0]["team_name"]}
    assert fo[-1]["year"] == 2025


def test_value_analysis(drafts):
    v = drafts["value"]
    assert len(v["grades"]) == 12
    for g in v["grades"]:
        assert g["picks"] >= 7 * 15          # 7 seasons of ~19 picks
    steals = v["steals"]
    assert steals[0]["delta"] >= 100         # a late pick that finished top-10
    deltas = [s["delta"] for s in steals]
    assert deltas == sorted(deltas, reverse=True)
    busts = v["busts"]
    assert all(b["round"] <= 4 for b in busts)
    assert busts[0]["delta"] < -50           # an early pick that cratered
