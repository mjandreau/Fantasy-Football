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
- **Complete, reconciled data** — every game, every season, with score conflicts
  between the two source files surfaced and resolved.
- A distinct, polished football visual identity.
- Shareable via a free GitHub Pages URL.

## Non-goals (Phase 1)

- Player valuation model, draft model/tool, ESPN data integration (later phases).
- Trash-talk archive, commish comments, and draft-prediction-accuracy tabs
  (data exists; held in reserve for a later pass).
- Any server-side/backend component or database.

## Source data & the cross-reference finding

Two Excel files (kept local in `data/`, gitignored). A game-log cross-reference
established their roles:

### League Schedule History.xlsx — **PRIMARY source of truth**
- 15 sheets, one per season 2011–2025. **1,360 games total.**
- Contains **every game including playoffs** and the **fun team names** per
  season (e.g. "MATTY BIG TRAPS"). Actively maintained and **complete through
  2025** (regular season + Playoff Rounds 1–3).
- Row layout: `AWAY TEAM (record) | Away Manager | Away Score | Home Score |
  Home Manager | HOME TEAM (record)`.
- Section headers delimit weeks: `NFL Week 1` … `NFL Week 14`, then
  `Playoff Round 1 (NFL Week 15)`, `Playoff Round 2 (NFL Week 16)`,
  `Playoff Round 3 (NFL Week 17)`. A `Bye:` block in Round 1 lists the two
  top-seed bye teams and their bye-week points.

### The Gridiron.xlsx — **SECONDARY (validation + formula + curated lists)**
- `Data_Sorted` — **regular season only** (1,117 games, Weeks 1–14), normalized
  to short **owner names**. **Stale: froze at Week 9 of 2025.** Used to validate
  regular-season scores and to anchor the owner-name normalization.
- `All Time Stats` — source of the **Power Index formula** (read from the cell
  formula, not just values).
- `Input` — hand-entered **champions** and **last-place finishes** per owner.

### Why League History is primary
Cross-reference results (game-level, matched by season + week + owner pair):
- League History has every playoff game; Gridiron has none.
- Gridiron froze at 2025 Week 9; League History has all of 2025.
- Score disagreements (nearly all ~1 pt, consistent with ESPN stat
  corrections): 2019 = 0, 2024 = 3, **2021 = 34**, **2023 = 22**, others 0–3.
- **Resolution decision: League Schedule History wins all score conflicts.**
  The build emits a reconciliation report listing every Gridiron disagreement
  for spot-checking, but does not change values.

### Owner roster & name normalization
12 active owners (short name ← manager string in League History):

| Owner (short) | Manager string(s) in League History |
|---|---|
| Baker | Michael Baker |
| Buffalo Joe | Joe Kaszubowski |
| Devin | Devin Zeller |
| Joe Klim | Joseph Klimczak |
| Joe Ricci | joe ricci |
| Luke | Luke Palma (2014: "Luke Palma, Michael Baker") |
| Matt | Matt Jandreau |
| Nolan | nolan villani (early yrs: "nolan villani, Tucker Bachand") |
| Pel | Ryan Peloquin |
| Reid | "Mike Paleologopoulos, Reid Roberge" / "Red Roberge" |
| Spark | Spark Carpenter |
| Walter | Walter Klimczak |

Historical/co-manager tokens seen in Gridiron early years (Tucker Bachand,
Joe Kosich, Dan/Chris Borea) map to their team's primary owner; the build
reconciliation report flags any manager string that does not resolve. The
"Klimczak" collision (Walter vs Joseph) is resolved on first name.
League was 10 teams (2011–2014), expanded to 12 (2015+).

### Champions & last place (curated list)
Source: Gridiron `Input` + user corrections. Champions:
Walter '11/'12/**'25** · Matt '13/'15 · Luke '14 · Buffalo Joe '16/'22/**'23** ·
Nolan '17/'19/'20/'21 · Baker '18 · Joe Ricci '24.
Last place: Luke '11 · Devin '12/'19/**'23**/**'25** · Spark '13 · Reid '14/'18 ·
Nolan '15 · Joe Klim '16 · Joe Ricci '17/'21 · Pel '20 · Baker '22 · Matt '24.
All 15 seasons now have a recorded champion and last place.

