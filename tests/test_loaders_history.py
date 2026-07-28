from build.loaders import parse_league_history

def test_parse_history_counts_and_shape(league_history_path):
    games = parse_league_history(league_history_path)
    # Total games across all 15 sheets (verified via cross-reference)
    assert len(games) == 1360
    # Every game has both scores as floats and a season in range
    for g in games:
        assert 2011 <= g["season"] <= 2025
        assert isinstance(g["home_score"], float)
        assert isinstance(g["away_score"], float)
        assert g["phase"] in ("regular", "playoff")

def test_parse_history_regular_vs_playoff(league_history_path):
    games = parse_league_history(league_history_path)
    reg = [g for g in games if g["phase"] == "regular"]
    ply = [g for g in games if g["phase"] == "playoff"]
    # 2025 must be complete (froze in Gridiron, complete here)
    s25 = [g for g in games if g["season"] == 2025]
    assert len(s25) == 101
    # Playoffs are labeled rounds 1-3
    assert {g["playoff_round"] for g in ply} == {1, 2, 3}
    assert all(g["playoff_round"] is None for g in reg)

def test_parse_history_known_game(league_history_path):
    games = parse_league_history(league_history_path)
    # 2025 Week 1: Fields and Streams (Kaszubowski) 212.6 vs Herbie Fully Loaded (Walter) 152.8
    wk1 = [g for g in games if g["season"] == 2025 and g["phase"] == "regular" and g["week"] == 1]
    match = [g for g in wk1 if g["away_score"] == 212.6 and g["home_score"] == 152.8]
    assert len(match) == 1
    assert "Kaszubowski" in match[0]["away_manager"]
    assert match[0]["home_team_raw"].startswith("Herbie Fully Loaded")
