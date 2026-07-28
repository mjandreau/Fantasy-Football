from build.games import build_games, season_team_names

def test_build_games_shape_and_counts(league_history_path):
    games = build_games(league_history_path)
    assert len(games) == 1399
    g = games[0]
    for k in ("season", "week", "phase", "home_owner", "away_owner",
              "home_team", "away_team", "home_score", "away_score",
              "winner", "loser", "margin", "tie"):
        assert k in g

def test_build_games_winner_and_margin(league_history_path):
    games = build_games(league_history_path)
    m = [g for g in games if g["season"] == 2025 and g["phase"] == "regular"
         and g["week"] == 1 and g["away_score"] == 212.6][0]
    assert m["away_owner"] == "Buffalo Joe"
    assert m["home_owner"] == "Walter"
    assert m["winner"] == "Buffalo Joe"
    assert m["loser"] == "Walter"
    assert m["margin"] == 59.8
    assert m["tie"] is False

def test_build_games_no_unknown_owners(league_history_path):
    # Every game (all 15 seasons) resolves to a known all-time owner.
    from build.normalize import ALL_TIME_OWNERS
    games = build_games(league_history_path)
    for g in games:
        assert g["home_owner"] in ALL_TIME_OWNERS
        assert g["away_owner"] in ALL_TIME_OWNERS

def test_build_games_historical_owners_in_early_seasons(league_history_path):
    # The 3 departed owners appear in the 2011-2014 (10-team) era.
    games = build_games(league_history_path)
    early = {g["home_owner"] for g in games if g["season"] <= 2014} | \
            {g["away_owner"] for g in games if g["season"] <= 2014}
    assert {"Chris Borea", "Joe Kosich", "Tucker"} <= early

def test_season_team_names(league_history_path):
    games = build_games(league_history_path)
    names = season_team_names(games)
    assert names["2025"]["Walter"] == "Herbie Fully Loaded"
    assert names["2025"]["Matt"] == "MATTY BIG TRAPS"
