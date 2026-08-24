# 🏈 Fantasy Football — League History Dashboard ("The Gridiron")

Fifteen-plus seasons of league history (2011–present), reconciled from the
league's spreadsheets and ESPN's fantasy API, rendered into a single
self-contained static dashboard.

**Live dashboard:** https://mjandreau.github.io/Fantasy-Football/
(GitHub Pages, deploy-from-branch, repo root; the root `index.html` redirects
to `dashboard/`).

## The dashboard — 11 tabs

`dashboard/index.html` is fully self-contained: all data is embedded as a JSON
blob between `/*DATA_START*/…/*DATA_END*/` markers, so it opens locally or
hosts as a static file. Only Chart.js and web fonts load from CDNs.

1. **Overview** — stat tiles, headline insights, Hall of Champions, current standings
2. **All-Time Rankings** — standings with scope toggle (regular / incl. playoffs /
   playoffs-only + first-round byes), Power Index, trophies, finish columns,
   average-finish chart. Best = post-playoff final placement (🥇 = a title)
3. **Season Timeline** — finish-by-season bump chart with multi-select owner
   picker; league scoring-era trend
4. **Season-by-Season** — per-year standings, luck report (all-play), and the
   reconstructed championship bracket (byes, 3rd-place game, consolation collapse)
5. **Head-to-Head** — the Domination Grid (win% heatmap, active owners by
   default) + any-two-owners rivalry detail
6. **League Analytics** — skill-vs-schedule luck scatter, cumulative luck lines,
   boom/bust volatility, bracket DNA, **Moves vs Glory** (churn vs finish)
7. **Playoff Odds** — week-by-week probability of making the playoffs for
   every season, computed point-in-time (each week sees only what was known
   then), with a full-hindsight overlay, exact clinch/elimination, and a
   schedule-luck panel (actual vs all-play record)
8. **Lineup Lab** *(2019+)* — start/sit efficiency vs optimal lineups, Hall of
   Blunders, biggest benched games, **Waiver Wire Hall of Fame**, best seasons
   left on waivers
9. **Draft Room** — the two draft boards per year (main draft incl. K/D-ST;
   3-round defensive IDP draft), first-overall gallery, draft grades,
   steals & busts (value = pick slot vs points rank, within each draft).
   A board appears as soon as that season drafts; grades, steals and busts
   wait until games have actually been played
10. **Record Book** — sub-tabbed records: scores, blowouts, streaks, crowns…
11. **Owner Deep Dive** — per-owner career, All-Time Team (best-ever player at
    each of the 11 lineup slots), rivalry report, personal insights

League format notes: 12 teams (10 in 2011–14; Chris Borea, Joe Kosich, and
Tucker departed at the 2015 expansion and appear as pinned "inactive" owners).
IDP-lite lineup (QB/2RB/2WR/TE/2 flex/K/D-ST/DL/LB/DB). Two drafts per year.
Standings and Power Index are regular-season only, with a 40-game all-time
qualifier. Playoff seeding is record then points-for, and the playoff field has
varied (8 spots 2011-13, 6 since; 13 or 14 regular weeks depending on year) —
the build reads the format per season and never hardcodes it.

**Workbook rounding, and the four repaired games.** The League Schedule History
workbook stores pre-2018 scores rounded, so season points-for runs 3-5 points
above ESPN's for 2013-2017 and four decisive games (2011 wk14, 2013 wk12,
2014 wk5, 2017 wk7) were recorded as ties. ESPN reports no ties in any of those
seasons, and in each case both owners' records differ from the workbook by
exactly one win and one loss — so `build/tie_repair.py` restores the winner and
then asserts every season's W-L-T matches ESPN exactly, failing the build if it
does not. The lost half-point is not recoverable, so points-for stays slightly
high for 2013-2017; it does not change any seed order.

## Data sources

| Source | Role | Tracked in git? |
|---|---|---|
| `data/League Schedule History.xlsx` | **Primary** game results 2011–2025 (incl. playoffs) | No (local) |
| `data/The Gridiron.xlsx` | Validation cross-check; discrepancies → `build/reconciliation.md` | No (local) |
| `data/espn/*.json` | ESPN cache: drafts 2011+, box scores 2019+, transaction counters, scoring rulebooks, free-agent pools, player positions | No (local) |
| `data/espn_credentials.json` | ESPN league id + `espn_s2`/`SWID` cookies | **Never** (gitignored) |

