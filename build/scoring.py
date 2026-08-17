"""Point-in-time estimates of how much each team scores.

In fantasy football a team's score is produced entirely by its own starters --
the opponent cannot touch it. So team strength is a scoring *level*, not a
pairwise rating, and the natural model is: estimate each team's expected weekly
score, then simulate matchups by drawing scores and comparing them. That also
keeps the absolute point scale, which the league needs because record ties are
broken on points-for.

The estimate is shrunk toward the league mean by EMPIRICAL BAYES rather than a
hand-tuned schedule. With within-team variance s2 and n games played, a team's
observed mean carries sampling variance s2/n, and the observed spread of team
means is tau2 + s2/n for true between-team variance tau2. Solving for tau2 gives
a shrinkage weight that tightens on its own as evidence accumulates:

    tau2 = max(0, var(team means) - s2/n)
    k    = tau2 / (tau2 + s2/n)

This league needs that shrinkage to be severe early. Measured over 2011-2025,
the within-team weekly sd is 31.8 while the between-team sd of season averages
is only 13.6 -- week-to-week noise is 2.3x the entire spread in team quality --
so after four games the standard error on a team's mean (about 15.9) still
exceeds the real spread, and week-4 ratings belong more than halfway back to the
league mean.

Everything here reads only the weeks it is given. Point-in-time correctness is
structural: callers pass `before_week`, and there is no path by which a later
week can reach the estimator.

Pure functions only: no I/O, no numpy.
"""

import math
from collections import defaultdict

# Used only for the first weeks of 2011, where no prior season exists and no
# games have been played. Both are near the all-era league averages. They cannot
# bias anything meaningful: with no games played every team shrinks fully to the
# same mean, so the resulting odds are uniform whatever the constants say.
PRIOR_MEAN = 180.0
PRIOR_SD = 32.0

# Global damping on the empirical-Bayes weight, fit by build/calibrate.py
# against 2011-2024 by predictive log-likelihood (2025 held out). At 0.6 the
# data asks for noticeably MORE shrinkage than empirical Bayes alone -- another
# reading of how little of a weekly result is signal. The likelihood surface is
# flat between about 0.4 and 0.8 (0.3 nats across 989 games), so do not read the
# exact value as precise; re-run calibrate.py after any season is added.
FITTED_LAMBDA = 0.6

# The workbook stores half-points for 2011-12, whole points for 2013-17 and
# tenths from 2018. Ties fall out of that precision rather than a fitted
# parameter, so the simulator needs to know the step. Coarsest first: the
# granularity is the largest step every score in the season is a multiple of.
_GRANULARITIES = (1.0, 0.5, 0.1)


def detect_granularity(scores):
    """Coarsest step (1.0, 0.5 or 0.1) that every score is a multiple of."""
    if not scores:
        return 0.1
    for step in _GRANULARITIES:
        if all(abs(s / step - round(s / step)) < 1e-6 for s in scores):
            return step
    return 0.1


def team_scores(games, season, before_week=None):
    """{owner: [weekly scores]} for one regular season, weeks < before_week."""
    out = defaultdict(list)
    for g in games:
        if g["season"] != season or g["phase"] != "regular":
            continue
        if before_week is not None and g["week"] >= before_week:
            continue
        out[g["home_owner"]].append(g["home_score"])
        out[g["away_owner"]].append(g["away_score"])
    return dict(out)


def pooled_within_sd(by_owner):
    """Within-team weekly sd, pooled across teams. None if nobody has 2 games."""
    ss, dof = 0.0, 0
    for scores in by_owner.values():
        n = len(scores)
        if n < 2:
            continue
        m = sum(scores) / n
        ss += sum((s - m) ** 2 for s in scores)
        dof += n - 1
    return math.sqrt(ss / dof) if dof else None


def _variance(values):
    n = len(values)
    if n < 2:
        return 0.0
    m = sum(values) / n
    return sum((v - m) ** 2 for v in values) / (n - 1)


def shrinkage(n, sigma, tau2):
    """Empirical-Bayes weight on a team's own average, in [0, 1]."""
    if n <= 0:
        return 0.0
    if tau2 <= 0:
        return 0.0
    se2 = (sigma ** 2) / n
    if se2 <= 0:
        return 1.0
    return tau2 / (tau2 + se2)


def estimate(by_owner, fallback_mean=PRIOR_MEAN, fallback_sd=PRIOR_SD, lam=1.0):
    """Shrunken expected weekly score per owner.

    `lam` is a global damping factor on the empirical-Bayes weight, fit by
    build/calibrate.py. lam == 1.0 means empirical Bayes is taken at face value.

    Returns {"mean", "sd", "tau2", "mu": {owner: expected score}, "k": {owner: weight}}.
    """
    owners = sorted(by_owner)
    flat = [s for o in owners for s in by_owner[o]]
    if not flat:
        return {"mean": fallback_mean, "sd": fallback_sd, "tau2": 0.0,
                "mu": {o: fallback_mean for o in owners},
                "k": {o: 0.0 for o in owners}}

    grand = sum(flat) / len(flat)
    sigma = pooled_within_sd(by_owner) or fallback_sd
    means = [sum(by_owner[o]) / len(by_owner[o]) for o in owners if by_owner[o]]
    counts = [len(by_owner[o]) for o in owners if by_owner[o]]
    n_avg = sum(counts) / len(counts) if counts else 0

    # Observed spread of team means overstates the real spread by the sampling
    # noise each mean carries; subtract it to recover the true between-team
    # variance. Negative means "indistinguishable from no spread at all".
    tau2 = max(0.0, _variance(means) - (sigma ** 2) / n_avg) if n_avg else 0.0

    mu, k = {}, {}
    for o in owners:
        scores = by_owner[o]
        n = len(scores)
        weight = lam * shrinkage(n, sigma, tau2)
        weight = min(1.0, max(0.0, weight))
        own = sum(scores) / n if n else grand
        k[o] = weight
        mu[o] = grand + weight * (own - grand)
    return {"mean": grand, "sd": sigma, "tau2": tau2, "mu": mu, "k": k}


def prior_season_stats(games, season):
    """(mean, sd) from every completed season before `season`, or the constants."""
    scores = []
    for g in games:
        if g["phase"] != "regular" or g["season"] >= season:
            continue
        scores.extend((g["home_score"], g["away_score"]))
    if len(scores) < 2:
        return PRIOR_MEAN, PRIOR_SD
    mean = sum(scores) / len(scores)
    # Prior seasons only need a scale for the first weeks, so the total sd is a
    # fine stand-in for the within-team sd it slightly overstates.
    return mean, math.sqrt(_variance(scores))


def point_in_time(games, season, week, lam=FITTED_LAMBDA):
    """Estimate for `season` going into `week`, using weeks < week only."""
    fb_mean, fb_sd = prior_season_stats(games, season)
    by_owner = team_scores(games, season, before_week=week)
    if not by_owner:
        # Week 1: nobody has played, so every owner in the season sits at the
        # prior mean and the odds come out uniform, which is the honest answer.
        by_owner = {o: [] for o in team_scores(games, season)}
    return estimate(by_owner, fallback_mean=fb_mean, fallback_sd=fb_sd, lam=lam)
