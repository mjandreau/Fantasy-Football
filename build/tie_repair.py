"""Repair phantom ties in the workbook using ESPN's authoritative W-L-T.

The League Schedule History workbook is the primary source, but its pre-2018
scores are rounded -- season points-for totals run 3.0 to 5.5 points above
ESPN's for 2013-2017. The rounding collapses four decisive games into apparent
ties:

    2011 wk14  Devin 206.5 - Reid 206.5      ESPN: Devin won
    2013 wk12  Walter 191.0 - Reid 191.0     ESPN: Reid won
    2014 wk5   Spark 197.0 - Walter 197.0    ESPN: Walter won
    2017 wk7   Joe Klim 174.0 - Walter 174.0 ESPN: Walter won

ESPN records ZERO ties in each of those seasons. Nothing here is guessed: in
every case the two owners' ESPN records differ from the workbook's by exactly
one win and one loss, which names the winner uniquely. The two 2025 ties are
genuine and ESPN agrees, so they are left alone.

Only regular-season games are touched. Playoff ties are real (the 2015 semi-final
was a tie decided on seeding) and are handled by the bracket code, not here.

The repaired scores stay as the workbook recorded them -- the half-point that
rounding destroyed is not recoverable, so points-for remains a few points high
per season for 2013-2017. That does not affect any seed order, and is reported
rather than hidden.
"""

import json
from collections import defaultdict
from pathlib import Path

from build.normalize import owner_from_manager


def espn_records(espn_dir):
    """{season: {owner: {"wins", "losses", "ties", "pf"}}} from the ESPN cache."""
    out = {}
    for path in sorted(Path(espn_dir).glob("league_*.json")):
        blob = json.loads(path.read_text(encoding="utf-8"))
        season = blob["year"]
        teams = {}
        for team in blob.get("teams", []):
            owners = team.get("owners") or []
            if not owners:
                continue
            name = f"{owners[0].get('first', '')} {owners[0].get('last', '')}"
            try:
                owner = owner_from_manager(name)
            except ValueError:
                # An unmapped manager means the roster of owners changed; the
                # caller's assertion will surface it rather than us guessing.
                continue
            teams[owner] = {"wins": team["wins"], "losses": team["losses"],
                            "ties": team["ties"], "pf": team["points_for"]}
        if teams:
            out[season] = teams
    return out


def tally(games, season):
    """Regular-season W-L-T and points-for per owner, from game results.

    Reads the recorded `winner` rather than re-comparing scores: a repaired game
    keeps its tied scoreline (rounding destroyed the real margin), so comparing
    the numbers would score it as a loss for both sides.
    """
    acc = defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0, "pf": 0.0})
    for g in games:
        if g["season"] != season or g["phase"] != "regular":
            continue
        for owner, own in ((g["home_owner"], g["home_score"]),
                           (g["away_owner"], g["away_score"])):
            rec = acc[owner]
            rec["pf"] += own
            if g["tie"]:
                rec["ties"] += 1
            elif g["winner"] == owner:
                rec["wins"] += 1
            else:
                rec["losses"] += 1
    return dict(acc)


def _resolve(game, mine, theirs):
    """Winner of a workbook tie, or None if ESPN doesn't uniquely name one.

    A repairable tie looks like: ESPN gives one side exactly one more win and
    one fewer tie, and the other exactly one more loss and one fewer tie.
    """
    home, away = game["home_owner"], game["away_owner"]
    if home not in theirs or away not in theirs:
        return None

    def delta(owner):
        a, b = mine[owner], theirs[owner]
        return (b["wins"] - a["wins"], b["losses"] - a["losses"], b["ties"] - a["ties"])

    dh, da = delta(home), delta(away)
    if dh == (1, 0, -1) and da == (0, 1, -1):
        return home
    if dh == (0, 1, -1) and da == (1, 0, -1):
        return away
    return None


def repair_ties(games, espn_dir, strict=True):
    """Resolve workbook phantom ties from ESPN; return (games, report).

    Games are mutated in place and also returned. With strict=True a season
    whose W-L-T still disagrees with ESPN after repair raises ValueError --
    a silent mismatch here would quietly corrupt standings, the power index and
    every downstream odds curve.
    """
    truth = espn_records(espn_dir)
    repaired, notes = [], []

    for season in sorted({g["season"] for g in games}):
        theirs = truth.get(season)
        if not theirs:
            continue
        mine = tally(games, season)

        for game in games:
            if game["season"] != season or game["phase"] != "regular" or not game["tie"]:
                continue
            winner = _resolve(game, mine, theirs)
            if winner is None:
                continue
            loser = game["away_owner"] if winner == game["home_owner"] else game["home_owner"]
            game["tie"] = False
            game["winner"] = winner
            game["loser"] = loser
            # The scores stay as recorded -- rounding destroyed the margin, and
            # inventing one would be worse than admitting to a 0.0 margin.
            game["tie_repaired"] = True
            repaired.append({"season": season, "week": game["week"],
                             "winner": winner, "loser": loser,
                             "score": game["home_score"]})

        after = tally(games, season)
        for owner, rec in sorted(theirs.items()):
            got = after.get(owner)
            if not got:
                notes.append(f"{season}: {owner} has ESPN record but no games")
                continue
            if (got["wins"], got["losses"], got["ties"]) != (rec["wins"], rec["losses"], rec["ties"]):
                notes.append(
                    f"{season}: {owner} W-L-T {got['wins']}-{got['losses']}-{got['ties']} "
                    f"!= ESPN {rec['wins']}-{rec['losses']}-{rec['ties']}")

    if notes and strict:
        raise ValueError("W-L-T disagrees with ESPN after tie repair:\n  " +
                         "\n  ".join(notes))
    return games, {"repaired": repaired, "notes": notes}


def points_for_drift(games, espn_dir):
    """Per-season workbook-minus-ESPN points-for, exposing the pre-2018 rounding."""
    truth = espn_records(espn_dir)
    out = {}
    for season, theirs in sorted(truth.items()):
        mine = tally(games, season)
        drift = sum(mine[o]["pf"] for o in theirs if o in mine) - sum(
            r["pf"] for o, r in theirs.items() if o in mine)
        out[season] = round(drift, 1)
    return out
