"""Assemble the playoff-odds payload the dashboard embeds.

The dashboard already ships ~1.45 MB of inlined JSON, so this payload is kept
deliberately lean:

  * short keys -- p (odds), h (hindsight), s (status), w/l/t (record)
  * seed distributions ONLY for a season still in progress, where "what seed am
    I heading for" is a live question. For a finished season the final-week
    distribution is a point mass and says nothing.
  * per-week points-for is dropped; only the final standings carry it.

Status is a single character: a=alive, c=clinched, e=eliminated.
"""

import json
from pathlib import Path

from build.playoff_odds import N_SIMS, season_curves, season_format
from build.scoring import FITTED_LAMBDA

_STATUS = {"alive": "a", "clinched": "c", "eliminated": "e"}


def load_schedule(espn_dir, season):
    """[(week, home_owner, away_owner)] from the ESPN cache, or None.

    Only needed for a season still being played -- completed seasons have their
    schedule implicitly in the game results themselves.
    """
    path = Path(espn_dir) / f"league_{season}.json"
    if not path.exists():
        return None
    blob = json.loads(path.read_text(encoding="utf-8"))
    rows = blob.get("schedule")
    if not rows:
        return None

    from build.normalize import owner_from_manager
    by_id = {}
    for team in blob.get("teams", []):
        owners = team.get("owners") or []
        if not owners:
            continue
        try:
            by_id[team["team_id"]] = owner_from_manager(
                f"{owners[0].get('first', '')} {owners[0].get('last', '')}")
        except ValueError:
            return None

    out = []
    for row in rows:
        home, away = by_id.get(row["home_team_id"]), by_id.get(row["away_team_id"])
        if not home or not away:
            return None
        out.append((row["week"], home, away))
    return sorted(out)


def _compact(curves, in_progress):
    weeks = []
    for wk in curves["weeks"]:
        teams = {}
        for owner, rec in wk["teams"].items():
            teams[owner] = {"p": rec["p"], "h": rec["p_hindsight"],
                            "s": _STATUS[rec["status"]], "w": rec["wins"],
                            "l": rec["losses"], "t": rec["ties"]}
        weeks.append({"week": wk["week"], "teams": teams})

    out = {"season": curves["season"], "owners": curves["owners"],
           "reg_weeks": curves["reg_weeks"],
           "playoff_spots": curves["playoff_spots"],
           "in_progress": in_progress,
           "weeks": weeks,
           "made_playoffs": curves["made_playoffs"],
           "all_play": curves["all_play"],
           "final": curves["final"],
           "story": curves["story"]}

    if in_progress:
        # The live season is the only place a seed distribution earns its bytes,
        # and only at the latest week that has actually been played.
        played = max((w["week"] for w in curves["weeks"]
                      if any(t["wins"] + t["losses"] + t["ties"] > 0
                             for t in w["teams"].values())), default=0)
        latest = next((w for w in curves["weeks"] if w["week"] == played),
                      curves["weeks"][0])
        out["seed_dist"] = {o: latest["teams"][o]["seed_dist"]
                            for o in curves["owners"]}
        out["current_week"] = played
    return out


def build_odds(games, espn_dir, seasons=None, n_sims=N_SIMS, verbose=False):
    """{"seasons": [...], "by_season": {...}} for every season we can model."""
    espn_dir = Path(espn_dir)
    if seasons is None:
        seasons = sorted({int(p.stem.split("_")[1])
                          for p in espn_dir.glob("settings_*.json")})

    by_season, done = {}, []
    for season in seasons:
        try:
            fmt = season_format(espn_dir, season)
        except (FileNotFoundError, KeyError):
            continue
        if not fmt.get("reg_weeks") or not fmt.get("playoff_spots"):
            continue

        played = [g for g in games if g["season"] == season and g["phase"] == "regular"]
        schedule = load_schedule(espn_dir, season)
        weeks_played = max((g["week"] for g in played), default=0)
        in_progress = bool(schedule) and weeks_played < fmt["reg_weeks"]

        if not played:
            # Nothing to model yet. A season that has drafted already publishes
            # its full schedule, which is enough for season_curves to take the
            # owners from -- but the scoring model is fit from played games and
            # standings come from the results table, so both are empty until
            # week 1 is in the books.
            continue

        curves = season_curves(games, season, fmt, n_sims=n_sims,
                               schedule=schedule if in_progress else None)
        if curves is None:
            continue
        by_season[str(season)] = _compact(curves, in_progress)
        done.append(season)
        if verbose:
            print(f"  {season}: {len(curves['owners'])} owners, "
                  f"{fmt['reg_weeks']} weeks, {fmt['playoff_spots']} spots"
                  f"{' (in progress)' if in_progress else ''}")

    return {"seasons": done, "by_season": by_season, "lambda": FITTED_LAMBDA,
            "n_sims": n_sims}
