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
    assert fo[0]["year"] == 2011 and fo[0]["player"] == "Michael Vick"
    assert fo[0]["owner"] == "Matt"
    assert fo[-1]["year"] == 2025
    # gallery is the OFFENSIVE #1; the defensive draft's #1 rides along
    for f in fo:
        assert f["def_player"]
    # 2024's defensive draft came first — Crosby is def #1, not the gallery pick
    y24 = next(f for f in fo if f["year"] == 2024)
    assert y24["def_player"] == "Maxx Crosby"
    assert y24["player"] != "Maxx Crosby"


def test_pick_enrichment(drafts):
    # 2025 (box-score era): full enrichment
    p1 = drafts["years"]["2025"]["picks"][0]
    assert p1["player"] == "CeeDee Lamb" and p1["pos"] == "WR"
    assert p1["pro_team"] and p1["points"] > 100
    # 2011 (pre box scores): position from the core athlete API, no points
    v = drafts["years"]["2011"]["picks"][0]
    assert v["pos"] == "QB"            # Michael Vick
    assert v["points"] is None and v["pro_team"] is None
    # D/ST picks resolve to a position everywhere — and belong to the MAIN
    # (offensive) draft; the defensive draft is individual defenders only
    dst = [p for y in drafts["years"].values() for p in y["picks"]
           if p["player_id"] < 0]
    assert dst and all(p["pos"] == "D/ST" and p["side"] == "OFF" for p in dst)
    # modern defensive draft = 3 rounds x 12 teams
    d25 = [p for p in drafts["years"]["2025"]["picks"] if p["side"] == "DEF"]
    assert len(d25) == 36
    assert all(p["pos"] in {"DE", "DT", "LB", "CB", "S"} for p in d25)


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
    # busts = first four OFFENSIVE rounds of the offense draft
    assert all(b["side"] == "OFF" and b["overall"] <= 48 for b in busts)
    assert busts[0]["delta"] < -50           # an early pick that cratered
