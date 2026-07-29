"""Lineup analytics from the ESPN box-score cache (2019+).

For every owner-week: actual starter points vs the optimal lineup that week
(same slot structure, position eligibility), the points wasted on the bench,
plus the biggest start/sit blunders and benched-monster performances.
Only aggregates leave this module — raw box scores stay local."""

import json
import re
from collections import defaultdict
from pathlib import Path

from build.normalize import owner_from_manager

# Slots that don't score
_NON_STARTING = {"BE", "IR"}
# Which positions may fill which slots
_ELIGIBLE = {
    "QB": {"QB", "OP"},
    "RB": {"RB", "RB/WR", "RB/WR/TE", "FLEX", "OP"},
    "WR": {"WR", "RB/WR", "WR/TE", "RB/WR/TE", "FLEX", "OP"},
    "TE": {"TE", "WR/TE", "RB/WR/TE", "FLEX", "OP"},
    "K": {"K"},
    "D/ST": {"D/ST"},
    "DT": {"DT", "DL", "DP"}, "DE": {"DE", "DL", "DP"}, "LB": {"LB", "DP"},
    "CB": {"CB", "DB", "DP"}, "S": {"S", "DB", "DP"},
}


def owner_for_team(team):
    """Map an ESPN team's owner list to a short owner name."""
    for o in team.get("owners", []):
        first = (o.get("first") or "").strip()
        last = (o.get("last") or "").strip()
        full = f"{first} {last}".strip()
        if not full:
            continue
        # espn accounts may say "Joe Klimczak" where sheets said "Joseph"
        if re.search(r"klimczak", last, re.I) and re.match(r"jo", first, re.I):
            return "Joe Klim"
        try:
            return owner_from_manager(full)
        except ValueError:
            continue
    raise ValueError(f"cannot map ESPN team to owner: {team['team_name']!r} "
                     f"owners={team.get('owners')}")


def _optimal_points(lineup):
    """Best achievable starter total given the week's actual slot structure."""
    starters = [p for p in lineup if p["slot"] not in _NON_STARTING]
    slots = [p["slot"] for p in starters]
    players = [p for p in lineup if p["slot"] not in {"IR"}]
    # Fill scarcest slots first so FLEX-like slots take the leftovers.
    slot_order = sorted(slots, key=lambda s: sum(
        1 for pos, elig in _ELIGIBLE.items() if s in elig))
    used = set()
    total = 0.0
    for slot in slot_order:
        best, best_pts = None, None
        for i, p in enumerate(players):
            if i in used:
                continue
            elig = _ELIGIBLE.get(p.get("position") or "", set())
            if slot in elig or slot == p["slot"]:
                if best_pts is None or p["points"] > best_pts:
                    best, best_pts = i, p["points"]
        if best is not None:
            used.add(best)
            total += best_pts
    return total


def build_lineups(espn_dir):
    espn_dir = Path(espn_dir)
    acc = defaultdict(lambda: {"actual": 0.0, "optimal": 0.0, "games": 0})
    per_season = defaultdict(lambda: defaultdict(
        lambda: {"actual": 0.0, "optimal": 0.0, "games": 0}))
    blunders = []
    bench = []

    for bs_path in sorted(espn_dir.glob("boxscores_*.json")):
        year = int(bs_path.stem.split("_")[1])
        league = json.loads((espn_dir / f"league_{year}.json").read_text())
        owner_by_id = {t["team_id"]: owner_for_team(t) for t in league["teams"]}
        max_week = (league.get("reg_season_weeks") or 14) + 3
        data = json.loads(bs_path.read_text())
        for wk, matchups in data["weeks"].items():
            if int(wk) > max_week:
                continue
            for m in matchups:
                for side in ("home", "away"):
                    tid = m[f"{side}_team_id"]
                    if tid is None:
                        continue
                    owner = owner_by_id[tid]
                    lineup = m[f"{side}_lineup"]
                    if not lineup:
                        continue
                    actual = sum(p["points"] for p in lineup
                                 if p["slot"] not in _NON_STARTING)
                    optimal = max(_optimal_points(lineup), actual)
                    acc[owner]["actual"] += actual
                    acc[owner]["optimal"] += optimal
                    acc[owner]["games"] += 1
                    s = per_season[str(year)][owner]
                    s["actual"] += actual
                    s["optimal"] += optimal
                    s["games"] += 1
                    missed = optimal - actual
                    if missed > 0:
                        benched = [p for p in lineup if p["slot"] == "BE"]
                        star = max(benched, key=lambda p: p["points"],
                                   default=None)
                        if star and missed >= 15:
                            blunders.append({
                                "owner": owner, "season": year, "week": int(wk),
                                "wasted": round(missed, 1),
                                "benched_star": star["name"],
                                "star_points": round(star["points"], 1)})
                    for p in lineup:
                        if p["slot"] == "BE" and p["points"] >= 30:
                            bench.append({"owner": owner, "season": year,
                                          "week": int(wk), "player": p["name"],
                                          "points": round(p["points"], 1)})

    def rows(scope):
        out = []
        for owner, a in scope.items():
            out.append({"owner": owner,
                        "actual": round(a["actual"], 1),
                        "optimal": round(a["optimal"], 1),
                        "wasted": round(a["optimal"] - a["actual"], 1),
                        "efficiency": round(a["actual"] / a["optimal"], 4)
                                      if a["optimal"] else 1.0,
                        "games": a["games"]})
        out.sort(key=lambda r: -r["efficiency"])
        return out

    blunders.sort(key=lambda b: -b["wasted"])
    bench.sort(key=lambda b: -b["points"])
    return {"efficiency": rows(acc),
            "by_season": {y: rows(s) for y, s in sorted(per_season.items())},
            "blunders": blunders[:12],
            "bench_records": bench[:12],
            "all_time_teams": all_time_teams(espn_dir)}


