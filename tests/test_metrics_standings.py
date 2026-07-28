from build.games import build_games
from build.metrics import standings

def test_all_time_standings_structure(league_history_path):
    rows = build_and_stand(league_history_path)
    # 15 all-time owners: 12 active + 3 historical (2011-2014)
    assert len(rows) == 15
    top = rows[0]
    for k in ("owner", "wins", "losses", "ties", "win_pct", "pf", "pa",
              "games", "avg_score", "power_index", "power_rank"):
        assert k in top
    assert top["power_rank"] == 1
    # ranks are 1..15 unique
    assert sorted(r["power_rank"] for r in rows) == list(range(1, 16))

def test_early_season_has_ten_teams(league_history_path):
    from build.games import build_games
    rows = standings(build_games(league_history_path), season=2011)
    assert len(rows) == 10  # 10-team era

def test_standings_regular_season_only(league_history_path):
    games = build_games(league_history_path)
    rows = standings(games)  # all-time
    total_games = sum(r["games"] for r in rows)
    reg_games = sum(1 for g in games if g["phase"] == "regular")
    # each regular game contributes to 2 owners' game counts
    assert total_games == reg_games * 2

def test_season_standings_2025(league_history_path):
    games = build_games(league_history_path)
    rows = standings(games, season=2025)
    assert len(rows) == 12
    assert sum(r["games"] for r in rows) == sum(
        1 for g in games if g["season"] == 2025 and g["phase"] == "regular") * 2

def build_and_stand(path):
    return standings(build_games(path))
