"""Game-level analytics: luck, consistency, crowns, streaks, playoffs, trends,
H2H matrix, and the computed-insights engine. All derived from the tidy games
table; regular season only unless a metric says otherwise."""

from collections import defaultdict
from statistics import pstdev, mean

from build.curated import CHAMPIONS


def _weekly_scores(games):
    """{(season, week): [(owner, score), ...]} for regular-season games."""
    weeks = defaultdict(list)
    for g in games:
        if g["phase"] != "regular":
            continue
        key = (g["season"], g["week"])
        weeks[key].append((g["home_owner"], g["home_score"]))
        weeks[key].append((g["away_owner"], g["away_score"]))
    return weeks


def all_play(games):
    """Expected wins if every team played every other team each week."""
    weeks = _weekly_scores(games)
    exp = defaultdict(float)          # owner -> expected wins (scope: key later)
    exp_season = defaultdict(lambda: defaultdict(float))
    actual = defaultdict(float)
    actual_season = defaultdict(lambda: defaultdict(float))
    gp = defaultdict(int)
    gp_season = defaultdict(lambda: defaultdict(int))

    for (season, _wk), entries in weeks.items():
        n = len(entries)
        if n < 2:
            continue
        for owner, score in entries:
            beat = sum(1 for o, s in entries if o != owner and s < score)
            tied = sum(1 for o, s in entries if o != owner and s == score)
            e = (beat + 0.5 * tied) / (n - 1)
            exp[owner] += e
            exp_season[season][owner] += e
            gp[owner] += 1
            gp_season[season][owner] += 1

    for g in games:
        if g["phase"] != "regular":
            continue
        for owner, own, opp in ((g["home_owner"], g["home_score"], g["away_score"]),
                                (g["away_owner"], g["away_score"], g["home_score"])):
            w = 0.5 if g["tie"] else (1.0 if own > opp else 0.0)
            actual[owner] += w
            actual_season[g["season"]][owner] += w

    def rows(escope, ascope, gscope):
        out = []
        for owner in sorted(escope):
            out.append({"owner": owner,
                        "expected_wins": round(escope[owner], 2),
                        "actual_wins": round(ascope.get(owner, 0.0), 1),
                        "luck": round(ascope.get(owner, 0.0) - escope[owner], 2),
                        "games": gscope[owner]})
        out.sort(key=lambda r: r["luck"], reverse=True)
        return out

    return {"all_time": rows(exp, actual, gp),
            "by_season": {str(s): rows(exp_season[s], actual_season[s], gp_season[s])
                          for s in sorted(exp_season)}}


def consistency(games):
    """Mean and population stdev of weekly scores per owner."""
    scores = defaultdict(list)
    scores_season = defaultdict(lambda: defaultdict(list))
    for (season, _wk), entries in _weekly_scores(games).items():
        for owner, score in entries:
            scores[owner].append(score)
            scores_season[season][owner].append(score)

    def rows(scope):
        out = [{"owner": o, "avg": round(mean(v), 2),
                "stdev": round(pstdev(v), 2) if len(v) > 1 else 0.0,
                "games": len(v)}
               for o, v in scope.items()]
        out.sort(key=lambda r: r["stdev"], reverse=True)
        return out

    return {"all_time": rows(scores),
            "by_season": {str(s): rows(scores_season[s])
                          for s in sorted(scores_season)}}


def weekly_crowns(games):
    """Top score each regular-season week earns a crown (ties share)."""
    crowns = defaultdict(int)
    crowns_season = defaultdict(lambda: defaultdict(int))
    for (season, _wk), entries in _weekly_scores(games).items():
        top = max(s for _o, s in entries)
        for owner, score in entries:
            if score == top:
                crowns[owner] += 1
                crowns_season[season][owner] += 1

    def rows(scope):
        out = [{"owner": o, "crowns": n} for o, n in scope.items()]
        out.sort(key=lambda r: (-r["crowns"], r["owner"]))
        return out

    return {"all_time": rows(crowns),
            "by_season": {str(s): rows(crowns_season[s])
                          for s in sorted(crowns_season)}}


