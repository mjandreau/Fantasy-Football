from collections import Counter


def flag_conflicts(games, gridiron):
    for g in games:
        conflict = False
        missing = False
        if g["phase"] == "regular":
            key = (g["season"], g["week"], frozenset({g["home_owner"], g["away_owner"]}))
            gr = gridiron.get(key)
            if gr is None:
                missing = True
            else:
                gh = gr.get(g["home_owner"])
                ga = gr.get(g["away_owner"])
                if gh is None or ga is None:
                    missing = True
                else:
                    conflict = (gh != g["home_score"]) or (ga != g["away_score"])
        g["gridiron_conflict"] = conflict
        g["gridiron_missing"] = missing
    return games


def reconciliation_report(games):
    per_season = Counter()
    missing_per = Counter()
    details = []
    for g in games:
        if g.get("gridiron_conflict"):
            per_season[g["season"]] += 1
            details.append(g)
        if g.get("gridiron_missing"):
            missing_per[g["season"]] += 1
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
    lines += ["", "## Regular-season games not found in Gridiron", ""]
    for season in sorted(missing_per):
        lines.append(f"- {season}: {missing_per[season]} game(s) absent from Gridiron")
    if not missing_per:
        lines.append("- None — Gridiron covers every regular-season game.")
    lines += ["", "## Conflict detail", "",
              "| Season | Wk | Matchup | League Hist (home/away) |"]
    lines.append("|---|---|---|---|")
    for g in sorted(details, key=lambda x: (x["season"], x["week"])):
        lines.append(f"| {g['season']} | {g['week']} | "
                     f"{g['home_owner']} vs {g['away_owner']} | "
                     f"{g['home_score']}/{g['away_score']} |")
    return "\n".join(lines) + "\n"
