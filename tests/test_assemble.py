from build.assemble import assemble

def test_assemble_top_level_keys(league_history_path, gridiron_path):
    data, report = assemble(league_history_path, gridiron_path, generated="2026-07-28")
    for k in ("meta", "games", "champions", "team_names", "all_time_standings",
              "season_standings", "head_to_head", "record_book", "owner_careers"):
        assert k in data
    assert data["meta"]["total_games"] == 1399
    assert data["meta"]["seasons"] == list(range(2011, 2026))
    assert len(data["all_time_standings"]) == 15
    assert len(data["meta"]["active_owners"]) == 12
    assert set(data["season_standings"].keys()) == {str(y) for y in range(2011, 2026)}
    assert report.startswith("#")

def test_assemble_is_json_serializable(league_history_path, gridiron_path):
    import json
    data, _ = assemble(league_history_path, gridiron_path, generated="2026-07-28")
    json.dumps(data)  # must not raise
