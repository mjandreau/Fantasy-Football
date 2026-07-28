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


def standings(games, season=None):
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
    rows.sort(key=lambda r: r["power_index"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["power_rank"] = i
    return rows
