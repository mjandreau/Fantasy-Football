"""Week-by-week playoff probabilities, exact clinch math and schedule luck.

The curve for week N reflects only weeks 1..N. Team strength comes from
build/scoring.py, which is never shown a later week, so point-in-time
correctness is structural rather than a filter that could be mis-applied.

Monte Carlo never decides a settled question: a bound argument marks teams
mathematically in or out first, and those read exactly 1.0 or 0.0.

Seeding is record then points-for -- verified by replaying all 15 seasons and
matching ESPN's recorded standings for every team -- which is why the simulator
carries simulated point totals rather than just win counts.
"""

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from build.scoring import (FITTED_LAMBDA, detect_granularity, estimate,
                           point_in_time, team_scores)

N_SIMS = 10000
SEED = 20260817


def season_format(espn_dir, season):
    """{"reg_weeks", "playoff_spots"} for one season, read from the ESPN cache.

    The league has run 8 playoff spots and 6, 13 regular weeks and 14, with the
    field growing from 10 teams to 12 in 2015. None of it may be hardcoded.
    """
    path = Path(espn_dir) / f"settings_{season}.json"
    blob = json.loads(path.read_text(encoding="utf-8"))
    return {"reg_weeks": blob["reg_season_weeks"],
            "playoff_spots": blob["playoff_teams"]}


def owners_in(games, season):
    out = set()
    for g in games:
        if g["season"] == season and g["phase"] == "regular":
            out.add(g["home_owner"])
            out.add(g["away_owner"])
    return sorted(out)


def standings_at(games, season, through_week):
    """Regular-season record and points-for after `through_week` games."""
    acc = {o: {"wins": 0, "losses": 0, "ties": 0, "pf": 0.0, "played": 0}
           for o in owners_in(games, season)}
    for g in games:
        if g["season"] != season or g["phase"] != "regular" or g["week"] > through_week:
            continue
        for owner, own in ((g["home_owner"], g["home_score"]),
                           (g["away_owner"], g["away_score"])):
            rec = acc[owner]
            rec["pf"] += own
            rec["played"] += 1
            if g["tie"]:
                rec["ties"] += 1
            elif g["winner"] == owner:
                rec["wins"] += 1
            else:
                rec["losses"] += 1
    for rec in acc.values():
        rec["points"] = rec["wins"] + 0.5 * rec["ties"]
        rec["pf"] = round(rec["pf"], 1)
    return acc


def seed_order(standings):
    """Owners ordered by record then points-for -- the league's actual tiebreak."""
    return sorted(standings, key=lambda o: (-standings[o]["points"], -standings[o]["pf"]))


def remaining_matchups(games, season, after_week, reg_weeks):
    """[(week, home, away)] still to be played, from the recorded schedule."""
    out = []
    for g in games:
        if g["season"] != season or g["phase"] != "regular":
            continue
        if after_week < g["week"] <= reg_weeks:
            out.append((g["week"], g["home_owner"], g["away_owner"]))
    return sorted(out)


def clinch_status(standings, remaining, spots):
    """'clinched' / 'eliminated' / 'alive' per owner, by exact bound argument.

    A team's floor is its current points; points cannot be lost. A rival's
    ceiling is its points plus its remaining games.

    Deliberately CONSERVATIVE about ties, because points-for breaks them and the
    bound argument knows nothing about points-for: a rival level on record is
    treated as able to pass us, and only a strictly-higher floor counts as
    guaranteed ahead. So the answer is never "clinched" while a tiebreak could
    still go against the team -- those cases fall through to the simulation,
    which resolves them with simulated points-for.
    """
    left = defaultdict(int)
    for _wk, home, away in remaining:
        left[home] += 1
        left[away] += 1

    status = {}
    for owner, rec in standings.items():
        floor = rec["points"]
        ceiling = rec["points"] + left[owner]
        can_pass = sum(1 for other, orec in standings.items()
                       if other != owner and orec["points"] + left[other] >= floor)
        surely_ahead = sum(1 for other, orec in standings.items()
                           if other != owner and orec["points"] > ceiling)
        if can_pass < spots:
            status[owner] = "clinched"
        elif surely_ahead >= spots:
            status[owner] = "eliminated"
        else:
            status[owner] = "alive"
    return status


