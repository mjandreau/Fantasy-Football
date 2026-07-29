"""Draft history from the ESPN cache: every pick 2011-2025, the first-overall
gallery, and (2019+, where box scores exist) value analysis — steals, busts,
and per-owner draft grades based on pick slot vs actual season production."""

import json
from collections import defaultdict
from pathlib import Path

from build.lineups import owner_for_team


def _season_points(espn_dir, year):
    """player_id -> total fantasy points scored that season (any roster slot)."""
    path = Path(espn_dir) / f"boxscores_{year}.json"
    if not path.exists():
        return None
    league = json.loads((Path(espn_dir) / f"league_{year}.json").read_text())
    max_week = (league.get("reg_season_weeks") or 14) + 3
    totals = defaultdict(float)
    counted = set()   # (player, week) — avoid double-counting repeated matchups
    data = json.loads(path.read_text())
    for wk, matchups in data["weeks"].items():
        if int(wk) > max_week:
            continue
        for m in matchups:
            for side in ("home", "away"):
                for p in m[f"{side}_lineup"]:
                    key = (p["player_id"], int(wk))
                    if key in counted:
                        continue
                    counted.add(key)
                    totals[p["player_id"]] += p["points"]
    return totals


def build_drafts(espn_dir):
    espn_dir = Path(espn_dir)
    years = {}
    first_overall = []
    steals, busts = [], []
    grade_acc = defaultdict(lambda: {"delta": 0.0, "points": 0.0, "picks": 0})

    for lg_path in sorted(espn_dir.glob("league_*.json")):
        year = int(lg_path.stem.split("_")[1])
        league = json.loads(lg_path.read_text())
        owner_by_id = {t["team_id"]: owner_for_team(t) for t in league["teams"]}
        n_teams = len(league["teams"])
        picks = []
        for p in league["draft"]:
            overall = (p["round"] - 1) * n_teams + p["round_pick"]
            picks.append({
                "overall": overall, "round": p["round"], "pick": p["round_pick"],
                "player": p["player_name"], "player_id": p["player_id"],
                "owner": owner_by_id.get(p["team_id"], p["team_name"]),
                "team_name": p["team_name"], "keeper": bool(p.get("keeper")),
            })
        picks.sort(key=lambda x: x["overall"])
        years[str(year)] = {"teams": n_teams, "picks": picks}
        p1 = picks[0]
        first_overall.append({"year": year, "player": p1["player"],
                              "owner": p1["owner"], "team_name": p1["team_name"]})

        # Value analysis where scoring exists (2019+)
        totals = _season_points(espn_dir, year)
        if totals is None:
            continue
        scored = [{**pk, "points": round(totals.get(pk["player_id"], 0.0), 1)}
                  for pk in picks]
        # Rank drafted players by actual production; delta = slots outperformed
        by_points = sorted(scored, key=lambda x: -x["points"])
        points_rank = {pk["player_id"]: i + 1 for i, pk in enumerate(by_points)}
        for pk in scored:
            delta = pk["overall"] - points_rank[pk["player_id"]]
            entry = {"year": year, "player": pk["player"], "owner": pk["owner"],
                     "overall": pk["overall"], "round": pk["round"],
                     "points": pk["points"], "delta": delta}
            steals.append(entry)
            if pk["round"] <= 4:
                busts.append(entry)
            g = grade_acc[pk["owner"]]
            g["delta"] += delta
            g["points"] += pk["points"]
            g["picks"] += 1

    steals.sort(key=lambda e: -e["delta"])
    busts.sort(key=lambda e: e["delta"])
    grades = [{"owner": o, "avg_delta": round(g["delta"] / g["picks"], 1),
               "total_points": round(g["points"], 0), "picks": g["picks"]}
              for o, g in grade_acc.items()]
    grades.sort(key=lambda r: -r["avg_delta"])
    return {"years": years,
            "first_overall": sorted(first_overall, key=lambda x: x["year"]),
            "value": {"steals": steals[:12], "busts": busts[:12],
                      "grades": grades}}