**The drafted-but-unplayed season.** The moment a draft happens, ESPN serves the
whole upcoming season: real rosters, real lineups, an 18-week schedule — and
every score `0.0`. Counted naively that becomes a phantom season at 100% lineup
efficiency, pads career game totals, stretches All-Time Team spans into a year
nobody scored in, and manufactures draft grades out of ranked zeros.
`lineups.season_has_results()` is the single guard, and everything reading box
scores calls it (`build_lineups`, `all_time_teams`, `build_waivers`,
`drafts._season_points`); `build_odds` skips a season with no played games
because its scoring model is fit from results. The draft board itself is exempt
— that data is real, so the newest board ships the moment the draft ends.

**Kicker positions.** ESPN spells kicker both `K` and `PK` depending on where the
position is read from. `PK` must stay in `drafts._OFF_POS` or kickers fall into
the IDP draft — this silently put 88 kickers on the defensive side of the boards
until it was caught in Aug 2026. From 2019 on the defensive draft comes out at
exactly 3 rounds × teams (a test asserts it); earlier years still run over
because ESPN no longer resolves positions for some long-retired players, which
fall back to `-` and land on defense.

ESPN facts worth remembering: player-level box scores exist **2019 onward only**;
the per-move transaction log is **deleted** by ESPN when a season closes (only
season counters survive); in-season pickups are reconstructed by roster-diffing
weekly box scores (a "pickup" may be a waiver add or a trade).

## Rebuilding

```bash
pip install -r requirements.txt      # openpyxl, pytest (+ pip install espn_api)
python -m build.espn_scrape          # top up the ESPN cache (resumable; skips cached years)
python -m build.build_data           # xlsx + cache -> league_data.json -> injected into dashboard/index.html
python -m pytest                     # full test suite
git add dashboard/index.html && git commit && git push   # Pages redeploys automatically
```

The build degrades gracefully: without the ESPN cache, the ESPN-powered tabs
render a "not included" note; the credentials and cache never leave `data/`.

## Season-to-season runbook

**Each new season (first run of the year):**
1. ESPN rolls the league over automatically; the scraper's year range is
   dynamic, and empty "shell" seasons (no draft, no games yet) are skipped by
   the pipeline until real data exists.
2. After the drafts: `python -m build.espn_scrape --refresh 2026` (refetches
   that year only), then rebuild + push → Draft Room shows the new boards.

**During the season (weekly refresh):**
```bash
python -m build.espn_scrape --refresh 2026
python -m build.build_data
git commit -am "week N refresh" && git push
```
Note: current-season **standings/games** still come from the spreadsheet today.
A planned upgrade (below) sources the live season straight from ESPN so the
spreadsheet only needs updating at season's end — or not at all.

**End of season:** update the two spreadsheets, add the champion to
`CHAMPIONS` in `build/curated.py`, refresh the scrape, rebuild, push.

## Roadmap

- **Live-season mode** — a Current Season view fed entirely from the ESPN
  scrape (scores, standings, luck, and lineups updating via the weekly refresh
  commands; a one-command refresh script). The public site is static, so "the
  refresh button" is running that command locally — credentials never leave
  this machine.
- **Phase 2: valuation & draft model** — built and maintained **privately,
  outside this repo**. Not part of the public site, by design.

## Development notes

Specs and plans live in `docs/superpowers/`. Frontend changes are verified by
executing the actual built `dashboard/index.html` in jsdom (all tabs must
render with zero uncaught errors) — the data-marker bug taught us to test the
real bytes, not an approximation:

```
npm install jsdom
node tests/frontend/check_dashboard.js dashboard/index.html
```

That harness also re-derives the Playoff Odds tab's numbers from the embedded
payload, so a curve that silently disagrees with the engine fails the check.

`python -m build.calibrate` refits the odds model and prints its reliability
curve. Re-run it after adding a season and update `FITTED_LAMBDA` in
`build/scoring.py` if it moves.
