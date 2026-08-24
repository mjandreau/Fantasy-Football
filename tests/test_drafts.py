from pathlib import Path

import pytest

from build.drafts import build_drafts

ESPN_DIR = Path(__file__).resolve().parent.parent / "data" / "espn"


@pytest.fixture
def drafts():
    if not ESPN_DIR.exists() or not list(ESPN_DIR.glob("league_*.json")):
        pytest.skip("ESPN cache not present")
    return build_drafts(ESPN_DIR)


def _drafted_years():
    """Seasons with a draft in the cache, read independently of build_drafts."""
    import json
    out = []
    for path in ESPN_DIR.glob("league_*.json"):
        if json.loads(path.read_text(encoding="utf-8"))["draft"]:
            out.append(int(path.stem.split("_")[1]))
    return sorted(out)


def test_all_years_present(drafts):
    assert sorted(int(y) for y in drafts["years"]) == _drafted_years()
    assert len(drafts["years"]["2025"]["picks"]) == 228
    assert len(drafts["years"]["2012"]["picks"]) == 200
    # overall pick numbers are 1..N contiguous
    p = drafts["years"]["2025"]["picks"]
    assert [x["overall"] for x in p] == list(range(1, 229))


def test_first_overall_gallery(drafts):
    fo = drafts["first_overall"]
    years = _drafted_years()
    assert len(fo) == len(years)
    assert fo[0]["year"] == 2011 and fo[0]["player"] == "Michael Vick"
    assert fo[0]["owner"] == "Matt"
    assert fo[-1]["year"] == years[-1]
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


def _unplayed_drafted_years():
    """Seasons already drafted but with no game results yet -- the board should
    show, but nothing that needs points should."""
    import json
    out = []
    for path in ESPN_DIR.glob("league_*.json"):
        year = path.stem.split("_")[1]
        if not json.loads(path.read_text(encoding="utf-8"))["draft"]:
            continue
        bs = ESPN_DIR / f"boxscores_{year}.json"
        if not bs.exists():
            continue
        blob = json.loads(bs.read_text(encoding="utf-8"))
        if not any(m.get("home_score") or m.get("away_score")
                   for week in blob["weeks"].values() for m in week):
            out.append(int(year))
    return sorted(out)


def test_upcoming_draft_shows_a_board_but_no_scoring_analysis(drafts):
    """Once the draft happens ESPN serves the season's box scores as real
    lineups at zero points. The board is real and belongs on the tab; ranking
    those zeros would manufacture steals, busts and draft grades out of noise."""
    upcoming = _unplayed_drafted_years()
    if not upcoming:
        pytest.skip("no drafted-but-unplayed season in the cache")
    for year in upcoming:
        picks = drafts["years"][str(year)]["picks"]
        assert picks, f"{year} board is missing"
        assert all(p["points"] is None for p in picks), \
            f"{year} picks carry point totals before a game has been played"
        for bucket in ("steals", "busts"):
            assert not [e for e in drafts["value"][bucket] if e["year"] == year], \
                f"{year} produced {bucket} with no scoring"
    # Draft grades must be built only from seasons that were actually played.
    played_picks = sum(len(drafts["years"][y]["picks"]) for y in drafts["years"]
                       if int(y) not in upcoming and int(y) >= 2019)
    assert sum(g["picks"] for g in drafts["value"]["grades"]) <= played_picks
