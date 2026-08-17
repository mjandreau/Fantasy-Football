import json
from pathlib import Path

import pytest

from build.odds_data import _STATUS, build_odds, load_schedule
from build.tie_repair import repair_ties

ROOT = Path(__file__).resolve().parent.parent
ESPN = ROOT / "data" / "espn"
LEAGUE_DATA = ROOT / "build" / "league_data.json"

pytestmark = pytest.mark.skipif(
    not LEAGUE_DATA.exists() or not ESPN.exists(),
    reason="needs the built league data and ESPN cache")


@pytest.fixture(scope="module")
def odds():
    data = json.loads(LEAGUE_DATA.read_text(encoding="utf-8"))
    games, _ = repair_ties(data["games"], ESPN)
    # Few simulations: this checks payload shape and invariants, not precision.
    return build_odds(games, ESPN, n_sims=800)


def test_covers_every_played_season(odds):
    assert odds["seasons"] == list(range(2011, 2026))


def test_every_season_has_one_row_per_week_plus_preseason(odds):
    for year, s in odds["by_season"].items():
        assert len(s["weeks"]) == s["reg_weeks"] + 1, year
        assert s["weeks"][0]["week"] == 0
        assert s["weeks"][-1]["week"] == s["reg_weeks"]


def test_status_codes_are_the_documented_single_characters(odds):
    allowed = set(_STATUS.values())
    for s in odds["by_season"].values():
        for wk in s["weeks"]:
            for rec in wk["teams"].values():
                assert rec["s"] in allowed


def test_probabilities_are_probabilities(odds):
    for year, s in odds["by_season"].items():
        for wk in s["weeks"]:
            for owner, rec in wk["teams"].items():
                assert 0.0 <= rec["p"] <= 1.0, (year, owner)
                assert 0.0 <= rec["h"] <= 1.0, (year, owner)


def test_odds_sum_to_the_playoff_spots(odds):
    for year, s in odds["by_season"].items():
        for wk in s["weeks"]:
            total = sum(r["p"] for r in wk["teams"].values())
            assert abs(total - s["playoff_spots"]) < 0.05, (year, wk["week"], total)


def test_final_week_is_exactly_the_teams_that_made_it(odds):
    for year, s in odds["by_season"].items():
        if s["in_progress"]:
            continue
        last = s["weeks"][-1]["teams"]
        assert {o for o, r in last.items() if r["p"] == 1.0} == set(s["made_playoffs"]), year
        assert len(s["made_playoffs"]) == s["playoff_spots"], year


def test_a_clinched_team_never_reverts_to_alive(odds):
    """Clinching is monotone -- points cannot be lost, so neither can a berth."""
    for year, s in odds["by_season"].items():
        for owner in s["owners"]:
            seen_clinch = seen_elim = False
            for wk in s["weeks"]:
                st = wk["teams"][owner]["s"]
                if st == "c":
                    seen_clinch = True
                elif seen_clinch:
                    pytest.fail(f"{year} {owner}: clinched then {st} in week {wk['week']}")
                if st == "e":
                    seen_elim = True
                elif seen_elim:
                    pytest.fail(f"{year} {owner}: eliminated then {st} in week {wk['week']}")


def test_schedule_luck_is_zero_sum(odds):
    """One owner's good fortune is another's robbery; the league total is zero."""
    for year, s in odds["by_season"].items():
        total = 0.0
        for owner in s["owners"]:
            f, ap = s["final"][owner], s["all_play"][owner]
            gp = f["wins"] + f["losses"] + f["ties"]
            actual = (f["wins"] + 0.5 * f["ties"]) / gp if gp else 0.0
            total += (actual - ap["pct"]) * gp
        assert abs(total) < 0.05, (year, total)


def test_all_play_games_match_the_field_size(odds):
    for year, s in odds["by_season"].items():
        expected = (len(s["owners"]) - 1) * s["reg_weeks"]
        for owner, ap in s["all_play"].items():
            assert ap["wins"] + ap["losses"] + ap["ties"] == expected, (year, owner)


def test_seed_distributions_only_ship_for_a_live_season(odds):
    for s in odds["by_season"].values():
        assert ("seed_dist" in s) == s["in_progress"]


def test_payload_stays_small_enough_to_embed(odds):
    blob = json.dumps(odds, separators=(",", ":"))
    assert len(blob) < 400_000, f"{len(blob)} bytes is too much to inline"


def test_missing_schedule_is_absent_not_an_error(tmp_path):
    assert load_schedule(tmp_path, 2026) is None
