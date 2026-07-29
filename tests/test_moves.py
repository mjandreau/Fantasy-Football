from pathlib import Path

import pytest

from build.moves import build_moves, build_waivers, build_left_on_waivers

ESPN_DIR = Path(__file__).resolve().parent.parent / "data" / "espn"


def _needs(pattern):
    if not ESPN_DIR.exists() or not list(ESPN_DIR.glob(pattern)):
        pytest.skip(f"ESPN cache missing {pattern}")


def test_moves_career_counters():
    _needs("league_*.json")
    m = build_moves(ESPN_DIR)
    assert len(m["career"]) == 15                 # all all-time owners
    import json
    sample = json.loads((ESPN_DIR / "league_2012.json").read_text())
    assert any(t.get("acquisitions") for t in sample["teams"])  # counters cached
    active = [r for r in m["career"] if r["seasons"] >= 10]
    for r in active:
        assert r["adds"] > 50                     # a decade of churn
        assert r["adds_per_season"] == pytest.approx(r["adds"] / r["seasons"], abs=0.1)
    assert m["signal"]["median_adds"] > 10
    # scatter has one point per owner-season with a final standing
    assert len(m["scatter"]) >= 170


def test_waiver_hall_of_fame():
    _needs("boxscores_*.json")
    w = build_waivers(ESPN_DIR)
    hof = w["hall_of_fame"]
    assert len(hof) == 15
    pts = [r["points"] for r in hof]
    assert pts == sorted(pts, reverse=True)
    assert pts[0] > 150                           # someone's pickup won them a title
    for r in hof:
        assert r["week"] > 1                      # pickups, not opening rosters
    assert len(w["best_by_owner"]) == 12


def test_left_on_waivers():
    _needs("free_agents_*.json")
    rows = build_left_on_waivers(ESPN_DIR)
    assert rows and rows[0]["points"] >= 100
    assert all(r["points"] >= rows[-1]["points"] for r in rows)
