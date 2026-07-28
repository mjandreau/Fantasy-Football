# League History Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn 15 seasons of fantasy-football league data (two Excel files) into one clean dataset and a self-contained, GitHub Pages-hostable HTML dashboard with six tabs.

**Architecture:** A Python build step (`build/build_data.py`) parses **League Schedule History** (primary source), normalizes owner names, splits regular season from playoffs, reconciles scores against **The Gridiron** (which wins nothing but supplies the Power Index formula and a QA cross-check), computes all metrics, and writes `build/league_data.json` + `build/reconciliation.md`. A separate injector writes that JSON into a placeholder in the hand-authored `dashboard/index.html`, which renders everything client-side with vanilla JS + Chart.js.

**Tech Stack:** Python 3.12, `openpyxl` (xlsx parsing), `pytest` (tests). Frontend: vanilla HTML/CSS/JS, Chart.js via CDN. No build framework.

## Global Constraints

- **Primary data source:** `League Schedule History.xlsx`. It wins ALL score conflicts. `The Gridiron.xlsx` is validation + Power Index formula + (fallback) champions only.
- **Standings & Power Index use regular-season games only** (`phase == "regular"`, Weeks 1–14). Playoffs feed champions, record book, and H2H history — never regular-season standings.
- **Power Index formula (exact):** `PI = ((AvgScore / league_avg(AvgScore)) * 80 + Win% * 100) * (1/7)`, where `AvgScore = PointsFor / Games` and `league_avg(AvgScore)` = mean of per-owner average scores in scope (season or all-time). `PowerRank` = descending rank of PI within scope.
- **12 active owners** (short names): Baker, Buffalo Joe, Devin, Joe Klim, Joe Ricci, Luke, Matt, Nolan, Pel, Reid, Spark, Walter.
- **3 historical owners** (played only the 2011–2014 10-team era, then left): Chris Borea, Joe Kosich, Tucker. **15 all-time owners** total. Standings/records/H2H/careers include all 15; UI flags historical owners as inactive (via `meta.active_owners`). Early seasons (2011–2014) correctly show 10 teams. "Dan Borea" (schedule) and "Chris Borea" (Gridiron) are the same person → displayed as **Chris Borea**.
- **Source `.xlsx` files stay local** (gitignored). The dashboard must work standalone with data embedded.
- **Python interpreter:** use the environment where `openpyxl`/`pytest` are installed. Commands below use `python`/`pytest`; if not on PATH, prefix with the anaconda env python.
- **Champions (curated, authoritative):** 2011 Walter, 2012 Walter, 2013 Matt, 2014 Luke, 2015 Matt, 2016 Buffalo Joe, 2017 Nolan, 2018 Baker, 2019 Nolan, 2020 Nolan, 2021 Nolan, 2022 Buffalo Joe, 2023 Buffalo Joe, 2024 Joe Ricci, 2025 Walter.
- **Last place (curated):** 2011 Luke, 2012 Devin, 2013 Spark, 2014 Reid, 2015 Nolan, 2016 Joe Klim, 2017 Joe Ricci, 2018 Reid, 2019 Devin, 2020 Pel, 2021 Joe Ricci, 2022 Baker, 2023 Devin, 2024 Matt, 2025 Devin.

## The `league_data.json` contract (produced by Phase 1, consumed by Phase 2)

```json
{
  "meta": {"seasons": [2011, "...", 2025], "owners": ["Baker", "...15 all-time..."], "active_owners": ["Baker", "...12 active..."], "total_games": 1399, "generated": "2026-07-28"},
  "games": [{"season": 2025, "week": 1, "phase": "regular", "playoff_round": null,
             "home_owner": "Walter", "home_team": "Herbie Fully Loaded", "home_score": 152.8,
             "away_owner": "Buffalo Joe", "away_team": "Fields and Streams", "away_score": 212.6,
             "winner": "Buffalo Joe", "loser": "Walter", "margin": 59.8, "tie": false,
             "gridiron_conflict": false}],
  "champions": {"2025": {"champion": "Walter", "last_place": "Devin"}},
  "team_names": {"2025": {"Walter": "Herbie Fully Loaded"}},
  "all_time_standings": [{"owner": "Walter", "wins": 0, "losses": 0, "ties": 0, "win_pct": 0.0,
                          "pf": 0.0, "pa": 0.0, "games": 0, "avg_score": 0.0,
                          "power_index": 0.0, "power_rank": 1}],
  "season_standings": {"2025": ["...same shape as all_time_standings..."]},
  "head_to_head": {"Matt|Walter": {"a": "Matt", "b": "Walter", "a_wins": 0, "b_wins": 0, "ties": 0,
                                   "games": 0, "a_avg": 0.0, "b_avg": 0.0,
                                   "meetings": [{"season": 2019, "phase": "regular", "a_score": 0.0, "b_score": 0.0, "winner": "Matt"}]}},
  "record_book": {"highest_scores": [{"owner": "Spark", "score": 341.0, "season": 2011, "week": 14, "phase": "playoff"}],
                  "lowest_scores": ["..."], "biggest_margins": ["..."], "closest_games": ["..."],
                  "highest_combined": ["..."], "ties": ["..."]},
  "owner_careers": {"Walter": {"titles": [2011, 2012, 2025], "last_places": [],
                               "seasons": [{"season": 2011, "rank": 1, "wins": 0, "losses": 0, "avg_score": 0.0, "made_playoffs": true}],
                               "best_game": {}, "worst_game": {}, "top_rival": "Reid"}}
}
```

Head-to-head keys use the two owners sorted alphabetically joined by `|` (so `"Matt|Walter"`), with `a` < `b`.

## File Structure

- `data/The Gridiron.xlsx`, `data/League Schedule History.xlsx` — source (gitignored).
- `build/loaders.py` — low-level xlsx readers (League History parser, Gridiron reader).
- `build/normalize.py` — manager→owner mapping, team-name cleaning.
- `build/games.py` — assemble the tidy games table from parsed rows.
- `build/reconcile.py` — compare sources, write `reconciliation.md`, flag conflicts.
- `build/metrics.py` — standings, Power Index, head-to-head, record book, owner careers.
- `build/curated.py` — champions/last-place constants + validation.
- `build/build_data.py` — orchestrator: runs everything, writes `league_data.json`, injects into `index.html`.
- `build/inject.py` — inject JSON into `dashboard/index.html` between markers.
- `tests/` — one test module per build module.
- `dashboard/index.html` — hand-authored dashboard with a data placeholder and per-tab JS.
- `.gitignore`, `README.md`, `requirements.txt`.

---

## PHASE 1 — DATA PIPELINE

### Task 1: Scaffold repo + move source data + gitignore

**Files:**
- Create: `.gitignore`, `requirements.txt`, `build/__init__.py`, `tests/__init__.py`, `tests/conftest.py`
- Move: the two `.xlsx` files from the parent folder into `data/`

**Interfaces:**
- Produces: `tests/conftest.py` exposing `DATA_DIR` and a `league_history_path` / `gridiron_path` pytest fixture used by all later tests.

- [ ] **Step 1: Create directories and move the source spreadsheets into `data/`**

```bash
cd "Fantasy-Football"
mkdir -p build tests data dashboard
# Copy the two source files from the project parent folder into data/
cp "../The Gridiron.xlsx" "data/The Gridiron.xlsx"
cp "../League Schedule History.xlsx" "data/League Schedule History.xlsx"
```

- [ ] **Step 2: Write `.gitignore`**

```
# Source spreadsheets — local only
data/*.xlsx

# Python
__pycache__/
*.pyc
.pytest_cache/
.venv/

# Generated (regenerated by build)
build/league_data.json
build/reconciliation.md
```

- [ ] **Step 3: Write `requirements.txt`**

```
openpyxl>=3.1
pytest>=8.0
```

- [ ] **Step 4: Write `tests/conftest.py`**

```python
from pathlib import Path
import pytest

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

@pytest.fixture
def league_history_path():
    p = DATA_DIR / "League Schedule History.xlsx"
    if not p.exists():
        pytest.skip("League Schedule History.xlsx not present in data/")
    return p

@pytest.fixture
def gridiron_path():
    p = DATA_DIR / "The Gridiron.xlsx"
    if not p.exists():
        pytest.skip("The Gridiron.xlsx not present in data/")
    return p
```

- [ ] **Step 5: Create empty `build/__init__.py` and `tests/__init__.py`; verify pytest collects**

Run: `pytest -q`
Expected: `no tests ran` (0 collected) with exit 0 — confirms pytest works and conftest imports.

- [ ] **Step 6: Commit**

```bash
git add .gitignore requirements.txt build/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: scaffold build pipeline and gitignore source data"
```

---

### Task 2: League History parser → raw game rows

Parse every season sheet in League Schedule History into a flat list of raw game dicts. No normalization yet — capture manager strings and team-name-with-record verbatim, plus the section label.

**Files:**
- Create: `build/loaders.py`
- Test: `tests/test_loaders_history.py`

**Interfaces:**
- Produces: `parse_league_history(path) -> list[dict]`. Each dict:
  `{"season": int, "week": int, "phase": "regular"|"playoff", "playoff_round": int|None,
    "away_manager": str, "away_team_raw": str, "away_score": float,
    "home_manager": str, "home_team_raw": str, "home_score": float}`
  Regular weeks are `NFL Week N` (phase="regular", week=N). Playoff rows are under
  `Playoff Round R (NFL Week W)` → phase="playoff", playoff_round=R, week=W. `Bye:` blocks are skipped.

- [ ] **Step 1: Write the failing test**

