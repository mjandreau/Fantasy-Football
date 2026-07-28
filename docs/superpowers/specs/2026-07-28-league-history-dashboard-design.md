# Fantasy Football League History Dashboard — Design

**Date:** 2026-07-28
**Status:** Approved (design); pending implementation plan
**Author:** Matt Jandreau (with Claude)

## Summary

Build an interactive, self-contained HTML dashboard that presents 15 seasons
(2011–2025) of a 12-manager fantasy football league's history — standings,
records, head-to-head rivalries, and per-owner profiles — done with strong
front-end design and hosted on GitHub Pages so league managers can view it.

This is **Phase 1** of a larger project (`Fantasy-Football` repo, whose README
promises "Valuation Model, Draft Model, League History"). Phase 1 delivers the
**League History** half. Later phases add a **player valuation model** and a
**draft model/tool** (data sourced from ESPN), and may surface reserved content
(trash-talk interviews, commish comments, draft-prediction accuracy).

The design deliberately mirrors the sibling project
`Baseball Fantasy Draft and Valuation`, which already ships a single
self-contained `dashboard/index.html` (dark theme, Chart.js via CDN, embedded
data) served on GitHub Pages.

## Goals

- One repeatable build step turns the source spreadsheets into a clean dataset
  and a finished dashboard.
- The dashboard is a single `index.html` that opens with no server and no live
  Excel dependency (all data embedded as JSON).
- Faithful reproduction of the league's existing metrics (esp. Power Index).
- A distinct, polished football visual identity.
- Shareable via a free GitHub Pages URL.

## Non-goals (Phase 1)

- Player valuation model, draft model/tool, ESPN data integration (later phases).
- Trash-talk archive, commish comments, and draft-prediction-accuracy tabs
  (data exists; held in reserve for a later pass).
- Any server-side/backend component or database.

## Source data

Two Excel files (kept local in `data/`, gitignored):

### `The Gridiron.xlsx` (36 sheets — the analytical engine)
- **`Data_Sorted`** — the canonical results table: **1,117 games across all 15
  seasons**, normalized to consistent **owner names**. Columns: Season, Week,
  Home Team (owner), Home Score, Away Team (owner), Away Score, Total Score,
  Margin, Winner, Loser, Tie. This is the results spine.
- **`Data`** — same rows, raw Google-Form input (timestamped). Redundant with
  `Data_Sorted`; `Data_Sorted` is preferred.
- **`Input`** — hand-entered championships and last-place finishes per owner.
- **`All Time Stats` / `Current Season` / `Single Season Stats`** — computed
  standings; source of the **Power Index formula** (read from formula cells).
- **`Setup`** — owner roster (15 all-time owners incl. historical co-managers
  Chris Borea, Joe Kosich, Tucker).

### `League Schedule History.xlsx` (15 sheets, one per season 2011–2025)
- Weekly matchup grids carrying the **fun team names** (e.g. "MATTY BIG TRAPS")
  and W-L records — the flavor `Data_Sorted` lacks. Layout per row:
  `AWAY TEAM (record) | Manager | Score || Score | Manager | HOME TEAM (record)`.

### Owner roster
12 active owners: Baker, Buffalo Joe, Devin, Joe Klim, Joe Ricci, Luke, Matt,
Nolan, Pel, Reid (co-managed w/ Mike), Spark, Walter. Plus historical
co-managers: Chris Borea, Joe Kosich, Tucker. League was 10 teams (2011–2014),
expanded to 12 (2015+).

### Confirmed champions (from `Input`)
Walter '11/'12 · Matt '13/'15 · Luke '14 · Buffalo Joe '16/'22 ·
Nolan '17/'19/'20/'21 · Baker '18 · Joe Ricci '24.
**Gap:** 2023 champion & last-place are missing; 2025 is in progress.

## Architecture

A **Python build step** produces a **self-contained dashboard**:

```
data/*.xlsx  ──►  build/build_data.py  ──►  build/league_data.json
                                        └─►  dashboard/index.html (data embedded)
```

Rationale: repeatable every season (drop in new data, re-run, redeploy) and the
published page has zero runtime dependencies. Alternatives rejected: reading
xlsx live in-browser (fragile/slow); hand-copying data into HTML (not
repeatable).

### Project structure (inside the cloned `Fantasy-Football` repo)

