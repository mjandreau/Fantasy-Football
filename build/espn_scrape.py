"""Scrape The Gridiron's ESPN league data into local JSON caches.

Pulls, per season 2011-2025: settings, teams (with owners + final standings)
and the full draft. For 2019+ also pulls player-level box scores for every
matchup period. Everything lands in data/espn/ (gitignored). Resumable:
existing files are skipped; pass --force to refetch.

Usage:
  python -m build.espn_scrape                  # fetch anything not yet cached
  python -m build.espn_scrape --refresh 2026   # refetch ONE year (in-season use)
  python -m build.espn_scrape --force          # refetch everything
"""

import datetime
import json
import sys
import time
from pathlib import Path

from espn_api.football import League

ROOT = Path(__file__).resolve().parent.parent
CREDS = ROOT / "data" / "espn_credentials.json"
OUT = ROOT / "data" / "espn"
# Through the current NFL season (a not-yet-created season fails gracefully).
_END = datetime.date.today().year + 1
YEARS = range(2011, _END)
BOX_SCORE_YEARS = range(2019, _END)   # ESPN serves player-level data 2019+
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
        # season transaction counters (survive even for ancient seasons)
        "acquisitions": getattr(t, "acquisitions", 0),
        "drops": getattr(t, "drops", 0),
        "trades": getattr(t, "trades", 0),
        "faab_spent": getattr(t, "acquisition_budget_spent", 0),
        "waiver_rank": getattr(t, "waiver_rank", None),
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


def settings_blob(lg, year):
    """The league's exact rulebook that season — Phase 2's pricing ground truth."""
    s = lg.settings
    return {
        "year": year,
        "name": s.name,
        "reg_season_weeks": getattr(s, "reg_season_count", None),
        "playoff_teams": getattr(s, "playoff_team_count", None),
        "keeper_count": getattr(s, "keeper_count", None),
        "faab": getattr(s, "faab", None),
        "trade_deadline": getattr(s, "trade_deadline", None),
        "roster_slots": getattr(s, "position_slot_counts", None),
        "scoring": getattr(s, "scoring_format", None),
    }


def free_agents_blob(lg, year, size=400):
    """End-of-season free-agent pool with league-scored season totals —
    the replacement-level baseline for valuation work."""
    out = []
    for p in lg.free_agents(size=size):
        out.append({"player_id": p.playerId, "name": p.name,
                    "position": getattr(p, "position", None),
                    "pro_team": getattr(p, "proTeam", None),
                    "points": round(getattr(p, "total_points", 0.0) or 0.0, 1),
                    "projected": round(getattr(p, "projected_total_points", 0.0) or 0.0, 1),
                    "percent_owned": round(getattr(p, "percent_owned", 0.0) or 0.0, 1)})
    return {"year": year, "free_agents": out}


def scrape_core_positions():
    """Position for every drafted player ever, via ESPN's public core athlete
    API (works for long-retired players). Negative ids are D/ST units.
    Resumable: already-fetched ids are skipped."""
    import requests
    path = OUT / "players_core.json"
    existing = json.loads(path.read_text()) if path.exists() else {}
    all_ids = set()
    for lg_path in OUT.glob("league_*.json"):
        for p in json.loads(lg_path.read_text())["draft"]:
            all_ids.add(p["player_id"])
    todo = [i for i in sorted(all_ids) if str(i) not in existing]
    print(f"core positions: {len(existing)} cached, {len(todo)} to fetch")
    for n, pid in enumerate(todo, 1):
        if pid < 0:
            existing[str(pid)] = {"pos": "D/ST"}
            continue
        try:
            r = requests.get("https://sports.core.api.espn.com/v2/sports/"
                             f"football/leagues/nfl/athletes/{pid}", timeout=20)
            pos = ((r.json().get("position") or {}).get("abbreviation")
                   if r.status_code == 200 else None)
            existing[str(pid)] = {"pos": pos or "?"}
        except Exception:
            existing[str(pid)] = {"pos": "?"}
        if n % 100 == 0:
            path.write_text(json.dumps(existing))
            print(f"  {n}/{len(todo)}")
        time.sleep(0.08)
    path.write_text(json.dumps(existing))
    print(f"core positions done: {len(existing)} total")


def main():
    force = "--force" in sys.argv
    creds = json.loads(CREDS.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    # --refresh YEAR: drop that year's cache so it refetches (weekly in-season use)
    if "--refresh" in sys.argv:
        year = sys.argv[sys.argv.index("--refresh") + 1]
        dropped = 0
        for f in OUT.glob(f"*_{year}.json"):
            f.unlink()
            dropped += 1
        print(f"--refresh {year}: dropped {dropped} cached file(s)")
    summary = []
    for year in YEARS:
        lg_path = OUT / f"league_{year}.json"
        bs_path = OUT / f"boxscores_{year}.json"
        st_path = OUT / f"settings_{year}.json"
        fa_path = OUT / f"free_agents_{year}.json"
        need_lg = force or not lg_path.exists()
        need_bs = year in BOX_SCORE_YEARS and (force or not bs_path.exists())
        need_st = force or not st_path.exists()
        need_fa = force or not fa_path.exists()
        if not (need_lg or need_bs or need_st or need_fa):
            summary.append(f"{year}: cached, skipped")
            continue
        try:
            lg = League(league_id=creds["league_id"], year=year,
                        espn_s2=creds["espn_s2"], swid=creds["swid"])
        except Exception as e:
            summary.append(f"{year}: LEAGUE FETCH FAILED ({type(e).__name__})")
            continue
        if need_st:
            try:
                st_path.write_text(json.dumps(settings_blob(lg, year), indent=1))
                summary.append(f"{year}: settings ok")
            except Exception as e:
                summary.append(f"{year}: settings FAILED ({type(e).__name__})")
        if need_fa:
            try:
                fa = free_agents_blob(lg, year)
                fa_path.write_text(json.dumps(fa))
                summary.append(f"{year}: free agents ok ({len(fa['free_agents'])})")
            except Exception as e:
                summary.append(f"{year}: free agents n/a ({type(e).__name__})")
            time.sleep(SLEEP)
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
    scrape_core_positions()
    print("done ->", OUT)


if __name__ == "__main__":
    main()