```python
from build.loaders import parse_league_history

def test_parse_history_counts_and_shape(league_history_path):
    games = parse_league_history(league_history_path)
    # Total games across all 15 sheets (verified via cross-reference)
    assert len(games) == 1399
    # Every game has both scores as floats and a season in range
    for g in games:
        assert 2011 <= g["season"] <= 2025
        assert isinstance(g["home_score"], float)
        assert isinstance(g["away_score"], float)
        assert g["phase"] in ("regular", "playoff")

def test_parse_history_regular_vs_playoff(league_history_path):
    games = parse_league_history(league_history_path)
    reg = [g for g in games if g["phase"] == "regular"]
    ply = [g for g in games if g["phase"] == "playoff"]
    # 2025 must be complete (froze in Gridiron, complete here)
    s25 = [g for g in games if g["season"] == 2025]
    assert len(s25) == 101
    # Playoffs are labeled rounds 1-3
    assert {g["playoff_round"] for g in ply} == {1, 2, 3}
    assert all(g["playoff_round"] is None for g in reg)

def test_parse_history_known_game(league_history_path):
    games = parse_league_history(league_history_path)
    # 2025 Week 1: Fields and Streams (Kaszubowski) 212.6 vs Herbie Fully Loaded (Walter) 152.8
    wk1 = [g for g in games if g["season"] == 2025 and g["phase"] == "regular" and g["week"] == 1]
    match = [g for g in wk1 if g["away_score"] == 212.6 and g["home_score"] == 152.8]
    assert len(match) == 1
    assert "Kaszubowski" in match[0]["away_manager"]
    assert match[0]["home_team_raw"].startswith("Herbie Fully Loaded")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_loaders_history.py -q`
Expected: FAIL — `ModuleNotFoundError` / `parse_league_history` undefined.

- [ ] **Step 3: Implement `parse_league_history` in `build/loaders.py`**

```python
import re
import openpyxl

_WEEK_RE = re.compile(r"nfl week\s*(\d+)", re.I)
_PLAYOFF_RE = re.compile(r"playoff round\s*(\d+).*week\s*(\d+)", re.I)


def _isnum(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def parse_league_history(path):
    """Parse every season sheet into a flat list of raw game dicts."""
    wb = openpyxl.load_workbook(path, data_only=True)
    games = []
    for name in wb.sheetnames:
        if not name.strip().isdigit():
            continue
        season = int(name.strip())
        ws = wb[name]
        phase = "regular"
        week = None
        rnd = None
        for row in ws.iter_rows(values_only=True):
            c0 = row[0]
            if isinstance(c0, str):
                low = c0.strip().lower()
                mp = _PLAYOFF_RE.search(low)
                if mp:
                    phase, rnd, week = "playoff", int(mp.group(1)), int(mp.group(2))
                    continue
                mw = _WEEK_RE.search(low)
                if mw:
                    phase, rnd, week = "regular", None, int(mw.group(1))
                    continue
                if low.startswith("away team") or low.startswith("bye"):
                    continue
            # data row: cols = away_team, away_mgr, away_score, home_score, home_mgr, home_team
            if len(row) >= 6 and _isnum(row[2]) and _isnum(row[3]):
                games.append({
                    "season": season,
                    "week": week,
                    "phase": phase,
                    "playoff_round": rnd,
                    "away_team_raw": str(row[0]).strip() if row[0] else "",
                    "away_manager": str(row[1]).strip() if row[1] else "",
                    "away_score": round(float(row[2]), 1),
                    "home_score": round(float(row[3]), 1),
                    "home_manager": str(row[4]).strip() if row[4] else "",
                    "home_team_raw": str(row[5]).strip() if row[5] else "",
                })
    wb.close()
    return games
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_loaders_history.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add build/loaders.py tests/test_loaders_history.py
git commit -m "feat: parse League Schedule History into raw game rows"
```

---

### Task 3: Manager→owner normalization + team-name cleaning

**Files:**
- Create: `build/normalize.py`
- Test: `tests/test_normalize.py`

**Interfaces:**
- Produces:
  - `owner_from_manager(manager: str) -> str` — maps a League History manager string to a short owner name; raises `ValueError` on an unrecognized string (so the pipeline surfaces gaps).
  - `clean_team_name(raw: str) -> str` — strips the trailing `(record)` from a team-name cell.
  - `OWNERS: list[str]` — the 12 active owners.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from build.normalize import owner_from_manager, clean_team_name, OWNERS

def test_owner_mapping_basic():
    assert owner_from_manager("Joe Kaszubowski") == "Buffalo Joe"
    assert owner_from_manager("Joseph Klimczak") == "Joe Klim"
    assert owner_from_manager("Walter Klimczak") == "Walter"   # collision resolved on first name
    assert owner_from_manager("nolan villani") == "Nolan"
    assert owner_from_manager("nolan villani, Tucker Bachand") == "Nolan"
    assert owner_from_manager("Mike Paleologopoulos, Reid Roberge") == "Reid"
    assert owner_from_manager("Red Roberge") == "Reid"
    assert owner_from_manager("Ryan Peloquin") == "Pel"
    assert owner_from_manager("joe ricci") == "Joe Ricci"
    assert owner_from_manager("Luke Palma, Michael Baker") == "Luke"  # first listed wins

def test_owner_mapping_unknown_raises():
    with pytest.raises(ValueError):
        owner_from_manager("Some Rando")

def test_clean_team_name():
    assert clean_team_name("MATTY BIG TRAPS(6-7-1)") == "MATTY BIG TRAPS"
    assert clean_team_name("Herbie Fully Loaded(9-4-1)") == "Herbie Fully Loaded"
    assert clean_team_name("CEEDEE's NUTZ!?(8-6-0)") == "CEEDEE's NUTZ!?"
    assert clean_team_name("Plain Name") == "Plain Name"

def test_owner_mapping_historical():
    assert owner_from_manager("Tucker Bachand") == "Tucker"
    assert owner_from_manager("joe kosich") == "Joe Kosich"
    assert owner_from_manager("Dan Borea") == "Chris Borea"
    assert owner_from_manager("Chris Borea") == "Chris Borea"
    # co-managed early team resolves to the first-listed owner
    assert owner_from_manager("nolan villani, joe kosich") == "Nolan"

def test_owner_lists():
    from build.normalize import ACTIVE_OWNERS, HISTORICAL_OWNERS, ALL_TIME_OWNERS
    assert len(OWNERS) == 12 and OWNERS is ACTIVE_OWNERS
    assert set(HISTORICAL_OWNERS) == {"Chris Borea", "Joe Kosich", "Tucker"}
    assert len(ALL_TIME_OWNERS) == 15
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalize.py -q`
Expected: FAIL — module/functions undefined.

- [ ] **Step 3: Implement `build/normalize.py`**

```python
import re

ACTIVE_OWNERS = ["Baker", "Buffalo Joe", "Devin", "Joe Klim", "Joe Ricci", "Luke",
                 "Matt", "Nolan", "Pel", "Reid", "Spark", "Walter"]
# Departed after the 2015 expansion (played only the 2011-2014 10-team era):
HISTORICAL_OWNERS = ["Chris Borea", "Joe Kosich", "Tucker"]
ALL_TIME_OWNERS = ACTIVE_OWNERS + HISTORICAL_OWNERS
OWNERS = ACTIVE_OWNERS  # backward-compatible alias: the 12 active owners

# Ordered rules: first substring that matches the FIRST listed manager wins.
# Order matters — more specific keys first (e.g. "joseph klim" before "walter").
_RULES = [
    ("kaszubowski", "Buffalo Joe"),
    ("joseph klim", "Joe Klim"),
    ("walter", "Walter"),
    ("villani", "Nolan"),
    ("carpenter", "Spark"),
    ("jandreau", "Matt"),
    ("ricci", "Joe Ricci"),
    ("baker", "Baker"),
    ("zeller", "Devin"),
    ("palma", "Luke"),
    ("peloquin", "Pel"),
    ("roberge", "Reid"),
    ("paleologopoulos", "Reid"),
    # Historical (2011-2014) owners who later left the league:
    ("kosich", "Joe Kosich"),
    ("bachand", "Tucker"),
    ("borea", "Chris Borea"),  # both "Dan Borea" (schedule) and "Chris Borea" (Gridiron)
]

_RECORD_RE = re.compile(r"\s*\((\d+\s*-\s*\d+(?:\s*-\s*\d+)?)\)\s*$")


def owner_from_manager(manager):
    """Map a manager string to a short owner name. Uses only the FIRST listed
    manager (before any comma) so co-managed teams resolve to their primary owner."""
    if not manager:
        raise ValueError("empty manager string")
    first = manager.split(",")[0].strip().lower()
    for key, owner in _RULES:
        if key in first:
            return owner
    raise ValueError(f"unrecognized manager: {manager!r}")


def clean_team_name(raw):
    """Strip a trailing (record) suffix like '(9-4-1)' from a team name."""
    return _RECORD_RE.sub("", raw).strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_normalize.py -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add build/normalize.py tests/test_normalize.py
git commit -m "feat: manager->owner normalization and team-name cleaning"
```

---

### Task 4: Assemble the tidy games table

Turn raw parsed rows into normalized game dicts (owners resolved, teams cleaned, winner/loser/margin/tie derived). Also derive per-season team names (final/most-frequent name per owner).

**Files:**
- Create: `build/games.py`
- Test: `tests/test_games.py`

**Interfaces:**
- Consumes: `parse_league_history` (Task 2), `owner_from_manager`, `clean_team_name` (Task 3).
- Produces:
  - `build_games(history_path) -> list[dict]` — games in the `league_data.json` `games` shape **except** `gridiron_conflict` (added in Task 6). Fields: season, week, phase, playoff_round, home_owner, home_team, home_score, away_owner, away_team, away_score, winner, loser, margin, tie.
  - `season_team_names(games) -> dict[str, dict[str, str]]` — `{season(str): {owner: team_name}}` using each owner's most-frequent team name that season.

- [ ] **Step 1: Write the failing test**

```python
from build.games import build_games, season_team_names

def test_build_games_shape_and_counts(league_history_path):
    games = build_games(league_history_path)
    assert len(games) == 1399
    g = games[0]
    for k in ("season", "week", "phase", "home_owner", "away_owner",
              "home_team", "away_team", "home_score", "away_score",
              "winner", "loser", "margin", "tie"):
        assert k in g

