"""Dominance: how far above the league a team actually was.

Win-loss alone is noisy in a 13-14 game fantasy season -- the schedule decides
too much of it. Every measure here is built to survive that, and to survive the
league's own drift (10 teams to 12, scoring eras that move the whole league at
once, 8 playoff spots down to 6):

  * scoring is expressed as **z**, standard deviations above that season's
    league mean, so a 2011 team and a 2025 team are comparable and the
    pre-2018 workbook rounding cancels out;
  * **all-play** asks what the record would have been against everyone every
    week, which strips the schedule out entirely;
  * point differential and margins run over every game, playoffs included.

DOM combines them with published weights. The weights are opinions -- they live
in WEIGHTS, ship inside the payload, and every input is a column of its own on
the dashboard, so anyone who dislikes the blend can sort by the raw number.
"""

from collections import defaultdict
from statistics import mean, pstdev

from build.analytics import all_play
from build.games import season_team_names
from build.normalize import ACTIVE_OWNERS

# Season DOM. z and all-play carry the most weight because they are the two
# schedule-independent measures; the title bonus is deliberately smaller than
# a strong z so a lucky champion cannot outrank a juggernaut.
WEIGHTS = {
    "z": 1.6,             # per standard deviation of scoring above the league
    "all_play": 3.0,      # per unit of (all-play win% - .500), doubled
    "win_pct": 2.0,       # per unit of (win% - .500), doubled
    "title": 2.0,         # flat bonus for the ring
    "playoff_win": 0.25,  # per playoff win
}

# Career DOM. Titles are worth more here (they accumulate), and playoff win%
# earns a term of its own -- over 15 seasons it stops being noise.
FRANCHISE_WEIGHTS = {
    "avg_z": 1.5,
    "all_play": 4.0,
    "win_pct": 2.0,
    "title": 0.45,
    "playoff_pct": 1.5,
}

FORMULA_TEXT = (
    "DOM = 1.6·z + 3.0·(all-play% − .500)×2 + "
    "2.0·(win% − .500)×2 + 2.0·(title) + 0.25·(playoff wins)"
)

DYNASTY_LENGTHS = (3, 5)
NEVER_WON_LIMIT = 10


def _sides(game):
    """((owner, own score, opponent, opponent score), ...) for both teams."""
    return ((game["home_owner"], game["home_score"],
             game["away_owner"], game["away_score"]),
            (game["away_owner"], game["away_score"],
             game["home_owner"], game["home_score"]))


def _blank():
    return {"wins": 0, "losses": 0, "ties": 0, "pf": 0.0, "games": 0,
            "playoff_wins": 0, "playoff_losses": 0,
            "point_diff": 0.0, "all_games": 0, "worst_loss": 0.0}


def _tally(games):
    """(season, owner) -> raw counters. Regular-season W-L and points-for stay
    separate from the playoff record; differential spans every game played."""
    acc = defaultdict(_blank)
    for g in games:
        regular = g["phase"] == "regular"
        for owner, own, _opp_owner, opp in _sides(g):
            rec = acc[(g["season"], owner)]
            margin = own - opp
            rec["point_diff"] += margin
            rec["all_games"] += 1
            rec["worst_loss"] = min(rec["worst_loss"], margin)
            if regular:
                rec["pf"] += own
                rec["games"] += 1
                if g["tie"]:
                    rec["ties"] += 1
                elif g["winner"] == owner:
                    rec["wins"] += 1
                else:
                    rec["losses"] += 1
            elif not g["tie"]:
                if g["winner"] == owner:
                    rec["playoff_wins"] += 1
                else:
                    rec["playoff_losses"] += 1
    return acc


