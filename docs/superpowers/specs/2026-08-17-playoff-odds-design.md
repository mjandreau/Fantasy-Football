# Rolling playoff odds — design

**Date:** 2026-08-17
**Status:** approved, ready to build

A season-long, week-by-week probability that each owner makes the playoffs,
computed for every season the league has played (2011–2026) and surfaced as an
eleventh tab on the public dashboard.

## Goal

Answer "what were my odds, and when did the season actually get decided?" as a
curve across the whole season, not just a number for today. The value at week
*W* must reflect only what was knowable at week *W*. Three further series sit
beside it: a hindsight overlay, a schedule-luck panel, and per-season story
stats.

## Why this is not a port of the baseball engine

The sibling Fantasy-Baseball project answers the same question with Elo over
category share. That model does not belong here, for two reasons.

**There is no opponent interaction in fantasy football.** Your score is
produced entirely by your own starters; the team you are matched against cannot
affect it. Elo is a model *of* pairwise interaction, so applying it here fits a
parameter to something that does not exist. In H2H categories the interaction is
real — you and your opponent compete for each of the 14 categories — which is
why Elo is the right call over there and the wrong one here.

**Seeding needs the point scale.** ESPN breaks record ties on points-for
(verified below, on all 15 seasons). Elo discards the absolute scale and would
force an approximation of the exact quantity that decides seeding fights.

So the model is replaced. What *does* port, and is reused deliberately, is the
surrounding machinery: exact clinch/elimination by bound argument, Monte Carlo
only for genuinely undecided cases, exhaustive enumeration retained as a test
oracle, reliability-decile calibration that fails the build, and the
payload → inject → self-contained-HTML shape.

## League facts this rests on

Measured from `build/league_data.json` (1,153 regular-season games, 2011–2025):

- **Format varies by season and must be read from `data/espn/settings_*.json`,
  never hardcoded:**

  | Seasons | Teams | Regular weeks | Playoff spots |
  |---------|-------|---------------|---------------|
  | 2011 | 10 | 14 | 8 |
  | 2012–13 | 10 | 13 | 8 |
  | 2014 | 10 | 13 | 6 |
  | 2015–20 | 12 | 13 | 6 |
  | 2021–26 | 12 | 14 | 6 |

- **Seeding is record, then points-for.** Confirmed by replaying all 15 seasons
  from game results and matching ESPN's recorded `standing` for every team in
  every season. No divisions exist; the scraper captures none and none are
  needed.
- **Noise dominates skill.** Within-team weekly score sd is **31.8**; the
  between-team sd of season averages is **13.6**. Week-to-week variance is
  ~2.3× the entire spread in team quality.
- **First-half scoring predicts second-half scoring at r = 0.436** (n = 172
  team-seasons). Real signal, but a team's first half explains under 20% of its
  second half.
- **League scoring drifts by season** — 203.9 (2011), 163.1 (2017), ~180 today.
  Any shrinkage target must be per-season; a global mean would distort both ends.
- **Score granularity changes era to era**: half-points 2011–12, whole points
  2013–17, tenths 2018+. This is what governs the tie rate.

### Data-quality repair: four phantom ties

The xlsx is the primary source and its pre-2018 scores are **rounded** — season
points-for totals run +3.0 to +5.5 above ESPN's for 2013–2017. The rounding
collapses four decisive games into apparent ties:

| Season | Week | Game | Truth |
|--------|------|------|-------|
| 2011 | 14 | Devin 206.5 – Reid 206.5 | Devin won |
| 2013 | 12 | Walter 191.0 – Reid 191.0 | Reid won |
| 2014 | 5 | Spark 197.0 – Walter 197.0 | Walter won |
| 2017 | 7 | Joe Klim 174.0 – Walter 174.0 | Walter won |

ESPN records **zero** ties in each of those seasons. In every case the two teams
involved differ from the xlsx by exactly one win and one loss, so the winner is
determined uniquely — no judgement call. The two 2025 ties are genuine and ESPN
agrees.