def test_build_games_winner_and_margin(league_history_path):
    games = build_games(league_history_path)
    m = [g for g in games if g["season"] == 2025 and g["phase"] == "regular"
         and g["week"] == 1 and g["away_score"] == 212.6][0]
    assert m["away_owner"] == "Buffalo Joe"
    assert m["home_owner"] == "Walter"
    assert m["winner"] == "Buffalo Joe"
    assert m["loser"] == "Walter"
    assert m["margin"] == 59.8
    assert m["tie"] is False

def test_build_games_no_unknown_owners(league_history_path):
    # Every game (all 15 seasons) resolves to a known all-time owner.
    from build.normalize import ALL_TIME_OWNERS
    games = build_games(league_history_path)
    for g in games:
        assert g["home_owner"] in ALL_TIME_OWNERS
        assert g["away_owner"] in ALL_TIME_OWNERS

def test_build_games_historical_owners_in_early_seasons(league_history_path):
    # The 3 departed owners appear in the 2011-2014 (10-team) era.
    games = build_games(league_history_path)
    early = {g["home_owner"] for g in games if g["season"] <= 2014} | \
            {g["away_owner"] for g in games if g["season"] <= 2014}
    assert {"Chris Borea", "Joe Kosich", "Tucker"} <= early

def test_season_team_names(league_history_path):
    games = build_games(league_history_path)
    names = season_team_names(games)
    assert names["2025"]["Walter"] == "Herbie Fully Loaded"
    assert names["2025"]["Matt"] == "MATTY BIG TRAPS"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_games.py -q`
Expected: FAIL — module undefined.

- [ ] **Step 3: Implement `build/games.py`**

```python
from collections import Counter, defaultdict
from build.loaders import parse_league_history
from build.normalize import owner_from_manager, clean_team_name


def build_games(history_path):
    raw = parse_league_history(history_path)
    games = []
    for r in raw:
        ho = owner_from_manager(r["home_manager"])
        ao = owner_from_manager(r["away_manager"])
        hs, as_ = r["home_score"], r["away_score"]
        tie = hs == as_
        if tie:
            winner = loser = None
        elif hs > as_:
            winner, loser = ho, ao
        else:
            winner, loser = ao, ho
        games.append({
            "season": r["season"], "week": r["week"], "phase": r["phase"],
            "playoff_round": r["playoff_round"],
            "home_owner": ho, "home_team": clean_team_name(r["home_team_raw"]),
            "home_score": hs,
            "away_owner": ao, "away_team": clean_team_name(r["away_team_raw"]),
            "away_score": as_,
            "winner": winner, "loser": loser,
            "margin": round(abs(hs - as_), 1), "tie": tie,
        })
    return games


def season_team_names(games):
    counts = defaultdict(lambda: defaultdict(Counter))
    for g in games:
        counts[str(g["season"])][g["home_owner"]][g["home_team"]] += 1
        counts[str(g["season"])][g["away_owner"]][g["away_team"]] += 1
    out = {}
    for season, owners in counts.items():
        out[season] = {owner: c.most_common(1)[0][0] for owner, c in owners.items()}
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_games.py -q`
Expected: 5 passed. (The 3 historical owners — Chris Borea, Joe Kosich, Tucker — are already covered by `_RULES` from Task 3, so all seasons resolve. Co-managed early teams like "nolan villani, joe kosich" resolve to the first-listed owner, Nolan.)

- [ ] **Step 5: Commit**

```bash
git add build/games.py tests/test_games.py
git commit -m "feat: assemble tidy games table with owners, teams, outcomes"
```

---

### Task 5: Gridiron reader (regular-season scores for QA)

Read The Gridiron's `Data_Sorted` into the same keyed shape so scores can be reconciled. The Power Index formula is fixed in Global Constraints, so we do NOT extract it from cells.

**Files:**
- Modify: `build/loaders.py`
- Test: `tests/test_loaders_gridiron.py`

**Interfaces:**
- Produces: `parse_gridiron(path) -> dict` mapping `(season, week, frozenset({owner_a, owner_b}))` → `{owner: score}`. Owners here are already short names (Gridiron uses them natively), except co-manager historical tokens which are passed through as-is.

- [ ] **Step 1: Write the failing test**

```python
from build.loaders import parse_gridiron

def test_parse_gridiron_counts(gridiron_path):
    d = parse_gridiron(gridiron_path)
    # Gridiron Data_Sorted = regular season only, 1117 games
    assert len(d) == 1117
    # 2025 froze at week 9 -> far fewer 2025 keys than a full season
    s25 = [k for k in d if k[0] == 2025]
    assert 40 <= len(s25) <= 55

