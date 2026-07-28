from build.games import build_games, season_team_names
from build.loaders import parse_gridiron
from build.reconcile import flag_conflicts, reconciliation_report
from build.metrics import standings, head_to_head, record_book, owner_careers
from build.curated import CHAMPIONS, validate_curated
from build.normalize import ALL_TIME_OWNERS, ACTIVE_OWNERS


def assemble(history_path, gridiron_path, generated):
    validate_curated(ALL_TIME_OWNERS)
    games = build_games(history_path)
    grid = parse_gridiron(gridiron_path)
    games = flag_conflicts(games, grid)
    report = reconciliation_report(games)

    seasons = sorted({g["season"] for g in games})
    data = {
        "meta": {"seasons": seasons, "owners": ALL_TIME_OWNERS,
                 "active_owners": ACTIVE_OWNERS,
                 "total_games": len(games), "generated": generated},
        "games": games,
        "champions": CHAMPIONS,
        "team_names": season_team_names(games),
        "all_time_standings": standings(games),
        "season_standings": {str(s): standings(games, season=s) for s in seasons},
        "head_to_head": head_to_head(games),
        "record_book": record_book(games),
        "owner_careers": owner_careers(games, CHAMPIONS),
    }
    return data, report