def season_dominance(games, champions):
    """One row per team-season, with DOM and every input that feeds it."""
    acc = _tally(games)
    names = season_team_names(games)
    ap = all_play(games)["by_season"]

    ppg = {key: rec["pf"] / rec["games"] for key, rec in acc.items() if rec["games"]}
    by_season = defaultdict(list)
    for (season, owner) in acc:
        by_season[season].append(owner)

    rows = []
    for season, owners in by_season.items():
        vals = [ppg[(season, o)] for o in owners]
        mu, sigma = mean(vals), pstdev(vals)
        exp = {r["owner"]: r for r in ap.get(str(season), [])}
        champ = champions.get(str(season), {}).get("champion")
        for owner in owners:
            rec = acc[(season, owner)]
            decided = rec["wins"] + rec["losses"] + rec["ties"]
            win_pct = (rec["wins"] + 0.5 * rec["ties"]) / decided if decided else 0.0
            z = (ppg[(season, owner)] - mu) / sigma if sigma else 0.0
            e = exp.get(owner)
            ap_pct = (e["expected_wins"] / e["games"]) if e and e["games"] else 0.0
            title = owner == champ
            dom = (WEIGHTS["z"] * z
                   + WEIGHTS["all_play"] * (ap_pct - 0.5) * 2
                   + WEIGHTS["win_pct"] * (win_pct - 0.5) * 2
                   + WEIGHTS["title"] * (1 if title else 0)
                   + WEIGHTS["playoff_win"] * rec["playoff_wins"])
            rows.append({
                "season": season,
                "owner": owner,
                "team": names[str(season)][owner],
                "wins": rec["wins"], "losses": rec["losses"], "ties": rec["ties"],
                "win_pct": round(win_pct, 4),
                "ppg": round(ppg[(season, owner)], 2),
                "z": round(z, 3),
                "all_play_pct": round(ap_pct, 4),
                "expected_wins": e["expected_wins"] if e else 0.0,
                "playoff_wins": rec["playoff_wins"],
                "playoff_losses": rec["playoff_losses"],
                "point_diff": round(rec["point_diff"], 1),
                "avg_margin": round(rec["point_diff"] / rec["all_games"], 2),
                "worst_loss": round(rec["worst_loss"], 1),
                "title": title,
                "dom": round(dom, 3),
            })
    rows.sort(key=lambda r: (-r["dom"], r["season"], r["owner"]))
    return rows


def franchise_dominance(games, champions):
    """Career rollup per owner. Departed owners are kept but flagged inactive
    so the dashboard can pin them below the table rather than drop them."""
    seasons = season_dominance(games, champions)
    ap = {r["owner"]: r for r in all_play(games)["all_time"]}
    active = set(ACTIVE_OWNERS)

    titles = defaultdict(list)
    for season, rec in champions.items():
        titles[rec["champion"]].append(int(season))

    grouped = defaultdict(list)
    for r in seasons:
        grouped[r["owner"]].append(r)

    rows = []
    for owner, rs in grouped.items():
        wins = sum(r["wins"] for r in rs)
        losses = sum(r["losses"] for r in rs)
        ties = sum(r["ties"] for r in rs)
        decided = wins + losses + ties
        win_pct = (wins + 0.5 * ties) / decided if decided else 0.0
        pw = sum(r["playoff_wins"] for r in rs)
        pl = sum(r["playoff_losses"] for r in rs)
        po_pct = pw / (pw + pl) if (pw + pl) else 0.0
        e = ap.get(owner)
        ap_pct = (e["expected_wins"] / e["games"]) if e and e["games"] else 0.0
        avg_z = mean(r["z"] for r in rs)
        won = sorted(titles.get(owner, []))
        dom = (FRANCHISE_WEIGHTS["avg_z"] * avg_z
               + FRANCHISE_WEIGHTS["all_play"] * (ap_pct - 0.5)
               + FRANCHISE_WEIGHTS["win_pct"] * (win_pct - 0.5)
               + FRANCHISE_WEIGHTS["title"] * len(won)
               + FRANCHISE_WEIGHTS["playoff_pct"] * (po_pct - 0.5))
        rows.append({
            "owner": owner,
            "seasons": len(rs),
            "wins": wins, "losses": losses, "ties": ties,
            "win_pct": round(win_pct, 4),
            "avg_z": round(avg_z, 3),
            "all_play_pct": round(ap_pct, 4),
            "playoff_wins": pw, "playoff_losses": pl,
            "playoff_pct": round(po_pct, 3),
            "point_diff": round(sum(r["point_diff"] for r in rs), 1),
            "best_season": max(rs, key=lambda r: r["dom"])["season"],
            "best_dom": max(r["dom"] for r in rs),
            "titles": len(won),
            "title_years": won,
            "active": owner in active,
            "dom": round(dom, 3),
        })
    rows.sort(key=lambda r: -r["dom"])
    return rows


