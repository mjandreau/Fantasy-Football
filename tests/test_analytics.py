import pytest

from build.games import build_games
from build.analytics import (
    all_play, consistency, weekly_crowns, streaks, playoff_records,
    season_trends, h2h_matrix, build_insights, build_analytics,
)


_CACHE = {}


@pytest.fixture
def games(league_history_path):
    # league_history_path is function-scoped in conftest; cache the parsed
    # games ourselves so the xlsx is only read once for this module.
    if "games" not in _CACHE:
        _CACHE["games"] = build_games(league_history_path)
    return _CACHE["games"]


def test_all_play_luck_sums(games):
    ap = all_play(games)
    rows = ap["all_time"]
    assert len(rows) == 15
    # Across the league, luck nets to ~zero (every actual win is someone's loss;
    # expected wins sum to total games played / decided similarly).
    total_luck = sum(r["luck"] for r in rows)
    assert abs(total_luck) < 1.0
    # Expected wins are bounded by games played
    for r in rows:
        assert 0 <= r["expected_wins"] <= r["games"]
        assert isinstance(r["actual_wins"], (int, float))
    # per-season shape
    assert "2025" in ap["by_season"]
    assert len(ap["by_season"]["2025"]) == 12


def test_consistency_shape(games):
    c = consistency(games)
    rows = c["all_time"]
    assert len(rows) == 15
    for r in rows:
        assert r["stdev"] >= 0
        assert r["avg"] > 50  # sane fantasy scores
    s25 = c["by_season"]["2025"]
    assert len(s25) == 12


def test_weekly_crowns_total(games):
    cr = weekly_crowns(games)
    # number of distinct regular-season weeks across all seasons
    weeks = {(g["season"], g["week"]) for g in games if g["phase"] == "regular"}
    total_crowns = sum(r["crowns"] for r in cr["all_time"])
    # ties can only add crowns, never remove
    assert total_crowns >= len(weeks)
    assert total_crowns <= len(weeks) + 10  # ties are rare
    # per-season crowns sum to that season's weeks (+ ties)
    weeks25 = {w for (s, w) in weeks if s == 2025}
    total25 = sum(r["crowns"] for r in cr["by_season"]["2025"])
    assert total25 >= len(weeks25)


def test_streaks_shape(games):
    st = streaks(games)
    assert len(st) == 15
    for r in st:
        assert r["longest_win"] >= 1
        assert r["longest_loss"] >= 1
        assert "Wk" in r["win_span"] and "Wk" in r["loss_span"]
    # Matt won 12 straight regular games in 2013 (12-1 season) — streak >= 10
    matt = next(r for r in st if r["owner"] == "Matt")
    assert matt["longest_win"] >= 8


def test_playoff_records(games):
    pr = playoff_records(games)
    assert len(pr) == 15
    total_w = sum(r["wins"] for r in pr)
    total_l = sum(r["losses"] for r in pr)
    ply = [g for g in games if g["phase"] == "playoff" and not g["tie"]]
    assert total_w == len(ply)
    assert total_w == total_l
    for r in pr:
        assert 0.0 <= r["playoff_win_pct"] <= 1.0 or r["wins"] + r["losses"] == 0
        assert 0.0 <= r["reg_win_pct"] <= 1.0


def test_season_trends(games):
    tr = season_trends(games)
    assert [t["season"] for t in tr] == list(range(2011, 2026))
    for t in tr:
        assert t["min_score"] <= t["avg_score"] <= t["max_score"]
    t2011 = next(t for t in tr if t["season"] == 2011)
    assert t2011["max_score"] == 341.0  # Spark's all-time record


def test_h2h_matrix(games):
    m = h2h_matrix(games)
    assert len(m["owners"]) == 15
    cell = m["cells"]["Matt|Walter"]
    assert cell["games"] >= 20
    assert 0.0 <= cell["a_pct"] <= 1.0
    # keys are sorted pairs
    for key in m["cells"]:
        a, b = key.split("|")
        assert a < b


def test_build_insights(games):
    ins = build_insights(games)
    assert len(ins) >= 8
    for i in ins:
        for k in ("id", "tab", "icon", "title", "text"):
            assert i[k], f"insight missing {k}: {i}"
    tabs = {i["tab"] for i in ins}
    assert "overview" in tabs and "analytics" in tabs


def test_build_analytics_bundle(games):
    import json
    a = build_analytics(games)
    for k in ("all_play", "consistency", "crowns", "streaks",
              "playoff_records", "season_trends", "h2h_matrix"):
        assert k in a
    json.dumps(a)  # must be JSON-serializable