This is a pre-existing defect affecting standings, Power Index, the record book
and head-to-head, not only the new work. It is repaired at the source in
`build/tie_repair.py` so every consumer benefits, and because the odds engine's
primary validation anchor — replayed standings matching ESPN exactly — cannot
pass while it stands.

Points-for remains ~3–5 points high per season for 2013–2017. That is not
recoverable without finer source data (ESPN box scores start in 2019) and is
documented rather than papered over. It does not change any seed order.

## Model

### Point-in-time team strength

Team *i*'s expected score going into week *W*:

```
mu_i = season_mean + k · (team_mean_through_W-1 − season_mean)
```

where `season_mean` and the shrinkage `k` are computed from weeks `< W` only.
Point-in-time correctness is structural — the estimator is never shown a later
week — so there is no filtering step to get wrong.

`k` comes from **empirical Bayes** rather than a hand-tuned constant. With
within-team variance σ² and *n* games played, a team's observed mean has
sampling variance σ²/n, and the observed spread of team means is
`V_obs = τ² + σ²/n` for true between-team variance τ². So:

```
tau2 = max(0, V_obs − sigma2 / n)
k    = tau2 / (tau2 + sigma2 / n)
```

This is self-calibrating: it shrinks hard when *n* is small and relaxes as
evidence accumulates, without anyone choosing a schedule. The league's numbers
make the early shrinkage severe and correctly so — after four games the standard
error on a team's mean is ≈15.9, larger than the 13.6 spread between teams, so
week-4 ratings belong more than halfway back to the mean.

A single global damping factor `lambda` multiplies `k`, fit by predictive
log-likelihood on 2011–2024 with 2025 held out. If empirical Bayes is right,
`lambda` lands near 1 and the calibration harness says so.

### Simulation

Each remaining week, every team draws a score from `Normal(mu_i, sigma)`, and
the higher draw wins its matchup. Residual skew is 0.38 with excess kurtosis
0.30 — mildly right-skewed and slightly fat-tailed — so calibration checks a
normal draw against empirical resampling of standardised residuals and the
harness picks whichever reads better on the reliability curve.

**Ties emerge from granularity rather than a fitted parameter.** Simulated
scores are rounded to the season's actual precision (0.5 / 1.0 / 0.1) and exact
equality is a tie worth half a win. This predicts the coarse era almost exactly
— 0.89% expected against 4 observed in 499 games — and is the honest mechanism
rather than a constant bolted on.

### Hindsight overlay

A second, visually subordinate series holds team strength at its **full-season**
estimate while standings still advance week by week. It answers "how likely was
this given what these teams turned out to be worth", and given how noisy this
league is, the gap between the two lines is often the whole story.

## Exact clinch and elimination

Monte Carlo must never decide a settled question. The bound argument:

- A team's floor is its current points (`W + 0.5·T`); points cannot be lost.
- A rival's ceiling is its current points plus its remaining games.
- Count rivals whose ceiling ≥ our floor. Fewer than the number of playoff
  spots ⇒ clinched. The mirror argument gives elimination.

O(teams), exact, valid at any week.

**Football wrinkle:** because points-for breaks record ties, a rival level on
record is not resolved by the bound argument alone. The test is therefore
deliberately **conservative** — it declares clinched or eliminated only when the
outcome does not depend on a tiebreak, and leaves genuinely level cases to the
Monte Carlo, which resolves them with simulated points-for. The curve never
reads 100% while a tiebreak could still go the other way.

Exhaustive enumeration over remaining games is retained solely as a **test
oracle** for late-season weeks, where it must agree with both the bound argument
and the simulation.

## Architecture

```
League Schedule History.xlsx ─┐
                              ├─→ games ─→ tie_repair (vs ESPN) ─┐
data/espn/league_*.json ──────┘                                  │
                                                                 ▼
                              scoring.py      point-in-time mu/sigma per week
                              playoff_odds.py clinch + Monte Carlo → curves
                              odds_data.py    payload → league_data.json["odds"]
                              inject.py    →  dashboard/index.html
```

