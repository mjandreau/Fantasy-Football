# Fantasy Football — League History Dashboard

Fifteen seasons (2011–2025) of league history, reconciled from two independent
data sources and rendered into a single self-contained, static dashboard.

**Live dashboard:** hosted via GitHub Pages from this repo — see
[`dashboard/index.html`](dashboard/index.html). Once Pages is enabled
(Settings → Pages → Deploy from branch → root), the site root redirects
straight there.

## What's here

- **`dashboard/index.html`** — the league history dashboard. Fully
  self-contained: all league data is embedded directly in the HTML (as a JSON
  blob), so the file can be opened locally in a browser or hosted as a static
  file with no server or build step required. The only external requests are
  the Chart.js library and web fonts loaded from public CDNs, both with
  graceful fallbacks. Six tabs:
  - **Overview** — league-wide header stats and headline numbers
  - **All-Time Rankings** — Power Index and career leaderboards across all
    owners who meet the games-played qualifier
  - **Season-by-Season** — standings and results for any single season,
    2011–2025
  - **Head-to-Head** — pick any two owners and see their full matchup history
  - **Record Book** — single-game and single-season records, streaks, and
    other league milestones
  - **Owner Deep Dive** — full career history for a single owner across every
    season they played

- **`build/`** — the Python data pipeline that produces `league_data.json`
  and injects it into the dashboard. See "Rebuilding the dashboard" below.

- **`data/`** — source spreadsheets (not tracked in git; see below).

- **`tests/`** — pytest suite covering the loaders, normalization,
  reconciliation, metrics, and injection steps (33 tests).

## League scope

- **15 seasons**: 2011–2025
- **15 owners total**: 12 currently active + 3 historical owners who left the
  league in earlier seasons
- **1,399 regular-season + playoff games** reconciled across both sources

## Data sources

Two independent spreadsheets are cross-checked against each other during the
build, and any discrepancies are written out to `build/reconciliation.md`:

- **`data/League Schedule History.xlsx`** — the **primary** source of truth
  for schedules, scores, and standings.
- **`data/The Gridiron.xlsx`** — a secondary source used purely for
  **validation**. Where the two sources conflict, the reconciliation report
  flags the discrepancy and the primary source wins; games present in the
  primary source but missing from Gridiron (or vice versa) are also called
  out.

Both source files are excluded from version control (see `.gitignore`) since
they contain the raw league spreadsheets. To rebuild the dashboard from
scratch you'll need your own copies of these two files in `data/`.

## Rebuilding the dashboard

The dashboard's embedded data can be regenerated from the source spreadsheets:

```bash
pip install -r requirements.txt
python -m build.build_data
```

This will:

1. Load and normalize both source spreadsheets
2. Reconcile them against each other, writing `build/reconciliation.md`
3. Compute standings, Power Index, head-to-head records, career stats, and
   record-book entries
4. Assemble everything into `build/league_data.json`
5. Inject that JSON directly into `dashboard/index.html`, replacing the
   embedded data blob in place (the dashboard's HTML/CSS/JS shell is
   untouched — only the data payload changes)

Run the test suite with:

```bash
python -m pytest
```

## Hosting on GitHub Pages

This repo is set up to be served with **GitHub Pages, deploying from a
branch, from the repository root** — no build step on GitHub's side, since
the dashboard is a single static, self-contained HTML file.

- **`index.html`** at the repo root is a tiny redirect page that forwards
  visitors to `dashboard/`. This avoids duplicating the (large,
  data-embedded) dashboard file at two locations in the repo.
- **`.nojekyll`** at the repo root tells GitHub Pages to skip Jekyll
  processing, since this is a plain static site with no Jekyll content.

Enabling Pages itself (repo Settings → Pages) is a one-time manual step for a
repo maintainer with push/admin access and is not part of this codebase.

## Roadmap

**Phase 1 (this branch): League History Dashboard — complete.** Data
pipeline, reconciliation, and all six dashboard tabs are built and tested.

**Phase 2 (planned): Valuation & Draft Models.** The original goal of this
repository — a fantasy football player valuation model and draft-day
decision tool — is planned as a follow-on phase, building on the historical
league data established here.