## Architecture

A **Python build step** produces a **self-contained dashboard**:

```
data/*.xlsx  ──►  build/build_data.py  ──►  build/league_data.json   (clean data)
                                        ├─►  build/reconciliation.md  (QA report)
                                        └─►  dashboard/index.html     (data embedded)
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
│  ├─ league_data.json    # generated: the cleaned dataset
│  └─ reconciliation.md   # generated: QA report of source discrepancies
├─ docs/
│  └─ superpowers/specs/  # this spec and future specs
├─ .gitignore             # excludes data/*.xlsx
└─ README.md
```

## Data model — the tidy games table

`build_data.py` parses **League History** into one canonical **games** table,
one row per game:

| field | source |
|-------|--------|
| `season` | sheet name |
| `week` | section header (1–14 regular; 15–17 playoff rounds) |
| `phase` | `regular` or `playoff` (from section label) |
| `playoff_round` | 1/2/3 when playoff, else null |
| `home_owner`, `away_owner` | manager string → normalized owner |
| `home_team_name`, `away_team_name` | team-name text (record stripped) |
| `home_score`, `away_score` | League History scores (authoritative) |
| `winner`, `loser`, `margin`, `tie` | derived |
| `gridiron_conflict` | true if Gridiron had a differing score (for QA report) |

Team name per owner per season = the final/most-frequent team name in that
season's sheet (records in parentheses are stripped). Champions/last-place are a
small curated overlay keyed by season.

## Computed metrics

All computed from the games table. **Standings & Power Index use `phase =
regular` games only** (matching the league's existing figures); playoff games
feed champions, record book, and playoff history.

- **Standings** (all-time and per-season, regular season): Wins, Losses, Win%,
  Points For, Points Against, Average Score, Streak, Games.
- **Power Index** (exact league formula, reproduced):
  `PI = ((AvgScore / league_avg(AvgScore)) * 80 + Win% * 100) * (1/7)`
  where `AvgScore = PointsFor / Games` and `league_avg(AvgScore)` is the mean of
  per-owner average scores in scope. **Power Rank** = rank of PI within scope.
- **Head-to-head**: full pairwise matrix (record, avg scores, biggest wins,
  meeting history), with regular-season and playoff meetings distinguished.
- **Record book**: highest/lowest single-team scores, biggest margins, closest
  games, highest combined scores, ties log (regular + playoff, labeled).
- **Owner careers**: titles, last-place finishes, per-season finish, playoff
  appearances, best/worst seasons and games, top rivalries.

## Dashboard — six tabs

1. **Overview** — championship banner by year, all-time leaders, current-season
   (2025) snapshot, fun facts.
2. **All-Time Rankings** — sortable all-time standings with Power Index/Rank;
   career leaderboards.
3. **Season-by-Season** — year selector (2011–2025): that season's standings,
   champion, fun team names, weekly results, and playoff bracket/results.
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
because its data is embedded. (Before first push, optionally reset the local git
identity from the work email to Matt's personal email.)

## Open items (resolved during build)

1. **Reconciliation report review** — after first build, Matt spot-checks the
   ~60 flagged score conflicts (mostly 2021 & 2023); League History values stand
   unless he says otherwise.
2. **Playoff bracket derivation** — Round 1–3 sheets include all 12 teams
   (championship + placement brackets in parallel) plus a `Bye:` block. Champions
   come from the curated list, not fragile auto-derivation; the Season tab shows
   playoff-round results as recorded. Full bracket reconstruction (seeding →
   final) is best-effort/optional.
3. **Regular-season length varies by era** (13–14 weeks). `phase` is taken from
   the explicit `Playoff Round` labels, so this needs no per-season hardcoding.

## Future phases (out of scope now)

- Player valuation model (projections → values / auction $), ESPN data.
- Draft model / live draft assistant.
- Reserved content tabs: Trash Talk & Commish archive, Draft-Prediction Accuracy.