| Module | Responsibility | Depends on |
|--------|----------------|------------|
| `build/tie_repair.py` *(new)* | Resolve xlsx phantom ties from ESPN records; assert W-L-T then matches exactly | — |
| `build/scoring.py` *(new)* | Pure: per-season mean/sd, empirical-Bayes point-in-time team means. No I/O, no numpy. | — |
| `build/playoff_odds.py` *(new)* | Standings, exact clinch/elimination, Monte Carlo, all-play, story stats | scoring, numpy |
| `build/calibrate.py` *(new)* | Fit `lambda`, choose draw distribution, reliability deciles, fail loudly | scoring, playoff_odds |
| `build/odds_data.py` *(new)* | Assemble the payload | playoff_odds |
| `build/espn_scrape.py` *(extend)* | Persist the remaining schedule for the live season | espn_api |

`scoring.py` stays free of I/O and numpy so it is testable in isolation, matching
the discipline of the baseball project's `ratings.py`.

### Scraper change

Historical replay needs no new scraping — every completed game is already in
`league_data.json`. But **no source currently holds the remaining schedule**,
and an in-progress season cannot be simulated without knowing who plays whom in
the weeks still to come. `espn_scrape.py` gains each team's full-season opponent
list from `espn_api.football.Team.schedule`, persisted into
`data/espn/league_<year>.json` as `schedule`. Closed seasons need no backfill.

### Outputs

Per season, per week, per owner: `p_playoffs`, `p_playoffs_hindsight`,
`seed_dist`, and `status` (`alive` / `clinched` / `eliminated`).

Per season, per owner: actual record, all-play record, and the difference —
the schedule-luck panel.

Per season: the week each team clinched or was eliminated, the largest
single-week swing in probability, and the most improbable recovery.

## Surface

An eleventh tab, **Playoff Odds**, following the dashboard's existing lazy-build
tab pattern:

- Season selector, 2011–2026.
- The odds curve for every owner, honest line solid, hindsight overlay
  subordinate, using the CVD-validated owner palette in its fixed assignment
  order.
- Schedule-luck panel: actual vs all-play record, sorted by the gap.
- Story-stat tiles and a clinch/elimination table.

Chart.js 4.4.1 is already loaded by the dashboard, so no new dependency is
introduced on the front end.

## Testing

- **`scoring.py`** — shrinkage monotone in games played, `k → 0` at n = 0,
  `k → 1` as n grows, per-season mean isolation, hand-computed fixtures.
- **`tie_repair.py`** — the four known games resolve to the recorded winners;
  an ambiguous case raises rather than guesses; genuine 2025 ties survive.
- **Standings reconciliation** — replaying all 15 seasons must reproduce ESPN's
  `standing`, W, L and T for every team. This is the anchor test.
- **Champion sanity** — the computed top-N by seed must contain that season's
  curated champion, all 15 years. (The playoff sheets mix championship and
  consolation games, so who "made the playoffs" is derived from regular-season
  standings, never from the presence of playoff games.)
- **Clinch regression** — pins a known settled case.
- **Monte Carlo ↔ enumeration** — agreement within tolerance on a late-season
  week where both are computable.
- **Reliability** — decile check; poor calibration fails the build rather than
  shipping a plausible-looking wrong model.
- **Frontend** — the actual built `dashboard/index.html` executed in jsdom, all
  eleven tabs, zero console errors.

## Dependencies

`numpy` is added to `requirements.txt`. 15 seasons × up to 14 weeks × 10,000
simulations is minutes in pure Python and seconds vectorised.

## Known limitations

- Week-1 odds are near-uniform by construction. With noise at 2.3× skill that is
  the correct answer, not a defect to smooth over.
- Points-for for 2013–2017 stays ~3–5 points high per season from xlsx rounding.
  Seed order is unaffected.
- The model has no roster knowledge. An injury or a lopsided trade registers
  only once results reflect it.
- 2011 used ESPN's pre-tie-rules tiebreak, so its single scoreline tie is
  recorded with a winner.

## Out of scope

Championship odds — simulating the bracket itself. The bracket shape shifts
across eras (8 teams then 6, byes, consolation rounds mixed into the same
sheets) and stacking rounds compounds model error. Revisit once the regular-season
curves are trusted.
