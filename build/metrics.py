from collections import defaultdict


def _regular(games, season=None):
    return [g for g in games
            if g["phase"] == "regular" and (season is None or g["season"] == season)]


def _accumulate(games):
    acc = defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0, "pf": 0.0,
                               "pa": 0.0, "games": 0, "results": []})
    for g in games:
        for owner, own, opp in ((g["home_owner"], g["home_score"], g["away_score"]),
                                (g["away_owner"], g["away_score"], g["home_score"])):
            a = acc[owner]
            a["pf"] += own
            a["pa"] += opp
            a["games"] += 1
            if g["tie"]:
                a["ties"] += 1
                a["results"].append("T")
            elif own > opp:
                a["wins"] += 1
                a["results"].append("W")
            else:
                a["losses"] += 1
                a["results"].append("L")
    return acc


def standings(games, season=None, min_games=40):
    acc = _accumulate(_regular(games, season))
    rows = []
    for owner, a in acc.items():
        gp = a["games"]
        avg = a["pf"] / gp if gp else 0.0
        decided = a["wins"] + a["losses"] + a["ties"]
        win_pct = (a["wins"] + 0.5 * a["ties"]) / decided if decided else 0.0
        rows.append({"owner": owner, "wins": a["wins"], "losses": a["losses"],
                     "ties": a["ties"], "win_pct": round(win_pct, 4),
                     "pf": round(a["pf"], 1), "pa": round(a["pa"], 1),
                     "games": gp, "avg_score": round(avg, 2)})
    league_avg = sum(r["avg_score"] for r in rows) / len(rows) if rows else 1.0
    for r in rows:
        pi = ((r["avg_score"] / league_avg) * 80 + r["win_pct"] * 100) * (1 / 7) if league_avg else 0.0
        r["power_index"] = round(pi, 4)
    # All-time (season is None) applies the games qualifier so tiny-sample
    # historical owners don't top the leaderboard; per-season ranks everyone.
    apply_qualifier = season is None
    for r in rows:
        r["qualified"] = (r["games"] >= min_games) if apply_qualifier else True
    rows.sort(key=lambda r: r["power_index"], reverse=True)
    rank = 0
    for r in rows:
        if r["qualified"]:
            rank += 1
            r["power_rank"] = rank
        else:
            r["power_rank"] = None
    # qualified first (by rank), then unqualified by Power Index desc
    rows.sort(key=lambda r: (r["power_rank"] is None,
                             r["power_rank"] if r["power_rank"] is not None else -r["power_index"]))
    return rows


def head_to_head(games):
    out = {}
    for g in games:
        a, b = sorted([g["home_owner"], g["away_owner"]])
        key = f"{a}|{b}"
        rec = out.setdefault(key, {"a": a, "b": b, "a_wins": 0, "b_wins": 0,
                                   "ties": 0, "games": 0, "a_pts": 0.0, "b_pts": 0.0,
                                   "meetings": []})
        a_score = g["home_score"] if g["home_owner"] == a else g["away_score"]
        b_score = g["home_score"] if g["home_owner"] == b else g["away_score"]
        rec["games"] += 1
        rec["a_pts"] += a_score
        rec["b_pts"] += b_score
        if g["tie"]:
            rec["ties"] += 1
            winner = None
        elif a_score > b_score:
            rec["a_wins"] += 1
            winner = a
        else:
            rec["b_wins"] += 1
            winner = b
        rec["meetings"].append({"season": g["season"], "week": g["week"],
                                "phase": g["phase"], "a_score": a_score,
                                "b_score": b_score, "winner": winner})
    for rec in out.values():
        n = rec["games"]
        rec["a_avg"] = round(rec.pop("a_pts") / n, 1) if n else 0.0
        rec["b_avg"] = round(rec.pop("b_pts") / n, 1) if n else 0.0
    return out


def _sides(g):
    return [(g["home_owner"], g["home_score"], g["away_owner"], g["away_score"]),
            (g["away_owner"], g["away_score"], g["home_owner"], g["home_score"])]


def record_book(games, limit=15):
    scores, combined, margins, ties = [], [], [], []
    for g in games:
        base = {"season": g["season"], "week": g["week"], "phase": g["phase"]}
        for owner, s, opp, os_ in _sides(g):
            scores.append({**base, "owner": owner, "score": s, "opponent": opp})
        combined.append({**base, "total": round(g["home_score"] + g["away_score"], 1),
                         "home_owner": g["home_owner"], "away_owner": g["away_owner"]})
        if g["tie"]:
            ties.append({**base, "owner_a": g["home_owner"], "owner_b": g["away_owner"],
                         "score": g["home_score"]})
        else:
            margins.append({**base, "winner": g["winner"], "loser": g["loser"],
                            "margin": g["margin"],
                            "win_score": max(g["home_score"], g["away_score"]),
                            "lose_score": min(g["home_score"], g["away_score"])})
    highest = sorted(scores, key=lambda x: x["score"], reverse=True)[:limit]
    lowest = sorted(scores, key=lambda x: x["score"])[:limit]
    biggest = sorted(margins, key=lambda x: x["margin"], reverse=True)[:limit]
    closest = sorted(margins, key=lambda x: x["margin"])[:limit]
    hi_comb = sorted(combined, key=lambda x: x["total"], reverse=True)[:limit]
    return {"highest_scores": highest, "lowest_scores": lowest,
            "biggest_margins": biggest, "closest_games": closest,
            "highest_combined": hi_comb, "ties": ties[:limit]}


def owner_careers(games, champions):
    owners = sorted({g["home_owner"] for g in games} | {g["away_owner"] for g in games})
    titles = defaultdict(list)
    lasts = defaultdict(list)
    for season, rec in champions.items():
        titles[rec["champion"]].append(int(season))
        lasts[rec["last_place"]].append(int(season))
    seasons_played = defaultdict(set)
    for g in games:
        seasons_played[g["home_owner"]].add(g["season"])
        seasons_played[g["away_owner"]].add(g["season"])

    # best/worst single games and top rival per owner
    best = {}
    worst = {}
    rival_losses = defaultdict(lambda: defaultdict(int))
    for g in games:
        for owner, s, opp, os_ in _sides(g):
            entry = {"season": g["season"], "week": g["week"], "phase": g["phase"],
                     "score": s, "opponent": opp}
            if owner not in best or s > best[owner]["score"]:
                best[owner] = entry
            if owner not in worst or s < worst[owner]["score"]:
                worst[owner] = entry
        if not g["tie"]:
            rival_losses[g["loser"]][g["winner"]] += 1

    careers = {}
    for owner in owners:
        # per-season finish from that season's standings
        season_rows = []
        for season in sorted(seasons_played[owner]):
            srows = standings(games, season=season)
            r = next((x for x in srows if x["owner"] == owner), None)
            if r is None:
                continue
            season_rows.append({"season": season, "rank": r["power_rank"],
                                "wins": r["wins"], "losses": r["losses"],
                                "avg_score": r["avg_score"],
                                "made_playoffs": any(
                                    x["season"] == season and x["phase"] == "playoff"
                                    and owner in (x["home_owner"], x["away_owner"])
                                    for x in games)})
        rivals = rival_losses[owner]
        top_rival = max(rivals, key=rivals.get) if rivals else None
        careers[owner] = {"titles": sorted(titles[owner]),
                          "last_places": sorted(lasts[owner]),
                          "seasons": season_rows,
                          "best_game": best.get(owner),
                          "worst_game": worst.get(owner),
                          "top_rival": top_rival}
    return careers
