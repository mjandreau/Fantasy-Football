import json

import pytest

from build.tie_repair import _resolve, repair_ties, tally


def _game(season, week, home, hs, away, aws, phase="regular"):
    tie = hs == aws
    return {"season": season, "week": week, "phase": phase, "playoff_round": None,
            "home_owner": home, "home_team": home, "home_score": hs,
            "away_owner": away, "away_team": away, "away_score": aws,
            "winner": None if tie else (home if hs > aws else away),
            "loser": None if tie else (away if hs > aws else home),
            "margin": round(abs(hs - aws), 1), "tie": tie}


def _espn_dir(tmp_path, season, records):
    """Write a minimal league_<season>.json the repairer can read."""
    names = {"Matt": ("Matt", "Jandreau"), "Walter": ("Walter", "Klimczak"),
             "Reid": ("Reid", "Roberge"), "Devin": ("Devin", "Zeller")}
    teams = []
    for i, (owner, (w, l, t)) in enumerate(records.items(), start=1):
        first, last = names[owner]
        teams.append({"team_id": i, "team_name": owner, "abbrev": owner[:4],
                      "owners": [{"first": first, "last": last, "id": str(i)}],
                      "wins": w, "losses": l, "ties": t, "points_for": 0.0,
                      "points_against": 0.0, "final_standing": i, "standing": i})
    (tmp_path / f"league_{season}.json").write_text(
        json.dumps({"year": season, "teams": teams}), encoding="utf-8")
    return tmp_path


def test_tally_counts_ties_and_points():
    games = [_game(2020, 1, "Matt", 100.0, "Walter", 100.0),
             _game(2020, 2, "Matt", 120.0, "Walter", 90.0)]
    t = tally(games, 2020)
    assert t["Matt"] == {"wins": 1, "losses": 0, "ties": 1, "pf": 220.0}
    assert t["Walter"] == {"wins": 0, "losses": 1, "ties": 1, "pf": 190.0}


def test_repairs_a_phantom_tie_to_the_side_espn_credits_with_the_win(tmp_path):
    games = [_game(2020, 1, "Matt", 100.0, "Walter", 100.0)]
    # ESPN: Walter 1-0-0, Matt 0-1-0 -> the workbook tie was really a Walter win.
    d = _espn_dir(tmp_path, 2020, {"Matt": (0, 1, 0), "Walter": (1, 0, 0)})
    games, report = repair_ties(games, d)
    g = games[0]
    assert g["tie"] is False and g["winner"] == "Walter" and g["loser"] == "Matt"
    assert g["tie_repaired"] is True
    assert report["repaired"][0]["winner"] == "Walter"


def test_genuine_ties_are_left_alone(tmp_path):
    games = [_game(2020, 1, "Matt", 100.0, "Walter", 100.0)]
    d = _espn_dir(tmp_path, 2020, {"Matt": (0, 0, 1), "Walter": (0, 0, 1)})
    games, report = repair_ties(games, d)
    assert games[0]["tie"] is True
    assert games[0].get("tie_repaired") is None
    assert report["repaired"] == []


def test_playoff_ties_are_never_touched(tmp_path):
    games = [_game(2020, 1, "Matt", 110.0, "Walter", 100.0),
             _game(2020, 15, "Matt", 100.0, "Walter", 100.0, phase="playoff")]
    d = _espn_dir(tmp_path, 2020, {"Matt": (1, 0, 0), "Walter": (0, 1, 0)})
    games, _ = repair_ties(games, d)
    assert games[1]["tie"] is True


def test_ambiguous_tie_raises_rather_than_guessing(tmp_path):
    # ESPN claims both sides won -- impossible, so the repair must not invent one.
    games = [_game(2020, 1, "Matt", 100.0, "Walter", 100.0)]
    d = _espn_dir(tmp_path, 2020, {"Matt": (1, 0, 0), "Walter": (1, 0, 0)})
    with pytest.raises(ValueError, match="disagrees with ESPN"):
        repair_ties(games, d)


def test_resolve_returns_none_when_deltas_do_not_name_a_winner():
    game = _game(2020, 1, "Matt", 100.0, "Walter", 100.0)
    mine = {"Matt": {"wins": 0, "losses": 0, "ties": 1, "pf": 100.0},
            "Walter": {"wins": 0, "losses": 0, "ties": 1, "pf": 100.0}}
    same = {"Matt": {"wins": 0, "losses": 0, "ties": 1},
            "Walter": {"wins": 0, "losses": 0, "ties": 1}}
    assert _resolve(game, mine, same) is None