def final_standings(espn_dir):
    """owner -> {year: final post-playoff placement} from the ESPN cache.
    Validated against the curated champions (place 1 == champion, all years)."""
    out = defaultdict(dict)
    for lg_path in sorted(Path(espn_dir).glob("league_*.json")):
        league = json.loads(lg_path.read_text())
        for t in league["teams"]:
            place = t.get("final_standing")
            if place:
                out[owner_for_team(t)][str(league["year"])] = place
    return dict(out)


# Best-ever lineup slots per owner (points scored while on their roster).
# Mirrors the league's actual lineup: offense + D/ST + one DL/LB/DB (IDP).
_TEAM_SLOTS = [("QB", {"QB"}), ("RB1", {"RB"}), ("RB2", {"RB"}),
               ("WR1", {"WR"}), ("WR2", {"WR"}), ("TE", {"TE"}),
               ("K", {"K"}), ("D/ST", {"D/ST"}),
               ("DL", {"DE", "DT"}), ("LB", {"LB"}), ("DB", {"CB", "S"})]


def all_time_teams(espn_dir):
    """For each owner: the highest-scoring player they've ever rostered at each
    lineup slot, by total points accrued while on that owner's roster (2019+)."""
    espn_dir = Path(espn_dir)
    tally = defaultdict(lambda: defaultdict(
        lambda: {"points": 0.0, "seasons": set(), "pos": None, "name": None}))
    for bs_path in sorted(espn_dir.glob("boxscores_*.json")):
        year = int(bs_path.stem.split("_")[1])
        league = json.loads((espn_dir / f"league_{year}.json").read_text())
        owner_by_id = {t["team_id"]: owner_for_team(t) for t in league["teams"]}
        max_week = (league.get("reg_season_weeks") or 14) + 3
        data = json.loads(bs_path.read_text())
        counted = set()
        for wk, matchups in data["weeks"].items():
            if int(wk) > max_week:
                continue
            for m in matchups:
                for side in ("home", "away"):
                    tid = m[f"{side}_team_id"]
                    if tid is None:
                        continue
                    owner = owner_by_id[tid]
                    for p in m[f"{side}_lineup"]:
                        key = (owner, p["player_id"], int(wk), year)
                        if key in counted:
                            continue
                        counted.add(key)
                        t = tally[owner][p["player_id"]]
                        t["points"] += p["points"]
                        t["seasons"].add(year)
                        t["name"] = p["name"]
                        if p.get("position"):
                            t["pos"] = p["position"]

    out = {}
    for owner, players in tally.items():
        ranked = sorted(players.values(), key=lambda t: -t["points"])
        used = set()
        team = []
        for slot, poses in _TEAM_SLOTS:
            best = next((t for t in ranked
                         if t["pos"] in poses and id(t) not in used), None)
            if best:
                used.add(id(best))
                yrs = sorted(best["seasons"])
                span = str(yrs[0]) if len(yrs) == 1 else f"{yrs[0]}–{yrs[-1]}"
                team.append({"slot": slot, "player": best["name"],
                             "pos": best["pos"], "points": round(best["points"], 1),
                             "seasons": span})
            else:
                team.append({"slot": slot, "player": "—", "pos": "/".join(sorted(poses)),
                             "points": 0, "seasons": ""})
        out[owner] = team
    return out
