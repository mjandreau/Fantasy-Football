import json
from pathlib import Path
from build.assemble import assemble
from build.inject import inject_into_dashboard

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BUILD = ROOT / "build"
DASHBOARD = ROOT / "dashboard" / "index.html"
GENERATED = "2026-08-24"  # bump when rebuilding


def main():
    data, report = assemble(DATA / "League Schedule History.xlsx",
                            DATA / "The Gridiron.xlsx", generated=GENERATED,
                            espn_dir=DATA / "espn")
    (BUILD / "league_data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (BUILD / "reconciliation.md").write_text(report, encoding="utf-8")
    if DASHBOARD.exists():
        inject_into_dashboard(data, DASHBOARD)
        print(f"Injected data into {DASHBOARD}")
    print(f"Wrote league_data.json ({data['meta']['total_games']} games) and reconciliation.md")
    odds = data.get("odds")
    if odds:
        for fix in odds.get("tie_repairs", []):
            print(f"  tie repaired: {fix['season']} wk{fix['week']} "
                  f"{fix['winner']} beat {fix['loser']} (workbook had a tie)")
        print(f"  playoff odds: {len(odds['seasons'])} seasons "
              f"({odds['seasons'][0]}-{odds['seasons'][-1]})")


if __name__ == "__main__":
    main()
