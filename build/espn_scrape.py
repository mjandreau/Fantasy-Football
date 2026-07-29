"""Scrape The Gridiron's ESPN league data into local JSON caches.

Pulls, per season 2011-2025: settings, teams (with owners + final standings)
and the full draft. For 2019+ also pulls player-level box scores for every
matchup period. Everything lands in data/espn/ (gitignored). Resumable:
existing files are skipped; pass --force to refetch.

Usage: python -m build.espn_scrape [--force]
"""

import json
import sys
import time
from pathlib import Path

from espn_api.football import League

ROOT = Path(__file__).resolve().parent.parent
CREDS = ROOT / "data" / "espn_credentials.json"
OUT = ROOT / "data" / "espn"
YEARS = range(2011, 2026)
BOX_SCORE_YEARS = range(2019, 2026)   # ESPN serves player-level data 2019+
SLEEP = 0.4                           # be polite between requests


def team_blob(t):
    return {
        "team_id": t.team_id,
        "team_name": t.team_name,
        "abbrev": getattr(t, "team_abbrev", None),
        "owners": [
            {"first": o.get("firstName"), "last": o.get("lastName"), "id": o.get("id")}
            if isinstance(o, dict) else {"raw": str(o)}
            for o in (t.owners or [])
        ],
        "wins": t.wins, "losses": t.losses, "ties": getattr(t, "ties", 0),
        "points_for": round(t.points_for, 1),
        "points_against": round(t.points_against, 1),
        "final_standing": getattr(t, "final_standing", None),
        "standing": getattr(t, "standing", None),
    }


def draft_blob(p):
    return {
        "player_id": p.playerId,
        "player_name": p.playerName,
        "round": p.round_num,
        "round_pick": p.round_pick,
        "team_id": p.team.team_id if p.team else None,
        "team_name": p.team.team_name if p.team else None,
        "bid_amount": getattr(p, "bid_amount", 0),
        "keeper": getattr(p, "keeper_status", False),
    }


def player_blob(bp):
    return {
        "player_id": bp.playerId,
        "name": bp.name,
        "slot": bp.slot_position,           # QB/RB/.../BE (bench) /IR
        "position": getattr(bp, "position", None),
        "pro_team": getattr(bp, "proTeam", None),
        "points": round(bp.points, 2),
        "projected": round(getattr(bp, "projected_points", 0.0) or 0.0, 2),
    }


def scrape_league(lg, year):
    return {
        "year": year,
        "name": lg.settings.name,
        "reg_season_weeks": getattr(lg.settings, "reg_season_count", None),
        "playoff_teams": getattr(lg.settings, "playoff_team_count", None),
        "teams": [team_blob(t) for t in lg.teams],
        "draft": [draft_blob(p) for p in lg.draft],
    }


def scrape_box_scores(lg, year):
    weeks = {}
    for wk in range(1, 19):
        try:
            bs = lg.box_scores(wk)
        except Exception:
            break
        if not bs:
            break
        rows = []
        for m in bs:
            rows.append({
                "home_team": m.home_team.team_name if m.home_team else None,
                "home_team_id": m.home_team.team_id if m.home_team else None,
                "home_score": round(m.home_score, 2),
                "home_lineup": [player_blob(p) for p in m.home_lineup],
                "away_team": m.away_team.team_name if m.away_team else None,
                "away_team_id": m.away_team.team_id if m.away_team else None,
                "away_score": round(m.away_score, 2),
                "away_lineup": [player_blob(p) for p in m.away_lineup],
                "is_playoff": getattr(m, "is_playoff", None),
                "matchup_type": getattr(m, "matchup_type", None),
            })
        weeks[str(wk)] = rows
        time.sleep(SLEEP)
    return {"year": year, "weeks": weeks}


def main():
    force = "--force" in sys.argv
    creds = json.loads(CREDS.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    summary = []
    for year in YEARS:
        lg_path = OUT / f"league_{year}.json"
        bs_path = OUT / f"boxscores_{year}.json"
        need_lg = force or not lg_path.exists()
        need_bs = year in BOX_SCORE_YEARS and (force or not bs_path.exists())
        if not need_lg and not need_bs:
            summary.append(f"{year}: cached, skipped")
            continue
        try:
            lg = League(league_id=creds["league_id"], year=year,
                        espn_s2=creds["espn_s2"], swid=creds["swid"])
        except Exception as e:
            summary.append(f"{year}: LEAGUE FETCH FAILED ({type(e).__name__})")
            continue
        if need_lg:
            data = scrape_league(lg, year)
            lg_path.write_text(json.dumps(data, indent=1))
            summary.append(f"{year}: league+draft ok ({len(data['draft'])} picks)")
        time.sleep(SLEEP)
        if need_bs:
            bs = scrape_box_scores(lg, year)
            bs_path.write_text(json.dumps(bs))
            n = sum(len(v) for v in bs["weeks"].values())
            summary.append(f"{year}: box scores ok ({len(bs['weeks'])} weeks, {n} matchups)")
    print("\n".join(summary))
    print("done ->", OUT)


if __name__ == "__main__":
    main()
