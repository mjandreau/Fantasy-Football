from pathlib import Path

import pytest

from build.lineups import build_lineups

ESPN_DIR = Path(__file__).resolve().parent.parent / "data" / "espn"


@pytest.fixture
def lineups():
    if not ESPN_DIR.exists() or not list(ESPN_DIR.glob("boxscores_*.json")):
        pytest.skip("ESPN cache not present")
    return build_lineups(ESPN_DIR)


def test_efficiency_table(lineups):
    rows = lineups["efficiency"]
    assert len(rows) == 12                      # all active owners map
    for r in rows:
        assert r["optimal"] >= r["actual"] > 0  # optimal is an upper bound
        assert 0.5 < r["efficiency"] <= 1.0
        assert r["wasted"] == pytest.approx(r["optimal"] - r["actual"], abs=0.1)
        assert r["games"] > 50                   # 7 seasons of weekly lineups


def test_per_season_shape(lineups):
    per = lineups["by_season"]
    assert set(per.keys()) == {str(y) for y in range(2019, 2026)}
    assert len(per["2025"]) == 12


def test_blunders_sorted(lineups):
    bl = lineups["blunders"]
    assert 5 <= len(bl) <= 15
    wasted = [b["wasted"] for b in bl]
    assert wasted == sorted(wasted, reverse=True)
    for b in bl:
        assert b["owner"] and b["season"] and b["benched_star"]
        assert b["wasted"] > 20                  # blunders are big misses


def test_all_time_teams(lineups):
    teams = lineups["all_time_teams"]
    assert len(teams) == 12
    for owner, team in teams.items():
        slots = [r["slot"] for r in team]
        assert slots == ["QB", "RB1", "RB2", "WR1", "WR2", "TE", "K", "D/ST",
                         "DL", "LB", "DB"]
        qb = team[0]
        assert qb["pos"] == "QB" and qb["points"] > 100
        rb1, rb2 = team[1], team[2]
        assert rb1["points"] >= rb2["points"]
        assert rb1["player"] != rb2["player"] or rb1["player"] == "—"


def test_final_standings():
    if not ESPN_DIR.exists() or not list(ESPN_DIR.glob("league_*.json")):
        pytest.skip("ESPN cache not present")
    from build.lineups import final_standings
    from build.curated import CHAMPIONS
    fs = final_standings(ESPN_DIR)
    # every season's place-1 owner is exactly the curated champion
    for year, rec in CHAMPIONS.items():
        winners = [o for o, years in fs.items() if years.get(year) == 1]
        assert winners == [rec["champion"]], f"{year}: {winners}"
    # Walter's best final placement is 1; every owner has >= 1 season recorded
    assert min(fs["Walter"].values()) == 1
    assert len(fs) == 15


def test_bench_records(lineups):
    br = lineups["bench_records"]
    assert len(br) >= 5
    pts = [b["points"] for b in br]
    assert pts == sorted(pts, reverse=True)
    assert pts[0] >= 40                          # someone benched a monster