def dynasty_windows(games, champions, length=5, limit=10):
    """Best consecutive `length`-season stretches. A window only counts if the
    owner actually played all of its seasons -- nobody gets credit for a gap."""
    seasons = season_dominance(games, champions)
    by_owner = defaultdict(dict)
    for r in seasons:
        by_owner[r["owner"]][r["season"]] = r

    windows = []
    for owner, years in by_owner.items():
        played = sorted(years)
        for start in played:
            span = list(range(start, start + length))
            if not all(y in years for y in span):
                continue
            rs = [years[y] for y in span]
            windows.append({
                "owner": owner,
                "start": span[0], "end": span[-1],
                "seasons": span,
                "length": length,
                "wins": sum(r["wins"] for r in rs),
                "losses": sum(r["losses"] for r in rs),
                "ties": sum(r["ties"] for r in rs),
                "titles": sum(1 for r in rs if r["title"]),
                "title_years": [r["season"] for r in rs if r["title"]],
                "avg_z": round(mean(r["z"] for r in rs), 3),
                "playoff_wins": sum(r["playoff_wins"] for r in rs),
                "point_diff": round(sum(r["point_diff"] for r in rs), 1),
                "dom": round(sum(r["dom"] for r in rs), 3),
            })
    windows.sort(key=lambda w: (-w["titles"], -w["dom"]))
    return windows[:limit]


def championship_bracket(games, season, champion):
    """The title-bracket games for one season.

    The playoff sheets interleave the championship bracket with consolation
    games, so the bracket is traced backwards from the champion: the final is
    the champion's last playoff game, and a round is in the bracket if one of
    its teams turns up in a later bracket game. Membership never reads
    `winner`, which keeps the 2015 semifinal -- a tie decided on seeding --
    attached to the team that actually advanced.
    """
    po = [g for g in games
          if g["season"] == season and g["phase"] != "regular"
          and g["playoff_round"] is not None]
    champ_games = [g for g in po
                   if champion in (g["home_owner"], g["away_owner"])]
    if not champ_games:
        return []
    final = max(champ_games, key=lambda g: (g["playoff_round"], g["week"]))
    bracket = [final]
    seen = {final["home_owner"], final["away_owner"]}
    earlier = sorted({g["playoff_round"] for g in po
                      if g["playoff_round"] < final["playoff_round"]}, reverse=True)
    for rnd in earlier:
        matches = [g for g in po if g["playoff_round"] == rnd
                   and ({g["home_owner"], g["away_owner"]} & seen)]
        bracket.extend(matches)
        for g in matches:
            seen |= {g["home_owner"], g["away_owner"]}
    return bracket


def _round_label(game, final_round):
    depth = final_round - game["playoff_round"]
    return {0: "Championship", 1: "Semifinal", 2: "Quarterfinal"}.get(
        depth, f"Round {game['playoff_round']}")


def never_won(games, champions, limit=NEVER_WON_LIMIT):
    """The best seasons that ended without a ring, and how each one ended."""
    rows = [dict(r) for r in season_dominance(games, champions) if not r["title"]]
    brackets = {}
    for r in rows[:limit]:
        season = r["season"]
        if season not in brackets:
            champ = champions.get(str(season), {}).get("champion")
            bracket = championship_bracket(games, season, champ)
            final_round = max((g["playoff_round"] for g in bracket), default=None)
            brackets[season] = (bracket, final_round)
        bracket, final_round = brackets[season]
        mine = [g for g in bracket
                if r["owner"] in (g["home_owner"], g["away_owner"])]
        r.update({"eliminated_by": None, "elimination_score": None,
                  "elimination_opp_score": None, "elimination_round": None,
                  "elimination_week": None})
        if mine:
            last = max(mine, key=lambda g: (g["playoff_round"], g["week"]))
            for owner, own, opp_owner, opp in _sides(last):
                if owner == r["owner"]:
                    r.update({"eliminated_by": opp_owner,
                              "elimination_score": own,
                              "elimination_opp_score": opp,
                              "elimination_round": _round_label(last, final_round),
                              "elimination_week": last["week"]})
    return rows[:limit]


def build_dominance(games, champions):
    return {
        "seasons": season_dominance(games, champions),
        "franchises": franchise_dominance(games, champions),
        "dynasties": {str(n): dynasty_windows(games, champions, length=n)
                      for n in DYNASTY_LENGTHS},
        "never_won": never_won(games, champions),
        "formula": {"weights": WEIGHTS,
                    "franchise_weights": FRANCHISE_WEIGHTS,
                    "text": FORMULA_TEXT},
    }