def simulate(owners, standings, remaining, mu, sigma, spots,
             granularity=0.1, n_sims=N_SIMS, rng=None):
    """Monte Carlo the rest of the schedule; return playoff odds and seed spread.

    Scores are drawn per team per week and rounded to the season's actual
    precision, so ties arise from the same mechanism that produces them in real
    life rather than from a fitted tie parameter.
    """
    rng = rng or np.random.default_rng(SEED)
    idx = {o: i for i, o in enumerate(owners)}
    n_teams = len(owners)

    weeks = sorted({wk for wk, _h, _a in remaining})
    week_pos = {wk: i for i, wk in enumerate(weeks)}

    points = np.array([standings[o]["points"] for o in owners], dtype=float)
    points = np.tile(points, (n_sims, 1))
    pf = np.array([standings[o]["pf"] for o in owners], dtype=float)
    pf = np.tile(pf, (n_sims, 1))

    if remaining:
        means = np.array([mu[o] for o in owners], dtype=float)
        draws = rng.normal(means[None, :, None], sigma,
                           size=(n_sims, n_teams, len(weeks)))
        if granularity:
            draws = np.round(draws / granularity) * granularity

        for wk, home, away in remaining:
            w = week_pos[wk]
            h, a = idx[home], idx[away]
            hs, as_ = draws[:, h, w], draws[:, a, w]
            tie = hs == as_
            points[:, h] += np.where(hs > as_, 1.0, 0.0) + 0.5 * tie
            points[:, a] += np.where(as_ > hs, 1.0, 0.0) + 0.5 * tie
            # Accumulate points-for inside the loop, not by summing every drawn
            # week, so a team idle in some week is never credited for it.
            pf[:, h] += hs
            pf[:, a] += as_

    # ahead[n, i, j] -- did j finish above i, on record then points-for?
    same_pts = points[:, None, :] == points[:, :, None]
    same_pf = pf[:, None, :] == pf[:, :, None]
    # Level on BOTH record and points-for happens in roughly 1 simulation in
    # 4,000 once scores are rounded to the season's precision. A real league
    # would go to a further tiebreaker; here a stable team ordering settles it,
    # which keeps seeds a strict permutation so the probabilities still sum to
    # exactly the number of playoff spots.
    order_break = np.arange(n_teams)[None, :] < np.arange(n_teams)[:, None]
    ahead = ((points[:, None, :] > points[:, :, None])
             | (same_pts & (pf[:, None, :] > pf[:, :, None]))
             | (same_pts & same_pf & order_break[None, :, :]))
    seeds = 1 + ahead.sum(axis=2)

    made = (seeds <= spots).mean(axis=0)
    dist = np.zeros((n_teams, n_teams), dtype=float)
    for i in range(n_teams):
        counts = np.bincount(seeds[:, i], minlength=n_teams + 1)[1:n_teams + 1]
        dist[i] = counts / n_sims
    return {o: {"p": float(made[i]), "seed_dist": [float(x) for x in dist[i]]}
            for i, o in enumerate(owners)}


def all_play(games, season, reg_weeks):
    """What each owner's record would be if they played everyone every week.

    Actual record minus all-play record is this league's schedule luck, and with
    weekly noise at 2.3x the spread in team quality it is often the whole story
    of a season.
    """
    by_week = defaultdict(list)
    for g in games:
        if g["season"] != season or g["phase"] != "regular" or g["week"] > reg_weeks:
            continue
        by_week[g["week"]].append((g["home_owner"], g["home_score"]))
        by_week[g["week"]].append((g["away_owner"], g["away_score"]))

    out = defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0})
    for entries in by_week.values():
        for owner, score in entries:
            for other, other_score in entries:
                if other == owner:
                    continue
                if score > other_score:
                    out[owner]["wins"] += 1
                elif score < other_score:
                    out[owner]["losses"] += 1
                else:
                    out[owner]["ties"] += 1
    for rec in out.values():
        total = rec["wins"] + rec["losses"] + rec["ties"]
        rec["pct"] = round((rec["wins"] + 0.5 * rec["ties"]) / total, 4) if total else 0.0
    return dict(out)


