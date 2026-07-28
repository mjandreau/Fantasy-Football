from build.games import build_games
from build.loaders import parse_gridiron
from build.reconcile import flag_conflicts, reconciliation_report

def test_flag_conflicts_2019_clean_2021_dirty(league_history_path, gridiron_path):
    games = build_games(league_history_path)
    grid = parse_gridiron(gridiron_path)
    flagged = flag_conflicts(games, grid)
    assert all("gridiron_conflict" in g for g in flagged)
    def conflicts(season):
        return sum(1 for g in flagged
                   if g["season"] == season and g["phase"] == "regular" and g["gridiron_conflict"])
    assert conflicts(2019) == 0
    assert conflicts(2021) >= 20   # cross-reference found ~34
    # playoffs never flagged
    assert all(not g["gridiron_conflict"] for g in flagged if g["phase"] == "playoff")

def test_reconciliation_report_is_markdown(league_history_path, gridiron_path):
    games = flag_conflicts(build_games(league_history_path), parse_gridiron(gridiron_path))
    report = reconciliation_report(games)
    assert report.startswith("#")
    assert "2021" in report