def streaks(games):
    """Longest win and loss streaks per owner across ALL games (ties break both)."""
    per_owner = defaultdict(list)   # owner -> [(season, week, 'W'|'L'|'T')]
    for g in sorted(games, key=lambda x: (x["season"], x["week"])):
        for owner in (g["home_owner"], g["away_owner"]):
            if g["tie"]:
                res = "T"
            else:
                res = "W" if g["winner"] == owner else "L"
            per_owner[owner].append((g["season"], g["week"], res))

    def longest(seq, want):
        best_len, best_span = 0, ("", "")
        cur_len, cur_start = 0, None
        for season, week, res in seq:
            if res == want:
                if cur_len == 0:
                    cur_start = (season, week)
                cur_len += 1
                if cur_len > best_len:
                    best_len = cur_len
                    best_span = (cur_start, (season, week))
            else:
                cur_len = 0
        if best_len == 0:
            return 0, "—"
        (s1, w1), (s2, w2) = best_span
        return best_len, f"{s1} Wk{w1} – {s2} Wk{w2}"

    out = []
    for owner, seq in per_owner.items():
        lw, wspan = longest(seq, "W")
        ll, lspan = longest(seq, "L")
        out.append({"owner": owner, "longest_win": lw, "win_span": wspan,
                    "longest_loss": ll, "loss_span": lspan})
    out.sort(key=lambda r: -r["longest_win"])
    return out


def playoff_records(games):
    """All-time playoff W-L per owner, with regular-season win% for contrast."""
    pw = defaultdict(int)
    pl = defaultdict(int)
    rw = defaultdict(float)
    rg = defaultdict(int)
    owners = set()
    for g in games:
        for owner, own, opp in ((g["home_owner"], g["home_score"], g["away_score"]),
                                (g["away_owner"], g["away_score"], g["home_score"])):
            owners.add(owner)
            if g["phase"] == "playoff":
                if not g["tie"]:
                    if own > opp:
                        pw[owner] += 1
                    else:
                        pl[owner] += 1
            else:
                rg[owner] += 1
                rw[owner] += 0.5 if g["tie"] else (1.0 if own > opp else 0.0)
    out = []
    for owner in sorted(owners):
        games_p = pw[owner] + pl[owner]
        out.append({"owner": owner, "wins": pw[owner], "losses": pl[owner],
                    "playoff_win_pct": round(pw[owner] / games_p, 3) if games_p else 0.0,
                    "reg_win_pct": round(rw[owner] / rg[owner], 3) if rg[owner] else 0.0})
    out.sort(key=lambda r: -r["playoff_win_pct"])
    return out


def season_trends(games):
    """League scoring environment per season (all phases)."""
    per = defaultdict(list)
    for g in games:
        per[g["season"]].append(g["home_score"])
        per[g["season"]].append(g["away_score"])
    return [{"season": s, "avg_score": round(mean(v), 1),
             "max_score": round(max(v), 1), "min_score": round(min(v), 1)}
            for s, v in sorted(per.items())]


def h2h_matrix(games):
    """Win% grid for every owner pair (all phases; ties = 0.5)."""
    wins = defaultdict(float)
    count = defaultdict(int)
    owners = set()
    for g in games:
        a, b = sorted([g["home_owner"], g["away_owner"]])
        owners.update((a, b))
        key = f"{a}|{b}"
        count[key] += 1
        if g["tie"]:
            wins[key] += 0.5
        elif g["winner"] == a:
            wins[key] += 1.0
    cells = {k: {"a_pct": round(wins[k] / count[k], 3), "games": count[k]}
             for k in count}
    return {"owners": sorted(owners), "cells": cells}


def _mk(id_, tab, icon, title, text):
    return {"id": id_, "tab": tab, "icon": icon, "title": title, "text": text}


