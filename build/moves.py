"""Roster-churn analytics from the ESPN cache.

Moves: per-owner transaction counters (adds/drops/trades, back to 2011) joined
with season finishes — does churn win?  Waivers: in-season pickups mined from
weekly roster diffs (2019+), ranked by points scored after joining."""

import json
from collections import defaultdict
from pathlib import Path

from build.lineups import owner_for_team


def build_moves(espn_dir):
    """Career + per-season transaction counters joined with final standing."""
    espn_dir = Path(espn_dir)
    career = defaultdict(lambda: {"adds": 0, "drops": 0, "trades": 0,
                                  "faab": 0, "seasons": 0})
    scatter = []          # one point per owner-season: churn vs finish
    for lg_path in sorted(espn_dir.glob("league_*.json")):
        league = json.loads(lg_path.read_text())
        year = league["year"]
        if not any((t.get("wins") or 0) + (t.get("losses") or 0)
                   for t in league["teams"]):
            continue   # rolled-over season shell (no games played yet)
        for t in league["teams"]:
            owner = owner_for_team(t)
            adds = t.get("acquisitions") or 0
            c = career[owner]
            c["adds"] += adds
            c["drops"] += t.get("drops") or 0
            c["trades"] += t.get("trades") or 0
            c["faab"] += t.get("faab_spent") or 0
            c["seasons"] += 1
            if t.get("final_standing"):
                scatter.append({"owner": owner, "season": year,
                                "adds": adds, "finish": t["final_standing"]})
    table = [{"owner": o, **c,
              "adds_per_season": round(c["adds"] / c["seasons"], 1)}
             for o, c in career.items()]
    table.sort(key=lambda r: -r["adds_per_season"])

    # Simple churn-vs-finish signal: average finish of high-churn vs low-churn
    # owner-seasons (split at the median adds).
    if scatter:
        srt = sorted(s["adds"] for s in scatter)
        median = srt[len(srt) // 2]
        hi = [s["finish"] for s in scatter if s["adds"] > median]
        lo = [s["finish"] for s in scatter if s["adds"] <= median]
        signal = {"median_adds": median,
                  "high_churn_avg_finish": round(sum(hi) / len(hi), 2) if hi else None,
                  "low_churn_avg_finish": round(sum(lo) / len(lo), 2) if lo else None}
    else:
        signal = None
    return {"career": table, "scatter": scatter, "signal": signal}


def build_waivers(espn_dir, top_n=15):
    """In-season pickups reconstructed from weekly roster diffs (2019+).

    A pickup = a player on an owner's roster in week w who was not on it in
    any earlier week and was not drafted by that owner that season. Credited
    with all points scored while on that owner's roster from week w on."""
    espn_dir = Path(espn_dir)
    pickups = []
    best_by_owner = defaultdict(lambda: None)
    for bs_path in sorted(espn_dir.glob("boxscores_*.json")):
        year = int(bs_path.stem.split("_")[1])
        league = json.loads((espn_dir / f"league_{year}.json").read_text())
        owner_by_id = {t["team_id"]: owner_for_team(t) for t in league["teams"]}
        drafted_by = {}
        for p in league["draft"]:
            drafted_by[p["player_id"]] = owner_by_id.get(p["team_id"])
        max_week = (league.get("reg_season_weeks") or 14) + 3
        data = json.loads(bs_path.read_text())
        weeks = sorted((int(w) for w in data["weeks"]), key=int)
        seen = defaultdict(set)          # owner -> player_ids seen so far
        acc = {}                          # (owner, pid) -> pickup record
        for wk in weeks:
            if wk > max_week:
                continue
            for m in data["weeks"][str(wk)]:
                for side in ("home", "away"):
                    tid = m[f"{side}_team_id"]
                    if tid is None:
                        continue
                    owner = owner_by_id[tid]
                    for p in m[f"{side}_lineup"]:
                        pid = p["player_id"]
                        key = (owner, pid)
                        if key not in acc:
                            if pid in seen[owner]:
                                continue
                            if wk == weeks[0] or drafted_by.get(pid) == owner:
                                seen[owner].add(pid)   # opening roster / own draftee
                                continue
                            acc[key] = {"owner": owner, "player": p["name"],
                                        "pos": p.get("position"),
                                        "season": year, "week": wk,
                                        "points": 0.0,
                                        "undrafted": pid not in drafted_by}
                        acc[key]["points"] += p["points"]
                        seen[owner].add(pid)
        for rec in acc.values():
            rec["points"] = round(rec["points"], 1)
            if rec["points"] > 0:
                pickups.append(rec)
                cur = best_by_owner[rec["owner"]]
                if cur is None or rec["points"] > cur["points"]:
                    best_by_owner[rec["owner"]] = rec

    pickups.sort(key=lambda r: -r["points"])
    return {"hall_of_fame": pickups[:top_n],
            "best_by_owner": dict(best_by_owner)}


def build_left_on_waivers(espn_dir, top_n=10):
    """Best season totals by players who ended the year as free agents."""
    espn_dir = Path(espn_dir)
    rows = []
    for fa_path in sorted(espn_dir.glob("free_agents_*.json")):
        data = json.loads(fa_path.read_text())
        for p in data["free_agents"]:
            if p["points"] > 0:
                rows.append({"season": data["year"], "player": p["name"],
                             "pos": p.get("position"), "points": p["points"]})
    rows.sort(key=lambda r: -r["points"])
    return rows[:top_n]