def test_parse_gridiron_lookup(gridiron_path):
    d = parse_gridiron(gridiron_path)
    key = (2025, 1, frozenset({"Walter", "Buffalo Joe"}))
    assert key in d
    assert d[key]["Buffalo Joe"] == 212.6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_loaders_gridiron.py -q`
Expected: FAIL — `parse_gridiron` undefined.

- [ ] **Step 3: Add `parse_gridiron` to `build/loaders.py`**

```python
def parse_gridiron(path):
    """Read Data_Sorted into {(season, week, frozenset(owners)): {owner: score}}."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Data_Sorted"]
    out = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        # cols: A blank, B season, C week, D home, E home_score, F away, G away_score
        season, week, home, hs, away, as_ = row[1], row[2], row[3], row[4], row[5], row[6]
        if not (_isnum(season) and _isnum(hs) and _isnum(as_)):
            continue
        if not home or not away:
            continue
        season = int(float(season))
        wk = int(float(week)) if _isnum(week) else week
        out[(season, wk, frozenset({home, away}))] = {
            home: round(float(hs), 1),
            away: round(float(as_), 1),
        }
    wb.close()
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_loaders_gridiron.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add build/loaders.py tests/test_loaders_gridiron.py
git commit -m "feat: read Gridiron Data_Sorted for score reconciliation"
```

---

### Task 6: Reconcile scores + write QA report + flag conflicts

Compare each regular-season game to Gridiron. League History always wins; flag `gridiron_conflict=True` where scores differ, and write a human-readable `reconciliation.md`.

**Files:**
- Create: `build/reconcile.py`
- Test: `tests/test_reconcile.py`

**Interfaces:**
- Consumes: `parse_gridiron` (Task 5); games list (Task 4).
- Produces:
  - `flag_conflicts(games, gridiron) -> list[dict]` — returns games with a `gridiron_conflict` bool added to every game (playoffs always False — Gridiron has no playoffs).
  - `reconciliation_report(games) -> str` — Markdown summarizing conflicts and missing-from-Gridiron counts per season.

- [ ] **Step 1: Write the failing test**

```python
from build.games import build_games
from build.loaders import parse_gridiron
from build.reconcile import flag_conflicts, reconciliation_report

def test_flag_conflicts_2019_clean_2021_dirty(league_history_path, gridiron_path):
    games = build_games(league_history_path)
    grid = parse_gridiron(gridiron_path)
    flagged = flag_conflicts(games, grid)
    assert all("gridiron_conflict" in g for g in flagged)
    def conflicts(season):
        return sum(1 for g in flagged
                   if g["season"] == season and g["phase"] == "regular" and g["gridiron_conflict"])
    assert conflicts(2019) == 0
    assert conflicts(2021) >= 20   # cross-reference found ~34
    # playoffs never flagged
    assert all(not g["gridiron_conflict"] for g in flagged if g["phase"] == "playoff")

def test_reconciliation_report_is_markdown(league_history_path, gridiron_path):
    games = flag_conflicts(build_games(league_history_path), parse_gridiron(gridiron_path))
    report = reconciliation_report(games)
    assert report.startswith("#")
    assert "2021" in report
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reconcile.py -q`
Expected: FAIL — module undefined.

- [ ] **Step 3: Implement `build/reconcile.py`**

```python
from collections import Counter


def flag_conflicts(games, gridiron):
    for g in games:
        conflict = False
        if g["phase"] == "regular":
            key = (g["season"], g["week"], frozenset({g["home_owner"], g["away_owner"]}))
            gr = gridiron.get(key)
            if gr is not None:
                gh = gr.get(g["home_owner"])
                ga = gr.get(g["away_owner"])
                if gh is not None and ga is not None:
                    conflict = (gh != g["home_score"]) or (ga != g["away_score"])
        g["gridiron_conflict"] = conflict
    return games


def reconciliation_report(games):
    per_season = Counter()
    details = []
    for g in games:
        if g.get("gridiron_conflict"):
            per_season[g["season"]] += 1
            details.append(g)
    lines = ["# Score Reconciliation Report",
             "",
             "League Schedule History is authoritative; the games below differ from "
             "The Gridiron (regular season only). League History values are used.",
             "",
             "## Conflicts per season", ""]
    for season in sorted(per_season):
        lines.append(f"- {season}: {per_season[season]} conflicting game(s)")
    if not per_season:
        lines.append("- None — sources agree on all overlapping regular-season games.")
    lines += ["", "## Detail", "",
              "| Season | Wk | Matchup | League Hist (home/away) |"]
    lines.append("|---|---|---|---|")
    for g in sorted(details, key=lambda x: (x["season"], x["week"])):
        lines.append(f"| {g['season']} | {g['week']} | "
                     f"{g['home_owner']} vs {g['away_owner']} | "
                     f"{g['home_score']}/{g['away_score']} |")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reconcile.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add build/reconcile.py tests/test_reconcile.py
git commit -m "feat: reconcile scores vs Gridiron and generate QA report"
```

---

### Task 7: Curated champions + last-place constants

**Files:**
- Create: `build/curated.py`
- Test: `tests/test_curated.py`

**Interfaces:**
- Produces: `CHAMPIONS: dict[str, dict]` = `{season(str): {"champion": owner, "last_place": owner}}` for 2011–2025, and `validate_curated(owners) -> None` (raises if any name is not a known owner).

- [ ] **Step 1: Write the failing test**

```python
import pytest
from build.curated import CHAMPIONS, validate_curated
from build.normalize import OWNERS

def test_all_seasons_present():
    assert [int(y) for y in CHAMPIONS] == list(range(2011, 2026))
    assert CHAMPIONS["2025"] == {"champion": "Walter", "last_place": "Devin"}
    assert CHAMPIONS["2023"]["champion"] == "Buffalo Joe"

def test_curated_names_are_valid_owners():
    validate_curated(OWNERS)  # should not raise

def test_validate_curated_rejects_unknown():
    with pytest.raises(ValueError):
        validate_curated(["OnlyOneGuy"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_curated.py -q`
Expected: FAIL — module undefined.

- [ ] **Step 3: Implement `build/curated.py`**

```python
CHAMPIONS = {
    "2011": {"champion": "Walter", "last_place": "Luke"},
    "2012": {"champion": "Walter", "last_place": "Devin"},
    "2013": {"champion": "Matt", "last_place": "Spark"},
    "2014": {"champion": "Luke", "last_place": "Reid"},
    "2015": {"champion": "Matt", "last_place": "Nolan"},
    "2016": {"champion": "Buffalo Joe", "last_place": "Joe Klim"},
    "2017": {"champion": "Nolan", "last_place": "Joe Ricci"},
    "2018": {"champion": "Baker", "last_place": "Reid"},
    "2019": {"champion": "Nolan", "last_place": "Devin"},
    "2020": {"champion": "Nolan", "last_place": "Pel"},
    "2021": {"champion": "Nolan", "last_place": "Joe Ricci"},
    "2022": {"champion": "Buffalo Joe", "last_place": "Baker"},
    "2023": {"champion": "Buffalo Joe", "last_place": "Devin"},
    "2024": {"champion": "Joe Ricci", "last_place": "Matt"},
    "2025": {"champion": "Walter", "last_place": "Devin"},
}


def validate_curated(owners):
    valid = set(owners)
    for season, rec in CHAMPIONS.items():
        for role in ("champion", "last_place"):
            if rec[role] not in valid:
                raise ValueError(f"{season} {role} '{rec[role]}' not a known owner")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_curated.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add build/curated.py tests/test_curated.py
git commit -m "feat: curated champions and last-place constants"
```

---

### Task 8: Metrics — standings + Power Index

**Files:**
- Create: `build/metrics.py`
- Test: `tests/test_metrics_standings.py`

**Interfaces:**
- Consumes: games list (with `phase`).
- Produces:
  - `standings(games, season=None) -> list[dict]` — regular-season standings sorted by Power Rank. When `season` is None, all-time; else that season. Each row: owner, wins, losses, ties, win_pct, pf, pa, games, avg_score, power_index, power_rank. Uses **regular-season games only**.

- [ ] **Step 1: Write the failing test**

```python
from build.games import build_games
from build.metrics import standings

def test_all_time_standings_structure(league_history_path):
    rows = build_and_stand(league_history_path)
    # 15 all-time owners: 12 active + 3 historical (2011-2014)
    assert len(rows) == 15
    top = rows[0]
    for k in ("owner", "wins", "losses", "ties", "win_pct", "pf", "pa",
              "games", "avg_score", "power_index", "power_rank"):
        assert k in top
    assert top["power_rank"] == 1
    # ranks are 1..15 unique
    assert sorted(r["power_rank"] for r in rows) == list(range(1, 16))

def test_early_season_has_ten_teams(league_history_path):
    from build.games import build_games
    rows = standings(build_games(league_history_path), season=2011)
    assert len(rows) == 10  # 10-team era

def test_standings_regular_season_only(league_history_path):
    games = build_games(league_history_path)
    rows = standings(games)  # all-time
    total_games = sum(r["games"] for r in rows)
    reg_games = sum(1 for g in games if g["phase"] == "regular")
    # each regular game contributes to 2 owners' game counts
    assert total_games == reg_games * 2

def test_season_standings_2025(league_history_path):
    games = build_games(league_history_path)
    rows = standings(games, season=2025)
    assert len(rows) == 12
    assert sum(r["games"] for r in rows) == sum(
        1 for g in games if g["season"] == 2025 and g["phase"] == "regular") * 2

def build_and_stand(path):
    return standings(build_games(path))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_metrics_standings.py -q`
Expected: FAIL — module undefined.

- [ ] **Step 3: Implement `standings` in `build/metrics.py`**

```python
from collections import defaultdict


def _regular(games, season=None):
    return [g for g in games
            if g["phase"] == "regular" and (season is None or g["season"] == season)]


def _accumulate(games):
    acc = defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0, "pf": 0.0,
                               "pa": 0.0, "games": 0, "results": []})
    for g in games:
        for owner, own, opp in ((g["home_owner"], g["home_score"], g["away_score"]),
                                (g["away_owner"], g["away_score"], g["home_score"])):
            a = acc[owner]
            a["pf"] += own
            a["pa"] += opp
            a["games"] += 1
            if g["tie"]:
                a["ties"] += 1
                a["results"].append("T")
            elif own > opp:
                a["wins"] += 1
                a["results"].append("W")
            else:
                a["losses"] += 1
                a["results"].append("L")
    return acc


def standings(games, season=None):
    acc = _accumulate(_regular(games, season))
    rows = []
    for owner, a in acc.items():
        gp = a["games"]
        avg = a["pf"] / gp if gp else 0.0
        decided = a["wins"] + a["losses"] + a["ties"]
        win_pct = (a["wins"] + 0.5 * a["ties"]) / decided if decided else 0.0
        rows.append({"owner": owner, "wins": a["wins"], "losses": a["losses"],
                     "ties": a["ties"], "win_pct": round(win_pct, 4),
                     "pf": round(a["pf"], 1), "pa": round(a["pa"], 1),
                     "games": gp, "avg_score": round(avg, 2)})
    league_avg = sum(r["avg_score"] for r in rows) / len(rows) if rows else 1.0
    for r in rows:
        pi = ((r["avg_score"] / league_avg) * 80 + r["win_pct"] * 100) * (1 / 7) if league_avg else 0.0
        r["power_index"] = round(pi, 4)
    rows.sort(key=lambda r: r["power_index"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["power_rank"] = i
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_metrics_standings.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add build/metrics.py tests/test_metrics_standings.py
git commit -m "feat: regular-season standings with Power Index"
```

---

### Task 9: Metrics — head-to-head, record book, owner careers

**Files:**
- Modify: `build/metrics.py`
- Test: `tests/test_metrics_extras.py`

**Interfaces:**
- Consumes: games list; `standings` (Task 8); `CHAMPIONS` (Task 7).
- Produces:
  - `head_to_head(games) -> dict` — keyed `"A|B"` (owners sorted), value per the contract (`a`,`b`,`a_wins`,`b_wins`,`ties`,`games`,`a_avg`,`b_avg`,`meetings[]`). All phases counted; each meeting tagged with its phase.
  - `record_book(games) -> dict` — `highest_scores`, `lowest_scores`, `biggest_margins`, `closest_games`, `highest_combined`, `ties`; each a list of up to 15 entries (all phases, phase-labeled).
  - `owner_careers(games, champions) -> dict` — per owner: `titles`, `last_places`, `seasons[]` (season, rank, wins, losses, avg_score, made_playoffs), `best_game`, `worst_game`, `top_rival`.

- [ ] **Step 1: Write the failing test**

```python
from build.games import build_games
from build.metrics import head_to_head, record_book, owner_careers
from build.curated import CHAMPIONS

def test_head_to_head_keys_sorted(league_history_path):
    h2h = head_to_head(build_games(league_history_path))
    assert "Matt|Walter" in h2h
    rec = h2h["Matt|Walter"]
    assert rec["a"] == "Matt" and rec["b"] == "Walter"
    assert rec["games"] == rec["a_wins"] + rec["b_wins"] + rec["ties"]
    assert len(rec["meetings"]) == rec["games"]

def test_record_book_highest_score(league_history_path):
    rb = record_book(build_games(league_history_path))
    top = rb["highest_scores"][0]
    assert top["score"] >= 300  # Spark 341 in 2011 is the known all-time high
    assert set(("owner", "score", "season", "week", "phase")).issubset(top)

def test_owner_careers_titles(league_history_path):
    careers = owner_careers(build_games(league_history_path), CHAMPIONS)
    assert set(careers["Walter"]["titles"]) == {2011, 2012, 2025}
    assert 2024 in careers["Matt"]["last_places"]
    assert len(careers["Nolan"]["seasons"]) >= 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_metrics_extras.py -q`
Expected: FAIL — functions undefined.

- [ ] **Step 3: Implement the three functions in `build/metrics.py`** (append)

```python
def head_to_head(games):
    out = {}
    for g in games:
        if g["tie"] is None:
            pass
        a, b = sorted([g["home_owner"], g["away_owner"]])
        key = f"{a}|{b}"
        rec = out.setdefault(key, {"a": a, "b": b, "a_wins": 0, "b_wins": 0,
                                   "ties": 0, "games": 0, "a_pts": 0.0, "b_pts": 0.0,
                                   "meetings": []})
        a_score = g["home_score"] if g["home_owner"] == a else g["away_score"]
        b_score = g["home_score"] if g["home_owner"] == b else g["away_score"]
        rec["games"] += 1
        rec["a_pts"] += a_score
        rec["b_pts"] += b_score
        if g["tie"]:
            rec["ties"] += 1
            winner = None
        elif a_score > b_score:
            rec["a_wins"] += 1
            winner = a
        else:
            rec["b_wins"] += 1
            winner = b
        rec["meetings"].append({"season": g["season"], "week": g["week"],
                                "phase": g["phase"], "a_score": a_score,
                                "b_score": b_score, "winner": winner})
    for rec in out.values():
        n = rec["games"]
        rec["a_avg"] = round(rec.pop("a_pts") / n, 1) if n else 0.0
        rec["b_avg"] = round(rec.pop("b_pts") / n, 1) if n else 0.0
    return out


def _sides(g):
    return [(g["home_owner"], g["home_score"], g["away_owner"], g["away_score"]),
            (g["away_owner"], g["away_score"], g["home_owner"], g["home_score"])]


def record_book(games, limit=15):
    scores, combined, margins, ties = [], [], [], []
    for g in games:
        base = {"season": g["season"], "week": g["week"], "phase": g["phase"]}
        for owner, s, opp, os_ in _sides(g):
            scores.append({**base, "owner": owner, "score": s, "opponent": opp})
        combined.append({**base, "total": round(g["home_score"] + g["away_score"], 1),
                         "home_owner": g["home_owner"], "away_owner": g["away_owner"]})
        if g["tie"]:
            ties.append({**base, "owner_a": g["home_owner"], "owner_b": g["away_owner"],
                         "score": g["home_score"]})
        else:
            margins.append({**base, "winner": g["winner"], "loser": g["loser"],
                            "margin": g["margin"],
                            "win_score": max(g["home_score"], g["away_score"]),
                            "lose_score": min(g["home_score"], g["away_score"])})
    highest = sorted(scores, key=lambda x: x["score"], reverse=True)[:limit]
    lowest = sorted(scores, key=lambda x: x["score"])[:limit]
    biggest = sorted(margins, key=lambda x: x["margin"], reverse=True)[:limit]
    closest = sorted(margins, key=lambda x: x["margin"])[:limit]
    hi_comb = sorted(combined, key=lambda x: x["total"], reverse=True)[:limit]
    return {"highest_scores": highest, "lowest_scores": lowest,
            "biggest_margins": biggest, "closest_games": closest,
            "highest_combined": hi_comb, "ties": ties}


def owner_careers(games, champions):
    from collections import defaultdict
    owners = sorted({g["home_owner"] for g in games} | {g["away_owner"] for g in games})
    titles = defaultdict(list)
    lasts = defaultdict(list)
    for season, rec in champions.items():
        titles[rec["champion"]].append(int(season))
        lasts[rec["last_place"]].append(int(season))
    seasons_played = defaultdict(set)
    for g in games:
        seasons_played[g["home_owner"]].add(g["season"])
        seasons_played[g["away_owner"]].add(g["season"])

    # best/worst single games and top rival per owner
    best = {}
    worst = {}
    rival_losses = defaultdict(lambda: defaultdict(int))
    for g in games:
        for owner, s, opp, os_ in _sides(g):
            entry = {"season": g["season"], "week": g["week"], "phase": g["phase"],
                     "score": s, "opponent": opp}
            if owner not in best or s > best[owner]["score"]:
                best[owner] = entry
            if owner not in worst or s < worst[owner]["score"]:
                worst[owner] = entry
        if not g["tie"]:
            rival_losses[g["loser"]][g["winner"]] += 1

    careers = {}
    for owner in owners:
        # per-season finish from that season's standings
        season_rows = []
        for season in sorted(seasons_played[owner]):
            srows = standings(games, season=season)
            r = next((x for x in srows if x["owner"] == owner), None)
            if r is None:
                continue
            season_rows.append({"season": season, "rank": r["power_rank"],
                                "wins": r["wins"], "losses": r["losses"],
                                "avg_score": r["avg_score"],
                                "made_playoffs": any(
                                    x["season"] == season and x["phase"] == "playoff"
                                    and owner in (x["home_owner"], x["away_owner"])
                                    for x in games)})
        rivals = rival_losses[owner]
        top_rival = max(rivals, key=rivals.get) if rivals else None
        careers[owner] = {"titles": sorted(titles[owner]),
                          "last_places": sorted(lasts[owner]),
                          "seasons": season_rows,
                          "best_game": best.get(owner),
                          "worst_game": worst.get(owner),
                          "top_rival": top_rival}
    return careers
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_metrics_extras.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add build/metrics.py tests/test_metrics_extras.py
git commit -m "feat: head-to-head, record book, and owner career metrics"
```

---

### Task 10: Orchestrator — assemble `league_data.json` + `reconciliation.md`

**Files:**
- Create: `build/assemble.py` (pure function, easy to test), `build/build_data.py` (CLI wrapper)
- Test: `tests/test_assemble.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `assemble(history_path, gridiron_path, generated="YYYY-MM-DD") -> (dict, str)` — returns the full `league_data.json` dict and the reconciliation markdown.
  - `build/build_data.py` writes `build/league_data.json`, `build/reconciliation.md`, and calls the injector (Task 11).

- [ ] **Step 1: Write the failing test**

```python
from build.assemble import assemble

def test_assemble_top_level_keys(league_history_path, gridiron_path):
    data, report = assemble(league_history_path, gridiron_path, generated="2026-07-28")
    for k in ("meta", "games", "champions", "team_names", "all_time_standings",
              "season_standings", "head_to_head", "record_book", "owner_careers"):
        assert k in data
    assert data["meta"]["total_games"] == 1399
    assert data["meta"]["seasons"] == list(range(2011, 2026))
    assert len(data["all_time_standings"]) == 15
    assert len(data["meta"]["active_owners"]) == 12
    assert set(data["season_standings"].keys()) == {str(y) for y in range(2011, 2026)}
    assert report.startswith("#")

def test_assemble_is_json_serializable(league_history_path, gridiron_path):
    import json
    data, _ = assemble(league_history_path, gridiron_path, generated="2026-07-28")
    json.dumps(data)  # must not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_assemble.py -q`
Expected: FAIL — module undefined.

- [ ] **Step 3: Implement `build/assemble.py`**

```python
from build.games import build_games, season_team_names
from build.loaders import parse_gridiron
from build.reconcile import flag_conflicts, reconciliation_report
from build.metrics import standings, head_to_head, record_book, owner_careers
from build.curated import CHAMPIONS, validate_curated
from build.normalize import ALL_TIME_OWNERS, ACTIVE_OWNERS


def assemble(history_path, gridiron_path, generated):
    validate_curated(ALL_TIME_OWNERS)
    games = build_games(history_path)
    grid = parse_gridiron(gridiron_path)
    games = flag_conflicts(games, grid)
    report = reconciliation_report(games)

    seasons = sorted({g["season"] for g in games})
    data = {
        "meta": {"seasons": seasons, "owners": ALL_TIME_OWNERS,
                 "active_owners": ACTIVE_OWNERS,
                 "total_games": len(games), "generated": generated},
        "games": games,
        "champions": CHAMPIONS,
        "team_names": season_team_names(games),
        "all_time_standings": standings(games),
        "season_standings": {str(s): standings(games, season=s) for s in seasons},
        "head_to_head": head_to_head(games),
        "record_book": record_book(games),
        "owner_careers": owner_careers(games, CHAMPIONS),
    }
    return data, report
```

- [ ] **Step 4: Implement `build/build_data.py`**

```python
import json
from pathlib import Path
from build.assemble import assemble
from build.inject import inject_into_dashboard

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BUILD = ROOT / "build"
DASHBOARD = ROOT / "dashboard" / "index.html"
GENERATED = "2026-07-28"  # bump when rebuilding


def main():
    data, report = assemble(DATA / "League Schedule History.xlsx",
                            DATA / "The Gridiron.xlsx", generated=GENERATED)
    (BUILD / "league_data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (BUILD / "reconciliation.md").write_text(report, encoding="utf-8")
    if DASHBOARD.exists():
        inject_into_dashboard(data, DASHBOARD)
        print(f"Injected data into {DASHBOARD}")
    print(f"Wrote league_data.json ({data['meta']['total_games']} games) and reconciliation.md")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_assemble.py -q`
Expected: 2 passed. (Note: `build_data.py` imports `build.inject` from Task 11 — if running Task 10 alone before Task 11, `test_assemble.py` still passes because it imports `assemble`, not `build_data`. Do not run `build_data.py` until Task 11 exists.)

- [ ] **Step 6: Commit**

```bash
git add build/assemble.py build/build_data.py tests/test_assemble.py
git commit -m "feat: assemble full league_data.json and build orchestrator"
```

---

### Task 11: JSON injector into the dashboard

**Files:**
- Create: `build/inject.py`
- Test: `tests/test_inject.py`

**Interfaces:**
- Consumes: assembled data dict.
- Produces: `inject_into_dashboard(data, html_path) -> None` — replaces the content between `/*DATA_START*/` and `/*DATA_END*/` inside `html_path` with `JSON.stringify`-ready JSON. Idempotent (re-running replaces, never appends).

- [ ] **Step 1: Write the failing test**

```python
import json
from build.inject import inject_into_dashboard

TEMPLATE = ('<html><body><script id="league-data" type="application/json">'
            '/*DATA_START*/{}/*DATA_END*/</script></body></html>')

def test_inject_replaces_between_markers(tmp_path):
    html = tmp_path / "index.html"
    html.write_text(TEMPLATE, encoding="utf-8")
    inject_into_dashboard({"meta": {"total_games": 1360}}, html)
    text = html.read_text(encoding="utf-8")
    start = text.index("/*DATA_START*/") + len("/*DATA_START*/")
    end = text.index("/*DATA_END*/")
    payload = json.loads(text[start:end])
    assert payload["meta"]["total_games"] == 1360

def test_inject_is_idempotent(tmp_path):
    html = tmp_path / "index.html"
    html.write_text(TEMPLATE, encoding="utf-8")
    inject_into_dashboard({"a": 1}, html)
    inject_into_dashboard({"a": 2}, html)
    text = html.read_text(encoding="utf-8")
    assert text.count("/*DATA_START*/") == 1
    start = text.index("/*DATA_START*/") + len("/*DATA_START*/")
    end = text.index("/*DATA_END*/")
    assert json.loads(text[start:end])["a"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_inject.py -q`
Expected: FAIL — module undefined.

- [ ] **Step 3: Implement `build/inject.py`**

```python
import json
import re

_MARKER_RE = re.compile(r"/\*DATA_START\*/.*?/\*DATA_END\*/", re.S)


def inject_into_dashboard(data, html_path):
    text = html_path.read_text(encoding="utf-8")
    if not _MARKER_RE.search(text):
        raise ValueError("data markers /*DATA_START*/.../*DATA_END*/ not found in dashboard")
    payload = json.dumps(data, separators=(",", ":"))
    replacement = f"/*DATA_START*/{payload}/*DATA_END*/"
    text = _MARKER_RE.sub(lambda _m: replacement, text, count=1)
    html_path.write_text(text, encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_inject.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add build/inject.py tests/test_inject.py
git commit -m "feat: idempotent JSON injector for dashboard"
```

---

### Task 12: Full pipeline smoke run

**Files:** none new. Verifies the whole pipeline end-to-end.

- [ ] **Step 1: Run the full test suite**

Run: `pytest -q`
Expected: all tests pass (Tasks 1–11).

- [ ] **Step 2: Create a minimal placeholder dashboard so the injector has a target**

Create `dashboard/index.html` with just:
```html
<!DOCTYPE html><html><head><meta charset="utf-8"><title>Gridiron League History</title></head>
<body><script id="league-data" type="application/json">/*DATA_START*/{}/*DATA_END*/</script>
<p>placeholder — replaced in Phase 2</p></body></html>
```

- [ ] **Step 3: Run the build**

Run: `python -m build.build_data`
Expected: prints "Injected data into ..." and "Wrote league_data.json (1399 games) and reconciliation.md". `build/league_data.json` and `build/reconciliation.md` now exist.

- [ ] **Step 4: Eyeball the reconciliation report**

Open `build/reconciliation.md`; confirm 2021 & 2023 show conflicts and 2019 shows none. (This is the QA artifact Matt reviews.)

- [ ] **Step 5: Commit (dashboard placeholder only — generated files are gitignored)**

```bash
git add dashboard/index.html
git commit -m "chore: placeholder dashboard + verified end-to-end build"
```

---

## PHASE 2 — DASHBOARD

> **Frontend verification convention:** these tasks aren't unit-testable. Each ends with a browser check: run `python -m build.build_data`, open `dashboard/index.html` (use the `claude-in-chrome` skill or `run` skill), confirm the tab renders with real data and the browser console shows **no errors**. Every tab reads data via:
> `const DATA = JSON.parse(document.getElementById('league-data').textContent);`

### Task 13: Dashboard shell — theme, header, nav, tab framework

**REQUIRED SUB-SKILL:** invoke `frontend-design` before writing CSS to establish the distinct football visual identity (dark, broadcast/ESPN feel, gridiron greens + bold accent, yard-line motifs). The code below is the functional skeleton; frontend-design refines palette, type, spacing.

**Files:**
- Modify: `dashboard/index.html` (replace the Task 12 placeholder)

**Interfaces:**
- Produces (global JS available to all tab tasks):
  - `const DATA` — parsed league data.
  - `OWNER_COLORS: {owner: hexcolor}` — stable color per owner.
  - `el(tag, attrs, ...children)` — tiny DOM helper.
  - `renderTable(container, columns, rows)` — sortable table helper. `columns` = `[{key, label, fmt?}]`.
  - `switchTab(id)` and nav wiring; tab panels are `<section class="tab" id="tab-<name>">`.
  - Tab render functions are registered in `RENDERERS = {overview: fn, ...}` and called on first activation.

- [ ] **Step 1: Author the shell** — replace `dashboard/index.html` with a document containing:
  1. `<head>`: meta viewport, `<title>Gridiron League History</title>`, Chart.js CDN `<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>`, and an inline `<style>` implementing the football theme (CSS variables for bg/surface/border/text/accent/green; header, nav tabs, cards, tables, pills, rank badges, chart wrappers, responsive `@media` at 900px).
  2. `<body>`: a `.header` (league title + headline stats: seasons, total games, all-time champ leader), a `.nav` with 6 buttons, six `<section class="tab">` panels (`tab-overview` active by default, others hidden), and the data script:
     `<script id="league-data" type="application/json">/*DATA_START*/{}/*DATA_END*/</script>`
  3. A final `<script>` with the shared helpers below.

```html
<script>
const DATA = JSON.parse(document.getElementById('league-data').textContent);
const OWNERS = DATA.meta.owners;                    // 15 all-time
const ACTIVE_OWNERS = DATA.meta.active_owners;      // 12 active
const isActive = o => ACTIVE_OWNERS.includes(o);
const PALETTE = ["#3fb950","#58a6ff","#f0b429","#bb86fc","#f85149","#39d353",
                 "#ff7b72","#79c0ff","#d29922","#a5d6ff","#ffa657","#7ee787",
                 "#e3b341","#ff9bce","#56d4dd"];   // >=15 for all-time owners
const OWNER_COLORS = Object.fromEntries(OWNERS.map((o,i)=>[o, PALETTE[i%PALETTE.length]]));

function el(tag, attrs={}, ...kids){
  const n=document.createElement(tag);
  for(const [k,v] of Object.entries(attrs||{})){
    if(k==="class") n.className=v;
    else if(k==="html") n.innerHTML=v;
    else if(k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k,v);
  }
  for(const kid of kids){ if(kid==null) continue;
    n.append(kid.nodeType?kid:document.createTextNode(String(kid))); }
  return n;
}

function renderTable(container, columns, rows){
  container.innerHTML="";
  const table=el("table",{class:"data-table"});
  const thead=el("thead"); const htr=el("tr");
  let sortKey=null, sortDir=-1;
  columns.forEach(c=>{
    const th=el("th",{onclick:()=>{ sortKey=c.key; sortDir=-sortDir; draw(); }}, c.label);
    htr.append(th);
  });
  thead.append(htr); table.append(thead);
  const tbody=el("tbody"); table.append(tbody); container.append(table);
  function draw(){
    const data=[...rows];
    if(sortKey) data.sort((a,b)=>{
      const x=a[sortKey], y=b[sortKey];
      return (x>y?1:x<y?-1:0)*sortDir;
    });
    tbody.innerHTML="";
    data.forEach(r=>{
      const tr=el("tr");
      columns.forEach(c=>tr.append(el("td",{html:c.fmt?c.fmt(r[c.key],r):String(r[c.key]??"")})));
      tbody.append(tr);
    });
  }
  draw();
}

const RENDERERS={};
const rendered=new Set();
function switchTab(name){
  document.querySelectorAll(".tab").forEach(s=>s.classList.toggle("active", s.id==="tab-"+name));
  document.querySelectorAll(".nav-btn").forEach(b=>b.classList.toggle("active", b.dataset.tab===name));
  if(!rendered.has(name) && RENDERERS[name]){ RENDERERS[name](); rendered.add(name); }
}
document.querySelectorAll(".nav-btn").forEach(b=>b.addEventListener("click",()=>switchTab(b.dataset.tab)));
// header stats + first tab
window.addEventListener("DOMContentLoaded",()=>{ switchTab("overview"); });
</script>
```

- [ ] **Step 2: Build and open**

Run: `python -m build.build_data` then open `dashboard/index.html` in a browser.
Expected: header + 6 nav buttons render; clicking tabs switches panels; console has no errors. (Panels are empty until their tab tasks land.)

- [ ] **Step 3: Commit**

```bash
git add dashboard/index.html
git commit -m "feat: dashboard shell with football theme, nav, and helpers"
```

---

### Task 14: Overview tab

**Files:** Modify `dashboard/index.html` (add to the final `<script>` and the `#tab-overview` panel).

**Interfaces:** Consumes `DATA.champions`, `DATA.all_time_standings`, `DATA.season_standings`, `DATA.team_names`. Registers `RENDERERS.overview`.

- [ ] **Step 1: Add the renderer** (append inside the shell script, before the `DOMContentLoaded` line)

```javascript
RENDERERS.overview = function(){
  const root=document.getElementById("tab-overview");
  root.innerHTML="";
  // Championship banner
  const champCard=el("div",{class:"card"}, el("div",{class:"card-title"},"🏆 Champions by Year"));
  const champGrid=el("div",{class:"champ-grid"});
  Object.keys(DATA.champions).sort().reverse().forEach(y=>{
    const c=DATA.champions[y].champion;
    const team=(DATA.team_names[y]||{})[c]||"";
    champGrid.append(el("div",{class:"champ-card"},
      el("div",{class:"champ-year"},y),
      el("div",{class:"champ-owner"},c),
      el("div",{class:"champ-team"},team)));
  });
  champCard.append(champGrid); root.append(champCard);

  // All-time leaders (titles)
  const titleCounts={};
  Object.values(DATA.champions).forEach(r=>titleCounts[r.champion]=(titleCounts[r.champion]||0)+1);
  const leaders=Object.entries(titleCounts).sort((a,b)=>b[1]-a[1]);
  const leadCard=el("div",{class:"card"}, el("div",{class:"card-title"},"👑 Most Titles"));
  leaders.forEach(([o,n])=>leadCard.append(el("div",{},`${o}: ${n}`)));
  // Current season snapshot
  const cur=DATA.meta.seasons[DATA.meta.seasons.length-1];
  const curRows=DATA.season_standings[String(cur)];
  const curCard=el("div",{class:"card"}, el("div",{class:"card-title"},`📅 ${cur} Standings`));
  const curWrap=el("div",{class:"table-scroll"}); curCard.append(curWrap);
  const grid2=el("div",{class:"grid2"}, leadCard, curCard);
  root.append(grid2);
  renderTable(curWrap,
    [{key:"power_rank",label:"#"},{key:"owner",label:"Team"},
     {key:"wins",label:"W"},{key:"losses",label:"L"},
     {key:"avg_score",label:"Avg",fmt:v=>v.toFixed(1)},
     {key:"power_index",label:"P-Idx",fmt:v=>v.toFixed(2)}],
    curRows);
};
```

- [ ] **Step 2: Build, open, verify** — `python -m build.build_data`; open dashboard; Overview shows the champions banner (2025 = Walter), Most Titles (Nolan 4), and current-season standings. No console errors.

- [ ] **Step 3: Commit** — `git add dashboard/index.html && git commit -m "feat: Overview tab"`

---

### Task 15: All-Time Rankings tab

**Files:** Modify `dashboard/index.html`.

**Interfaces:** Consumes `DATA.all_time_standings`, `DATA.owner_careers`. Registers `RENDERERS.rankings`. Uses Chart.js for a Power Index bar chart.

- [ ] **Step 1: Add the renderer**

```javascript
RENDERERS.rankings = function(){
  const root=document.getElementById("tab-rankings"); root.innerHTML="";
  const card=el("div",{class:"card"}, el("div",{class:"card-title"},"🏈 All-Time Standings (Regular Season)"));
  const wrap=el("div",{class:"table-scroll"}); card.append(wrap); root.append(card);
  const rows=DATA.all_time_standings.map(r=>({...r,
     titles:(DATA.owner_careers[r.owner]?.titles||[]).length}));
  renderTable(wrap,
    [{key:"power_rank",label:"#"},{key:"owner",label:"Team"},
     {key:"wins",label:"W"},{key:"losses",label:"L"},{key:"ties",label:"T"},
     {key:"win_pct",label:"Win%",fmt:v=>(v*100).toFixed(1)+"%"},
     {key:"pf",label:"PF",fmt:v=>v.toFixed(0)},
     {key:"pa",label:"PA",fmt:v=>v.toFixed(0)},
     {key:"avg_score",label:"Avg",fmt:v=>v.toFixed(1)},
     {key:"power_index",label:"P-Idx",fmt:v=>v.toFixed(2)},
     {key:"titles",label:"🏆"}],
    rows);
  const chartCard=el("div",{class:"card"}, el("div",{class:"card-title"},"Power Index"));
  const cw=el("div",{class:"chart-wrap"}); const canvas=el("canvas"); cw.append(canvas);
  chartCard.append(cw); root.append(chartCard);
  const sorted=[...DATA.all_time_standings].sort((a,b)=>a.power_rank-b.power_rank);
  new Chart(canvas,{type:"bar",data:{labels:sorted.map(r=>r.owner),
    datasets:[{label:"Power Index",data:sorted.map(r=>r.power_index),
      backgroundColor:sorted.map(r=>OWNER_COLORS[r.owner])}]},
    options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}});
};
```

- [ ] **Step 2: Build, open, verify** — All-Time table sorts on header click; Power Index bar chart renders; no console errors.

- [ ] **Step 3: Commit** — `git commit -am "feat: All-Time Rankings tab"`

---

### Task 16: Season-by-Season tab

**Files:** Modify `dashboard/index.html`.

**Interfaces:** Consumes `DATA.season_standings`, `DATA.champions`, `DATA.team_names`, `DATA.games`. Registers `RENDERERS.season`. Includes a `<select>` year picker.

- [ ] **Step 1: Add the renderer**

```javascript
RENDERERS.season = function(){
  const root=document.getElementById("tab-season"); root.innerHTML="";
  const seasons=[...DATA.meta.seasons].reverse();
  const select=el("select",{class:"season-select"});
  seasons.forEach(y=>select.append(el("option",{value:y},y)));
  root.append(el("div",{class:"card"}, el("div",{class:"card-title"},"Select Season"), select));
  const body=el("div"); root.append(body);
  function draw(y){
    body.innerHTML="";
    const champ=DATA.champions[String(y)];
    const names=DATA.team_names[String(y)]||{};
    const head=el("div",{class:"card"},
      el("div",{class:"card-title"},`${y} Season`),
      el("div",{}, `🏆 Champion: ${champ.champion} (${names[champ.champion]||""})`),
      el("div",{}, `💩 Last place: ${champ.last_place} (${names[champ.last_place]||""})`));
    body.append(head);
    const card=el("div",{class:"card"}, el("div",{class:"card-title"},"Final Standings"));
    const wrap=el("div",{class:"table-scroll"}); card.append(wrap); body.append(card);
    const rows=DATA.season_standings[String(y)].map(r=>({...r, team:names[r.owner]||""}));
    renderTable(wrap,
      [{key:"power_rank",label:"#"},{key:"owner",label:"Owner"},{key:"team",label:"Team"},
       {key:"wins",label:"W"},{key:"losses",label:"L"},{key:"ties",label:"T"},
       {key:"pf",label:"PF",fmt:v=>v.toFixed(0)},
       {key:"avg_score",label:"Avg",fmt:v=>v.toFixed(1)},
       {key:"power_index",label:"P-Idx",fmt:v=>v.toFixed(2)}],
      rows);
    // playoff results
    const ply=DATA.games.filter(g=>g.season===y&&g.phase==="playoff")
      .sort((a,b)=>a.playoff_round-b.playoff_round);
    if(ply.length){
      const pc=el("div",{class:"card"}, el("div",{class:"card-title"},"Playoff Results"));
      ply.forEach(g=>pc.append(el("div",{},
        `R${g.playoff_round}: ${g.winner} def. ${g.loser} — `+
        `${Math.max(g.home_score,g.away_score)}–${Math.min(g.home_score,g.away_score)}`)));
      body.append(pc);
    }
  }
  select.addEventListener("change",()=>draw(Number(select.value)));
  draw(seasons[0]);
};
```

- [ ] **Step 2: Build, open, verify** — Year picker defaults to 2025; changing it updates champion line, standings, and playoff results. No console errors.

- [ ] **Step 3: Commit** — `git commit -am "feat: Season-by-Season tab"`

---

### Task 17: Head-to-Head tab

**Files:** Modify `dashboard/index.html`.

**Interfaces:** Consumes `DATA.head_to_head`, `DATA.meta.owners`. Registers `RENDERERS.h2h`. Two `<select>`s pick owners A and B.

- [ ] **Step 1: Add the renderer**

```javascript
RENDERERS.h2h = function(){
  const root=document.getElementById("tab-h2h"); root.innerHTML="";
  const mk=()=>{ const s=el("select",{class:"season-select"});
    OWNERS.forEach(o=>s.append(el("option",{value:o},o))); return s; };
  const a=mk(), b=mk(); b.selectedIndex=1;
  root.append(el("div",{class:"card"}, el("div",{class:"card-title"},"Pick Two Teams"),
    a, el("span",{}," vs "), b));
  const out=el("div"); root.append(out);
  function draw(){
    out.innerHTML="";
    const o1=a.value, o2=b.value;
    if(o1===o2){ out.append(el("div",{class:"card"},"Pick two different owners.")); return; }
    const [x,y]=[o1,o2].sort();
    const rec=DATA.head_to_head[`${x}|${y}`];
    if(!rec){ out.append(el("div",{class:"card"},"No meetings on record.")); return; }
    const o1w = o1===x?rec.a_wins:rec.b_wins;
    const o2w = o2===x?rec.a_wins:rec.b_wins;
    const card=el("div",{class:"card"}, el("div",{class:"card-title"},`${o1} vs ${o2}`),
      el("div",{}, `Record: ${o1} ${o1w} — ${o2w} ${o2}  (${rec.ties} ties, ${rec.games} games)`),
      el("div",{}, `Avg: ${o1} ${(o1===x?rec.a_avg:rec.b_avg).toFixed(1)} — `+
                   `${(o2===x?rec.a_avg:rec.b_avg).toFixed(1)} ${o2}`));
    out.append(card);
    const hist=el("div",{class:"card"}, el("div",{class:"card-title"},"Every Meeting"));
    const wrap=el("div",{class:"table-scroll"}); hist.append(wrap); out.append(hist);
    const rows=[...rec.meetings].reverse().map(m=>({
      season:m.season, week:m.week, phase:m.phase,
      score:`${(o1===x?m.a_score:m.b_score)}–${(o2===x?m.a_score:m.b_score)}`,
      winner:m.winner||"TIE"}));
    renderTable(wrap,[{key:"season",label:"Year"},{key:"week",label:"Wk"},
      {key:"phase",label:"Phase"},{key:"score",label:`${o1}–${o2}`},{key:"winner",label:"Winner"}],rows);
  }
  a.addEventListener("change",draw); b.addEventListener("change",draw); draw();
};
```

- [ ] **Step 2: Build, open, verify** — selecting two owners shows the rivalry record, averages, and full meeting list (regular + playoff labeled). No console errors.

- [ ] **Step 3: Commit** — `git commit -am "feat: Head-to-Head tab"`

---

### Task 18: Record Book tab

**Files:** Modify `dashboard/index.html`.

**Interfaces:** Consumes `DATA.record_book`. Registers `RENDERERS.records`.

- [ ] **Step 1: Add the renderer**

```javascript
RENDERERS.records = function(){
  const root=document.getElementById("tab-records"); root.innerHTML="";
  const section=(title, rows, cols)=>{
    const card=el("div",{class:"card"}, el("div",{class:"card-title"},title));
    const wrap=el("div",{class:"table-scroll"}); card.append(wrap); root.append(card);
    renderTable(wrap, cols, rows);
  };
  const wk=r=>`${r.season} Wk${r.week}${r.phase==="playoff"?" (PO)":""}`;
  section("🔥 Highest Scores", DATA.record_book.highest_scores,
    [{key:"owner",label:"Team"},{key:"score",label:"Score",fmt:v=>v.toFixed(1)},
     {key:"opponent",label:"vs"},{key:"season",label:"When",fmt:(_ ,r)=>wk(r)}]);
  section("🧊 Lowest Scores", DATA.record_book.lowest_scores,
    [{key:"owner",label:"Team"},{key:"score",label:"Score",fmt:v=>v.toFixed(1)},
     {key:"opponent",label:"vs"},{key:"season",label:"When",fmt:(_ ,r)=>wk(r)}]);
  section("💥 Biggest Blowouts", DATA.record_book.biggest_margins,
    [{key:"winner",label:"Winner"},{key:"margin",label:"Margin",fmt:v=>v.toFixed(1)},
     {key:"loser",label:"Loser"},{key:"season",label:"When",fmt:(_ ,r)=>wk(r)}]);
  section("😬 Closest Games", DATA.record_book.closest_games,
    [{key:"winner",label:"Winner"},{key:"margin",label:"Margin",fmt:v=>v.toFixed(1)},
     {key:"loser",label:"Loser"},{key:"season",label:"When",fmt:(_ ,r)=>wk(r)}]);
  section("📈 Highest Combined", DATA.record_book.highest_combined,
    [{key:"total",label:"Total",fmt:v=>v.toFixed(1)},{key:"home_owner",label:"Home"},
     {key:"away_owner",label:"Away"},{key:"season",label:"When",fmt:(_ ,r)=>wk(r)}]);
  if(DATA.record_book.ties.length)
    section("🤝 Ties", DATA.record_book.ties,
      [{key:"owner_a",label:"Team A"},{key:"owner_b",label:"Team B"},
       {key:"score",label:"Score",fmt:v=>v.toFixed(1)},{key:"season",label:"When",fmt:(_ ,r)=>wk(r)}]);
};
```

- [ ] **Step 2: Build, open, verify** — all record sections render; highest score ≈ 341 (Spark, 2011). No console errors.

- [ ] **Step 3: Commit** — `git commit -am "feat: Record Book tab"`

---

### Task 19: Owner Deep Dive tab

**Files:** Modify `dashboard/index.html`.

**Interfaces:** Consumes `DATA.owner_careers`, `DATA.team_names`. Registers `RENDERERS.owner`. Owner `<select>`; Chart.js line of season rank over time.

- [ ] **Step 1: Add the renderer**

```javascript
RENDERERS.owner = function(){
  const root=document.getElementById("tab-owner"); root.innerHTML="";
  const sel=el("select",{class:"season-select"});
  OWNERS.forEach(o=>sel.append(el("option",{value:o},o)));
  root.append(el("div",{class:"card"}, el("div",{class:"card-title"},"Select Owner"), sel));
  const body=el("div"); root.append(body);
  let chart=null;
  function draw(owner){
    if(chart){ chart.destroy(); chart=null; }
    body.innerHTML="";
    const c=DATA.owner_careers[owner];
    const head=el("div",{class:"card"}, el("div",{class:"card-title"},owner),
      el("div",{}, `🏆 Titles: ${c.titles.join(", ")||"none"}`),
      el("div",{}, `💩 Last place: ${c.last_places.join(", ")||"none"}`),
      el("div",{}, `🤝 Top rival (most losses to): ${c.top_rival||"—"}`),
      el("div",{}, c.best_game?`🔥 Best game: ${c.best_game.score} (${c.best_game.season} Wk${c.best_game.week}) vs ${c.best_game.opponent}`:""),
      el("div",{}, c.worst_game?`🧊 Worst game: ${c.worst_game.score} (${c.worst_game.season} Wk${c.worst_game.week}) vs ${c.worst_game.opponent}`:""));
    body.append(head);
    const chartCard=el("div",{class:"card"}, el("div",{class:"card-title"},"Finish by Season (lower = better)"));
    const cw=el("div",{class:"chart-wrap"}); const canvas=el("canvas"); cw.append(canvas);
    chartCard.append(cw); body.append(chartCard);
    const seasons=c.seasons;
    chart=new Chart(canvas,{type:"line",data:{labels:seasons.map(s=>s.season),
      datasets:[{label:"Power Rank",data:seasons.map(s=>s.rank),
        borderColor:OWNER_COLORS[owner],backgroundColor:OWNER_COLORS[owner],tension:0.2}]},
      options:{scales:{y:{reverse:true,min:1,ticks:{stepSize:1}}},plugins:{legend:{display:false}}}});
    const card=el("div",{class:"card"}, el("div",{class:"card-title"},"Season History"));
    const wrap=el("div",{class:"table-scroll"}); card.append(wrap); body.append(card);
    renderTable(wrap,[{key:"season",label:"Year"},{key:"rank",label:"Finish"},
      {key:"wins",label:"W"},{key:"losses",label:"L"},
      {key:"avg_score",label:"Avg",fmt:v=>v.toFixed(1)},
      {key:"made_playoffs",label:"Playoffs",fmt:v=>v?"✓":""}], seasons);
  }
  sel.addEventListener("change",()=>draw(sel.value)); draw(OWNERS[0]);
};
```

- [ ] **Step 2: Build, open, verify** — selecting an owner shows titles/rivals/best-worst, a rank-over-time line chart (Y reversed), and season table. Switching owners doesn't leak charts (old chart destroyed). No console errors.

- [ ] **Step 3: Commit** — `git commit -am "feat: Owner Deep Dive tab"`

---

### Task 20: Visual polish pass + full cross-tab verification

**REQUIRED SUB-SKILL:** invoke `frontend-design` for the polish pass (typography scale, spacing rhythm, card elevation, accent usage, header stat treatment, hover/active states, empty states). Use the `claude-in-chrome` skill to drive the browser verification.

**Files:** Modify `dashboard/index.html` (CSS + minor markup only; no data-shape changes).

- [ ] **Step 1: Populate header stats** — wire the `.header` stats to real values: number of seasons (`DATA.meta.seasons.length`), total games (`DATA.meta.total_games`), and the most-titled owner. Add this to the shell script's `DOMContentLoaded` handler.

- [ ] **Step 2: Responsive + polish** — verify `@media (max-width:900px)` collapses `.grid2`/`.grid3` to one column, nav scrolls horizontally, tables scroll inside `.table-scroll`. Apply the frontend-design refinements.

- [ ] **Step 3: Cross-tab browser check** — build, then open each of the 6 tabs; confirm every tab renders real data, charts draw, selects work, and the console is error-free on all tabs.

Run: `python -m build.build_data`
Then load `dashboard/index.html` and click through all tabs.
Expected: no console errors; all six tabs populated.

- [ ] **Step 4: Commit** — `git commit -am "style: responsive polish and header stats"`

---

### Task 21: README, hosting (GitHub Pages), and push

**Files:** Create `README.md`; verify `.gitignore`; configure git identity and Pages.

- [ ] **Step 1: Write `README.md`** modeled on the baseball project:

```markdown
# 🏈 Fantasy Football — League History & Valuation

Tooling and history for a 12-manager fantasy football league running since 2011.

- **League History** — 15 seasons (2011–2025) of standings, records, rivalries,
  and per-owner history in an interactive dashboard. *(Phase 1 — done.)*
- **Valuation & Draft Models** — player valuation + draft tools (ESPN data). *(Planned.)*

## Dashboard
Open `dashboard/index.html` in any modern browser — no build step or server needed.
Six tabs: Overview, All-Time Rankings, Season-by-Season, Head-to-Head, Record Book,
Owner Deep Dive.

**Hosted:** served via GitHub Pages from `dashboard/`.

## Rebuild the data
Source spreadsheets live in `data/` (kept local, gitignored). To regenerate:
`python -m build.build_data` — parses the spreadsheets, reconciles scores, and
embeds fresh data into `dashboard/index.html`. Review `build/reconciliation.md`
for any source discrepancies.

## Data sources
- `data/League Schedule History.xlsx` — primary source (every game incl. playoffs).
- `data/The Gridiron.xlsx` — validation cross-check + curated champions list.
```

- [ ] **Step 2: (Optional) reset git identity to personal email** before pushing:

```bash
git config user.email "mattjandreau@protonmail.com"
git config user.name "Matt Jandreau"
```

- [ ] **Step 3: Commit and push**

```bash
git add README.md
git commit -m "docs: project README"
git push origin main
```

- [ ] **Step 4: Enable GitHub Pages** — on GitHub → repo Settings → Pages → deploy from `main`. Because the dashboard lives in `dashboard/`, either set the Pages source folder appropriately or add a root redirect. Simplest: set Pages to serve from `/ (root)` and add a root `index.html` that redirects to `dashboard/`, OR move the dashboard to repo root. **Decision for execution:** copy the built dashboard to a root `index.html` as part of the build (add one line to `build_data.py` writing the same injected file to `ROOT/index.html`), so Pages serves it from root directly. Confirm the live URL loads for a non-logged-in viewer.

- [ ] **Step 5: Commit any hosting tweaks** — `git commit -am "chore: GitHub Pages hosting"` and push.

---

## Self-Review

**Spec coverage** (each spec section → task):
- League History primary / Gridiron secondary → Tasks 2, 5, 6 (reconcile, League History wins).
- Owner name normalization → Task 3.
- Regular vs playoff split; standings regular-only → Tasks 2, 8.
- Power Index exact formula → Task 8 (formula in Global Constraints).
- Reconciliation report → Task 6, surfaced in Task 12.
- Curated champions incl. 2023 Buffalo Joe, 2025 Walter → Task 7.
- Team names from League History → Task 4.
- Six tabs → Tasks 14–19.
- Football visual identity → Tasks 13, 20 (frontend-design).
- Self-contained + embedded data → Tasks 11, 13.
- GitHub Pages hosting + gitignored xlsx → Tasks 1, 21.
- Head-to-head engine → Task 9 + Task 17.
- Record book, owner careers → Task 9 + Tasks 18, 19.

**Placeholder scan:** No TBDs; all code blocks are complete and runnable.

**Type consistency:** `league_data.json` contract is defined once up front; Task 10 assembles exactly those keys; Tasks 14–19 read exactly those keys. `standings()` row shape (Task 8) is reused by Task 9 (`owner_careers`) and Tasks 14–16, 19. `head_to_head` `a|b` sorted-key convention is defined in Task 9 and consumed in Task 17.

**Known execution notes:**
- Pre-2015 co-manager manager strings may need extra `_RULES` entries (Task 4, Step 4) — verify against the sheet before mapping.
- All-time W/L will differ slightly from the Gridiron's historical figures because League History wins score conflicts (2021/2023). Tests assert structure and stable facts, not the Gridiron's exact numbers.
- Frontend tabs are verified in-browser, not unit-tested (stated convention at Phase 2 start).