```
Fantasy-Football/
├─ dashboard/
│  └─ index.html          # self-contained dashboard (data embedded as JSON)
├─ data/                  # source spreadsheets — gitignored, local only
│  ├─ The Gridiron.xlsx
│  └─ League Schedule History.xlsx
├─ build/
│  ├─ build_data.py       # xlsx → clean games + computed stats → JSON + HTML
│  └─ league_data.json    # generated intermediate ("the cleaned data")
├─ docs/
│  └─ superpowers/specs/  # this spec and future specs
├─ .gitignore             # excludes data/*.xlsx
└─ README.md
```

## Data model — the tidy games table

`build_data.py` emits one canonical **games** table, one row per game:

| field | source |
|-------|--------|
| `season` | Data_Sorted |
| `week` | Data_Sorted |
| `is_playoff` | inferred (see Open Items) |
| `home_owner`, `away_owner` | Data_Sorted |
| `home_team_name`, `away_team_name` | joined from League Schedule History (by owner+season+score) |
| `home_score`, `away_score` | Data_Sorted |
| `winner`, `loser`, `margin`, `tie` | Data_Sorted / derived |

All downstream stats are **computed** from this table — never hand-copied.
Champions/last-place come from `Input` (a small curated overlay keyed by
owner+season).

## Computed metrics

- **Standings** (all-time and per-season): Wins, Losses, Win%, Points For,
  Points Against, Average Score, Streak, Games.
- **Power Index** (exact league formula, reproduced):
  `PI = ((AvgScore / league_avg(AvgScore)) * 80 + Win% * 100) * (1/7)`
  where `AvgScore = PointsFor / Games`, and `league_avg(AvgScore)` is the mean
  of per-owner average scores in that scope (season or all-time).
- **Power Rank** = rank of Power Index within scope.
- **Head-to-head**: full pairwise matrix (record, avg scores, biggest wins,
  meeting history) for every owner pairing.
- **Record book**: highest/lowest single-team scores, biggest margins, closest
  games, highest combined scores, ties log.
- **Owner careers**: titles, last-place finishes, per-season finish, best/worst
  seasons and games, top rivalries.

## Dashboard — six tabs

1. **Overview** — championship banner by year, all-time leaders, current-season
   (2025) snapshot, fun facts.
2. **All-Time Rankings** — sortable all-time standings with Power Index/Rank;
   career leaderboards.
3. **Season-by-Season** — year selector (2011–2025): that season's standings,
   champion, fun team names, and weekly results.
4. **Head-to-Head** — pick two owners → rivalry record, averages, biggest wins,
   full meeting history (interactive version of the Gridiron H2H engine).
5. **Record Book** — all-time highs/lows, blowouts, nail-biters, ties.
6. **Owner Deep Dive** — per-owner profile: titles, finishes, career-arc chart,
   top rivals, best/worst games.

## Visual direction

Distinct **football identity**: dark, modern, broadcast/ESPN-style — gridiron
greens with a bold accent color, subtle field/yard-line motifs, Chart.js for
charts, card-based layout, sortable tables, responsive. Detailed visual design
executed under the front-end design skill during implementation. Family
resemblance to the baseball dashboard's structure without copying its palette.

## Hosting

Push the repo to `github.com/mjandreau/Fantasy-Football`; enable **GitHub Pages**
(serving `dashboard/` or root `index.html`) for a free shareable link. Source
`.xlsx` files stay local via `.gitignore`; the dashboard works standalone
because its data is embedded.

## Open items (resolved during build)

1. **2023 champion & last-place** — missing from `Input`; Matt to provide, or
   derive from playoff results if identifiable.
2. **Playoffs vs regular season** — the games table includes playoff weeks;
   infer/mark `is_playoff` so standings can separate regular-season record from
   playoff results (needed to correctly attribute champions). Heuristic:
   regular-season week count varies by era (13–14 weeks); confirm the playoff
   start week per season against the schedule history.
3. **Team-name join** — matching fun team names to owners relies on
   owner+season+score; verify no ambiguous matches (e.g., identical scores in a
   week) and fall back to manager name where needed.

## Future phases (out of scope now)

- Player valuation model (projections → values / auction $), ESPN data.
- Draft model / live draft assistant.
- Reserved content tabs: Trash Talk & Commish archive, Draft-Prediction Accuracy.