def build_insights(games):
    """Deterministic computed findings. Owner-specific findings are also
    duplicated onto that owner's deep-dive tab (tab = 'owner:<name>')."""
    ap = all_play(games)
    cons = consistency(games)
    cr = weekly_crowns(games)
    st = streaks(games)
    pr = playoff_records(games)
    tr = season_trends(games)

    ins = []

    def add(id_, tab, icon, title, text, owner=None):
        ins.append(_mk(id_, tab, icon, title, text))
        if owner:
            ins.append(_mk(id_ + ":own", f"owner:{owner}", icon, title, text))

    # Dynasty
    titles = defaultdict(list)
    for season, rec in CHAMPIONS.items():
        titles[rec["champion"]].append(season)
    top_owner, top_years = max(titles.items(), key=lambda kv: len(kv[1]))
    add("dynasty", "overview", "👑", f"{top_owner} is the dynasty",
        f"{top_owner} owns a league-best {len(top_years)} championships "
        f"({', '.join(sorted(top_years))}).", owner=top_owner)

    # Luckiest / unluckiest single seasons (min 10 games)
    season_rows = [(s, r) for s, rows in ap["by_season"].items()
                   for r in rows if r["games"] >= 10]
    lucky_s, lucky = max(season_rows, key=lambda x: x[1]["luck"])
    unlucky_s, unlucky = min(season_rows, key=lambda x: x[1]["luck"])
    add("lucky-season", "overview", "🍀",
        f"Luckiest season ever: {lucky['owner']} ({lucky_s})",
        f"{lucky['owner']} won {lucky['actual_wins']:g} games in {lucky_s} but "
        f"deserved only {lucky['expected_wins']:g} on all-play — a +{lucky['luck']:g} "
        "schedule gift, the largest in league history.", owner=lucky["owner"])
    add("unlucky-season", "analytics", "🪦",
        f"Unluckiest season ever: {unlucky['owner']} ({unlucky_s})",
        f"{unlucky['owner']} played well enough for {unlucky['expected_wins']:g} wins "
        f"in {unlucky_s} but the schedule handed them just {unlucky['actual_wins']:g} "
        f"({unlucky['luck']:g} luck).", owner=unlucky["owner"])

    # Boom/bust and steadiest (min 40 games)
    vol = [r for r in cons["all_time"] if r["games"] >= 40]
    boom = max(vol, key=lambda r: r["stdev"])
    steady = min(vol, key=lambda r: r["stdev"])
    add("boom-bust", "analytics", "🎢", f"{boom['owner']} is the rollercoaster",
        f"Highest weekly volatility in the league: ±{boom['stdev']:g} points around "
        f"a {boom['avg']:g} average. Boom or bust, never boring.", owner=boom["owner"])
    add("steady", "analytics", "🧊", f"{steady['owner']} is the metronome",
        f"Steadiest scorer in league history: just ±{steady['stdev']:g} points of "
        f"weekly variation on a {steady['avg']:g} average.", owner=steady["owner"])

    # Crown king
    ck = cr["all_time"][0]
    add("crown-king", "overview", "👑", f"Weekly crown king: {ck['owner']}",
        f"{ck['owner']} has posted the league's top weekly score {ck['crowns']} times "
        "— more than anyone else.", owner=ck["owner"])

    # Longest win streak
    ws = max(st, key=lambda r: r["longest_win"])
    add("win-streak", "overview", "🔥",
        f"Longest win streak: {ws['owner']} ({ws['longest_win']} straight)",
        f"{ws['owner']} rattled off {ws['longest_win']} consecutive wins "
        f"({ws['win_span']}) — the longest run in league history.", owner=ws["owner"])

    # Playoff clutch / choker (min 10 playoff games)
    qual = [r for r in pr if r["wins"] + r["losses"] >= 10]
    if qual:
        clutch = max(qual, key=lambda r: r["playoff_win_pct"] - r["reg_win_pct"])
        choker = min(qual, key=lambda r: r["playoff_win_pct"] - r["reg_win_pct"])
        add("clutch", "analytics", "💎", f"Playoff riser: {clutch['owner']}",
            f"{clutch['owner']} lifts their game in the bracket: "
            f"{clutch['playoff_win_pct']:.0%} playoff win rate vs "
            f"{clutch['reg_win_pct']:.0%} in the regular season.", owner=clutch["owner"])
        add("choker", "analytics", "🥶", f"Playoff fader: {choker['owner']}",
            f"{choker['owner']} drops from {choker['reg_win_pct']:.0%} in the regular "
            f"season to {choker['playoff_win_pct']:.0%} when the bracket starts.",
            owner=choker["owner"])

    # Heartbreak: most losses by < 5
    hb = defaultdict(int)
    for g in games:
        if not g["tie"] and g["margin"] < 5:
            hb[g["loser"]] += 1
    if hb:
        hb_owner, hb_n = max(hb.items(), key=lambda kv: kv[1])
        add("heartbreak", "analytics", "💔", f"Heartbreak leader: {hb_owner}",
            f"{hb_owner} has lost {hb_n} games by fewer than 5 points — "
            "the most agonizing near-misses in the league.", owner=hb_owner)

    # Scoring inflation
    first, last = tr[0], tr[-1]
    diff = last["avg_score"] - first["avg_score"]
    direction = "up" if diff >= 0 else "down"
    add("inflation", "analytics", "📈", "The scoring era shift",
        f"League scoring has gone {direction} from a {first['avg_score']:g}-point "
        f"average in {first['season']} to {last['avg_score']:g} in {last['season']} "
        f"({diff:+g} points per team-week).")

    return ins


def build_analytics(games):
    return {"all_play": all_play(games),
            "consistency": consistency(games),
            "crowns": weekly_crowns(games),
            "streaks": streaks(games),
            "playoff_records": playoff_records(games),
            "season_trends": season_trends(games),
            "h2h_matrix": h2h_matrix(games)}
