from collections import Counter, defaultdict
from build.loaders import parse_league_history
from build.normalize import owner_from_manager, clean_team_name


def build_games(history_path):
    raw = parse_league_history(history_path)
    games = []
    for r in raw:
        ho = owner_from_manager(r["home_manager"])
        ao = owner_from_manager(r["away_manager"])
        hs, as_ = r["home_score"], r["away_score"]
        tie = hs == as_
        if tie:
            winner = loser = None
        elif hs > as_:
            winner, loser = ho, ao
        else:
            winner, loser = ao, ho
        games.append({
            "season": r["season"], "week": r["week"], "phase": r["phase"],
            "playoff_round": r["playoff_round"],
            "home_owner": ho, "home_team": clean_team_name(r["home_team_raw"]),
            "home_score": hs,
            "away_owner": ao, "away_team": clean_team_name(r["away_team_raw"]),
            "away_score": as_,
            "winner": winner, "loser": loser,
            "margin": round(abs(hs - as_), 1), "tie": tie,
        })
    return games


def season_team_names(games):
    counts = defaultdict(lambda: defaultdict(Counter))
    for g in games:
        counts[str(g["season"])][g["home_owner"]][g["home_team"]] += 1
        counts[str(g["season"])][g["away_owner"]][g["away_team"]] += 1
    out = {}
    for season, owners in counts.items():
        out[season] = {owner: c.most_common(1)[0][0] for owner, c in owners.items()}
    return out
