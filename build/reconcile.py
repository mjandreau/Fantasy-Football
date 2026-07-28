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
