# Dashboard Analytics Upgrade — Design (Phase 1.5)

**Date:** 2026-07-29
**Status:** Approved (design); inline execution (no separate plan doc, per user)
**Author:** Matt Jandreau (with Claude)

## Summary

Upgrade the live League History dashboard from 6 tabs to 8, with an analytics
layer the baseball dashboard doesn't have — powered by the weekly game-level
data (1,399 games) the pipeline already produces. Keep the football broadcast
identity; raise information density (stat tiles, insight boxes, heatmaps,
scatter charts).

## Architecture (unchanged pattern)

All new metrics are computed in the **Python pipeline** (TDD, pytest) and
embedded in `league_data.json` → injected into the self-contained
`dashboard/index.html`. No client-side computation of analytics beyond
rendering. Same build → inject → push → GitHub Pages flow.

New module: `build/analytics.py` (keeps `metrics.py` focused). Wired into
`assemble.py`. Tests: `tests/test_analytics.py`.

## New metrics (definitions)

Regular season only unless noted. "Week" = (season, week, phase="regular").

1. **All-play / luck** — per owner, all-time and per-season. For each of an
   owner's weekly scores, count opponents-that-week with a lower score (ties
   0.5); `expected_wins = sum / (teams_that_week - 1)`. `luck = actual_wins −
   expected_wins`. Positive = schedule-blessed.
2. **Consistency** — per owner: mean and population std dev of weekly scores
   (all-time and per-season). High stdev = boom/bust.
3. **Weekly crowns 👑** — per week, the top score wins a crown (ties: all
   tied owners get one). All-time counts + per-season counts.
4. **Streaks** — longest win streak and loss streak per owner across ALL
   games (regular + playoff), ordered by (season, week); ties broken by most
   recent. Reported with span text (e.g. "2013 Wk3 – 2013 Wk9").
5. **Playoff records** — all-time playoff-phase W-L per owner (counts all
   bracket games as recorded, incl. consolation) + regular-season win% for the
   clutch/choker delta.
6. **Season trends** — per season: league average game score, max and min
   single-team score (all phases; it describes the scoring environment).
7. **H2H matrix** — for every owner pair with ≥1 meeting (all phases):
   `pct` = wins/(games) with ties as 0.5, from the `a` perspective, plus games
   count. Frontend renders a 15×15 grid; never-played cells are blank.
8. **Insights engine** — deterministic, computed findings emitted as
   `{id, tab, icon, title, text}`. Initial set (~12): luckiest / unluckiest
   single season ever; biggest boom/bust owner; steadiest owner; clutch king
   (best titles vs all-time scoring rank); playoff choker (biggest reg→playoff
   win% drop, min 10 playoff games); crown king (most weekly crowns); longest
   win streak ever; heartbreak owner (most losses by <5); scoring-inflation
   note (first vs latest season avg); dynasty note (most titles); current-season
   storyline (2025 luck outlier). Tab values: overview | analytics | owner:<name>.

## Data contract additions (`league_data.json`)

```json
"analytics": {
  "all_play": {"all_time": [{"owner": "", "expected_wins": 0.0, "actual_wins": 0,
                             "luck": 0.0, "games": 0}],
               "by_season": {"2025": [/* same shape */]}},
  "consistency": {"all_time": [{"owner": "", "avg": 0.0, "stdev": 0.0, "games": 0}],
                  "by_season": {"2025": [/* same shape */]}},
  "crowns": {"all_time": [{"owner": "", "crowns": 0}],
             "by_season": {"2025": [{"owner": "", "crowns": 0}]}},
  "streaks": [{"owner": "", "longest_win": 0, "win_span": "",
               "longest_loss": 0, "loss_span": ""}],
  "playoff_records": [{"owner": "", "wins": 0, "losses": 0,
                       "playoff_win_pct": 0.0, "reg_win_pct": 0.0}],
  "season_trends": [{"season": 2011, "avg_score": 0.0, "max_score": 0.0,
                     "min_score": 0.0}],
  "h2h_matrix": {"owners": ["..."],
                 "cells": {"A|B": {"a_pct": 0.0, "games": 0}}}
},
"insights": [{"id": "", "tab": "overview", "icon": "", "title": "", "text": ""}]
```

Existing keys unchanged (backward compatible; existing tabs keep working).

## Tabs (6 → 8)

1. **Overview** — add stat-tile row (seasons, games, reigning champ, top PI,
   all-time high score); keep Hall of Champions; add 3–4 headline insight
   boxes; keep current-season standings.
2. **All-Time Rankings** — table adds Crowns 👑 column; below the PI chart add
   a "career chips" strip (longest streaks). Keep sortable table + chart.
3. **📈 Season Timeline** *(new)* — bump chart: every owner's power-rank finish
   2011→2025 (Chart.js line, y reversed, legend toggles owners; historical
   owners default-hidden); scoring-inflation line (season avg with max/min
   band); champions strip.
4. **Season-by-Season** — add that season's luck table (expected vs actual
   wins, luck ±) and the season's crown leader(s).
5. **Head-to-Head** — add the domination heatmap grid ABOVE the picker
   (rows × cols = owners; cell color by win%, text = pct; click a cell to load
   that rivalry in the existing detail view). Existing picker/detail unchanged.
6. **🔬 League Analytics** *(new)* — luck scatter (x = all-time expected wins,
   y = actual wins, diagonal = fair line); boom/bust horizontal bar (stdev);
   playoff clutch/choker paired bars (reg vs playoff win%); "Championship DNA"
   insight boxes.
7. **Record Book** — add Longest Streaks section and Weekly Crowns
   leaderboard.
8. **Owner Deep Dive** — add per-owner stat tiles (luck, stdev w/ league
   label, crowns, playoff W-L), personal insight box if one exists, and an H2H
   domination strip (best victim / worst nemesis by win%, min 5 games). Keep
   career chart + season table.

## Visual density pass

Keep football theme tokens. Add components: `.stat-tiles` (compact KPI row),
`.insight-box` (accent-left-border callout, variant colors), `.heatmap-table`
(green→red scale via inline background colors computed in JS from a fixed
palette), scatter/h-bar Chart.js configs. Slightly tighter card padding.
Load the `dataviz` skill before writing chart code for color/consistency
rules. All 15 owner colors remain from `OWNER_COLORS`.

## Verification

- pytest TDD for every metric with real-data assertions (e.g. crowns sum ==
  number of regular-season weeks ± ties; all-play expected_wins sum ≈ total
  actual wins; streak spans parse).
- jsdom harness runs the ACTUAL built `dashboard/index.html` (marker-bug
  lesson): 0 uncaught errors, all 8 tabs render real data, heatmap cells
  populated, insights present.
- `node --check` on extracted scripts; build idempotency (`git diff` clean
  after second build); push → Pages → live-bytes jsdom check.

## Out of scope

True championship-bracket derivation (consolation vs title games), trash-talk
archive, draft-prediction accuracy, Phase 2 valuation/draft models.