def season_curves(games, season, fmt, lam=FITTED_LAMBDA, n_sims=N_SIMS, schedule=None):
    """Odds for every week of one season, honest series plus hindsight overlay."""
    reg_weeks, spots = fmt["reg_weeks"], fmt["playoff_spots"]
    owners = owners_in(games, season)
    if not owners and schedule:
        owners = sorted({o for _wk, h, a in schedule for o in (h, a)})
    if not owners:
        return None

    season_games = [g for g in games
                    if g["season"] == season and g["phase"] == "regular"]
    all_scores = [s for g in season_games for s in (g["home_score"], g["away_score"])]
    gran = detect_granularity(all_scores)

    # Hindsight holds strength at the full-season estimate while standings still
    # advance week by week: "how likely was this given what these teams turned
    # out to be worth".
    full = estimate(team_scores(games, season), lam=lam) if season_games else None

    weeks = []
    for through in range(0, reg_weeks + 1):
        standings = standings_at(games, season, through)
        if schedule is not None:
            remaining = [(wk, h, a) for wk, h, a in schedule if wk > through]
        else:
            remaining = remaining_matchups(games, season, through, reg_weeks)
        status = clinch_status(standings, remaining, spots)

        est = point_in_time(games, season, week=through + 1, lam=lam)
        rng = np.random.default_rng(SEED + season * 100 + through)
        sim = simulate(owners, standings, remaining, est["mu"], est["sd"],
                       spots, granularity=gran, n_sims=n_sims, rng=rng)

        if full:
            rng_h = np.random.default_rng(SEED + season * 100 + through + 50)
            hind = simulate(owners, standings, remaining, full["mu"], full["sd"],
                            spots, granularity=gran, n_sims=n_sims, rng=rng_h)
        else:
            hind = sim

        row = {}
        for o in owners:
            p = sim[o]["p"]
            ph = hind[o]["p"]
            # A settled question is not for Monte Carlo to answer.
            if status[o] == "clinched":
                p = ph = 1.0
            elif status[o] == "eliminated":
                p = ph = 0.0
            row[o] = {"p": round(p, 4), "p_hindsight": round(ph, 4),
                      "status": status[o],
                      "seed_dist": [round(x, 4) for x in sim[o]["seed_dist"]],
                      "wins": standings[o]["wins"], "losses": standings[o]["losses"],
                      "ties": standings[o]["ties"], "pf": standings[o]["pf"]}
        weeks.append({"week": through, "teams": row})

    final = standings_at(games, season, reg_weeks)
    made = set(seed_order(final)[:spots]) if season_games else set()
    return {"season": season, "owners": owners, "reg_weeks": reg_weeks,
            "playoff_spots": spots, "weeks": weeks,
            "made_playoffs": sorted(made),
            "all_play": all_play(games, season, reg_weeks),
            "final": {o: final[o] for o in owners},
            "story": story_stats(weeks, owners, made)}


def story_stats(weeks, owners, made):
    """Clinch/elimination weeks, the biggest swing, and the best recovery."""
    clinched, eliminated = {}, {}
    for wk in weeks:
        for o in owners:
            st = wk["teams"][o]["status"]
            if st == "clinched" and o not in clinched:
                clinched[o] = wk["week"]
            if st == "eliminated" and o not in eliminated:
                eliminated[o] = wk["week"]

    biggest = None
    for prev, cur in zip(weeks, weeks[1:]):
        for o in owners:
            delta = cur["teams"][o]["p"] - prev["teams"][o]["p"]
            if biggest is None or abs(delta) > abs(biggest["delta"]):
                biggest = {"owner": o, "week": cur["week"], "delta": round(delta, 4),
                           "from": prev["teams"][o]["p"], "to": cur["teams"][o]["p"]}

    recovery = None
    for o in made:
        # Ignore the preseason point: everyone starts uniform, so it says nothing.
        low = min((wk["teams"][o]["p"], wk["week"]) for wk in weeks[1:]) if len(weeks) > 1 else None
        if low and (recovery is None or low[0] < recovery["low"]):
            recovery = {"owner": o, "low": low[0], "week": low[1]}

    return {"clinched": clinched, "eliminated": eliminated,
            "biggest_swing": biggest, "best_recovery": recovery}


def enumerate_exact(owners, standings, remaining, spots, granularity=0.1):
    """Exact playoff probability by enumerating every win/loss combination.

    A TEST ORACLE, not a production path: 3^n over remaining games is tractable
    only for the last week or two. Ties are ignored here (they are rare enough
    not to matter for the agreement check) so each game is a coin flip between
    two outcomes, which the simulator must match within tolerance.
    """
    from itertools import product

    n = len(remaining)
    if n > 14:
        raise ValueError(f"{n} games left is too many to enumerate")
    rank = {o: i for i, o in enumerate(owners)}
    counts = {o: 0 for o in owners}
    total = 0
    for outcomes in product((0, 1), repeat=n):
        pts = {o: standings[o]["points"] for o in owners}
        for (_wk, home, away), home_won in zip(remaining, outcomes):
            pts[home if home_won else away] += 1
        # Same strict ordering the simulator uses, so the two are comparable.
        order = sorted(owners, key=lambda o: (-pts[o], -standings[o]["pf"], rank[o]))
        for o in order[:spots]:
            counts[o] += 1
        total += 1
    return {o: counts[o] / total for o in owners}
