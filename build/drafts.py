"""Draft history from the ESPN cache: every pick 2011-2025, the first-overall
gallery, and (2019+, where box scores exist) value analysis — steals, busts,
and per-owner draft grades based on pick slot vs actual season production."""

import json
from collections import defaultdict
from pathlib import Path

from build.lineups import owner_for_team

# The league runs two separate drafts each year. The main ("offensive") draft
# includes K and team D/ST; the defensive draft is individual defenders only
# (3 rounds: DL/LB/DB). Everything side-specific keys off position.
_OFF_POS = {"QB", "RB", "WR", "TE", "K", "FB", "D/ST"}


def _side(pos):
    return "OFF" if (pos in _OFF_POS or pos == "?") else "DEF"


def _season_meta(espn_dir, year):
    """player_id -> (position, pro_team) as seen in that season's box scores."""
    path = Path(espn_dir) / f"boxscores_{year}.json"
    if not path.exists():
        return {}
    meta = {}
    data = json.loads(path.read_text())
    for matchups in data["weeks"].values():
        for m in matchups:
            for side in ("home", "away"):
                for p in m[f"{side}_lineup"]:
                    if p["player_id"] not in meta and p.get("position"):
                        meta[p["player_id"]] = (p["position"], p.get("pro_team"))
    return meta


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

    core_path = espn_dir / "players_core.json"
    core = json.loads(core_path.read_text()) if core_path.exists() else {}

    for lg_path in sorted(espn_dir.glob("league_*.json")):
        year = int(lg_path.stem.split("_")[1])
        league = json.loads(lg_path.read_text())
        if not league["draft"]:
            continue   # rolled-over season shell (no draft held yet)
        owner_by_id = {t["team_id"]: owner_for_team(t) for t in league["teams"]}
        n_teams = len(league["teams"])
        season_meta = _season_meta(espn_dir, year)
        totals = _season_points(espn_dir, year)
        picks = []
        for p in league["draft"]:
            overall = (p["round"] - 1) * n_teams + p["round_pick"]
            pid = p["player_id"]
            sm = season_meta.get(pid)
            pos = (sm[0] if sm else None) \
                or (core.get(str(pid)) or {}).get("pos") \
                or ("D/ST" if pid < 0 else "?")
            picks.append({
                "overall": overall, "round": p["round"], "pick": p["round_pick"],
                "player": p["player_name"], "player_id": pid,
                "pos": pos, "side": _side(pos),
                "pro_team": sm[1] if sm else None,
                "points": round(totals.get(pid, 0.0), 1) if totals is not None else None,
                "owner": owner_by_id.get(p["team_id"], p["team_name"]),
                "team_name": p["team_name"], "keeper": bool(p.get("keeper")),
            })
        picks.sort(key=lambda x: x["overall"])
        # side_overall: pick number WITHIN that side's own draft
        for s in ("OFF", "DEF"):
            for i, pk in enumerate([x for x in picks if x["side"] == s], 1):
                pk["side_overall"] = i
        years[str(year)] = {"teams": n_teams, "picks": picks}
        off1 = next(p for p in picks if p["side"] == "OFF")
        def1 = next((p for p in picks if p["side"] == "DEF"), None)
        first_overall.append({"year": year, "player": off1["player"],
                              "owner": off1["owner"], "team_name": off1["team_name"],
                              "def_player": def1["player"] if def1 else None,
                              "def_owner": def1["owner"] if def1 else None})

        # Value analysis where scoring exists (2019+) — ranked WITHIN each
        # side's draft so defenders aren't judged against offensive scoring.
        if totals is None:
            continue
        for s in ("OFF", "DEF"):
            side_picks = [pk for pk in picks if pk["side"] == s]
            by_points = sorted(side_picks, key=lambda x: -x["points"])
            points_rank = {pk["player_id"]: i + 1 for i, pk in enumerate(by_points)}
            for pk in side_picks:
                delta = pk["side_overall"] - points_rank[pk["player_id"]]
                entry = {"year": year, "player": pk["player"], "owner": pk["owner"],
                         "overall": pk["side_overall"], "round": pk["round"],
                         "pos": pk["pos"], "side": s,
                         "points": pk["points"], "delta": delta}
                steals.append(entry)
                if s == "OFF" and pk["side_overall"] <= 4 * n_teams:
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
