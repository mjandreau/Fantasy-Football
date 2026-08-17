import json
from pathlib import Path

import numpy as np
import pytest

from build.playoff_odds import (all_play, clinch_status, enumerate_exact,
                                remaining_matchups, seed_order, season_curves,
                                season_format, simulate, standings_at)
from build.tie_repair import repair_ties

ROOT = Path(__file__).resolve().parent.parent
ESPN = ROOT / "data" / "espn"
LEAGUE_DATA = ROOT / "build" / "league_data.json"

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _game(season, week, home, hs, away, aws, phase="regular"):
    tie = hs == aws
    return {"season": season, "week": week, "phase": phase,
            "home_owner": home, "home_score": hs,
            "away_owner": away, "away_score": aws,
            "winner": None if tie else (home if hs > aws else away),
            "loser": None if tie else (away if hs > aws else home),
            "tie": tie}


def _standing(points, pf):
    return {"wins": int(points), "losses": 0, "ties": 0, "points": points, "pf": pf,
            "played": int(points)}


class TestStandings:
    def test_ties_are_worth_half_a_win(self):
        games = [_game(2020, 1, "a", 100.0, "b", 100.0)]
        s = standings_at(games, 2020, 1)
        assert s["a"]["points"] == 0.5 and s["a"]["ties"] == 1

    def test_only_counts_weeks_up_to_the_cutoff(self):
        games = [_game(2020, 1, "a", 120.0, "b", 100.0),
                 _game(2020, 2, "a", 120.0, "b", 100.0)]
        assert standings_at(games, 2020, 1)["a"]["wins"] == 1
        assert standings_at(games, 2020, 2)["a"]["wins"] == 2

    def test_seed_order_breaks_record_ties_on_points_for(self):
        s = {"a": _standing(5, 1000.0), "b": _standing(5, 1200.0), "c": _standing(6, 1.0)}
        assert seed_order(s) == ["c", "b", "a"]


class TestClinch:
    def test_clinches_when_too_few_rivals_can_reach(self):
        # One spot; leader is 3 points clear with one game left.
        standings = {"a": _standing(5, 900.0), "b": _standing(2, 900.0),
                     "c": _standing(1, 900.0)}
        remaining = [(14, "b", "c")]
        st = clinch_status(standings, remaining, spots=1)
        assert st["a"] == "clinched"
        assert st["b"] == "eliminated" and st["c"] == "eliminated"

    def test_nothing_is_settled_when_everything_is_still_reachable(self):
        standings = {o: _standing(3, 900.0) for o in "abcd"}
        remaining = [(13, "a", "b"), (13, "c", "d"), (14, "a", "c"), (14, "b", "d")]
        st = clinch_status(standings, remaining, spots=2)
        assert set(st.values()) == {"alive"}

    def test_level_on_record_is_never_called_clinched(self):
        # Two spots, three teams level with no games left. Points-for decides,
        # and the bound argument knows nothing about points-for -- so it must
        # refuse to call this rather than guess.
        standings = {"a": _standing(5, 1200.0), "b": _standing(5, 1100.0),
                     "c": _standing(5, 1000.0)}
        st = clinch_status(standings, [], spots=2)
        assert "clinched" not in st.values()

    def test_a_finished_season_eliminates_whoever_missed_out(self):
        standings = {"a": _standing(9, 1200.0), "b": _standing(8, 1100.0),
                     "c": _standing(2, 1000.0)}
        st = clinch_status(standings, [], spots=2)
        assert st["c"] == "eliminated"


class TestSimulate:
    def test_probabilities_sum_to_the_number_of_playoff_spots(self):
        owners = list("abcdef")
        standings = {o: _standing(2, 400.0) for o in owners}
        remaining = [(3, "a", "b"), (3, "c", "d"), (3, "e", "f"),
                     (4, "a", "c"), (4, "b", "e"), (4, "d", "f")]
        mu = {o: 180.0 for o in owners}
        out = simulate(owners, standings, remaining, mu, 30.0, spots=3,
                       n_sims=4000, rng=np.random.default_rng(1))
        assert abs(sum(v["p"] for v in out.values()) - 3) < 1e-6

    def test_seed_distribution_is_a_distribution(self):
        owners = list("abcd")
        standings = {o: _standing(1, 200.0) for o in owners}
        remaining = [(2, "a", "b"), (2, "c", "d")]
        mu = {o: 180.0 for o in owners}
        out = simulate(owners, standings, remaining, mu, 30.0, spots=2,
                       n_sims=2000, rng=np.random.default_rng(2))
        for v in out.values():
            assert abs(sum(v["seed_dist"]) - 1.0) < 1e-9

    def test_a_stronger_team_gets_better_odds(self):
        owners = list("abcd")
        standings = {o: _standing(0, 0.0) for o in owners}
        remaining = [(1, "a", "b"), (1, "c", "d"), (2, "a", "c"), (2, "b", "d")]
        mu = {"a": 220.0, "b": 180.0, "c": 180.0, "d": 140.0}
        out = simulate(owners, standings, remaining, mu, 30.0, spots=2,
                       n_sims=6000, rng=np.random.default_rng(3))
        assert out["a"]["p"] > out["b"]["p"] > out["d"]["p"]

    def test_no_games_left_makes_the_answer_deterministic(self):
        owners = list("abc")
        standings = {"a": _standing(9, 1200.0), "b": _standing(5, 1100.0),
                     "c": _standing(1, 900.0)}
        out = simulate(owners, standings, [], {o: 180.0 for o in owners}, 30.0,
                       spots=2, n_sims=200, rng=np.random.default_rng(4))
        assert out["a"]["p"] == 1.0 and out["b"]["p"] == 1.0 and out["c"]["p"] == 0.0

    def test_coarse_granularity_produces_ties(self):
        # Whole-point scoring ties far more often than tenths, which is exactly
        # why the simulator rounds to the season's real precision.
        owners = ["a", "b"]
        standings = {o: _standing(0, 0.0) for o in owners}
        remaining = [(w, "a", "b") for w in range(1, 200)]
        mu = {o: 180.0 for o in owners}
        coarse = simulate(owners, standings, remaining, mu, 30.0, spots=1,
                          granularity=1.0, n_sims=200, rng=np.random.default_rng(5))
        fine = simulate(owners, standings, remaining, mu, 30.0, spots=1,
                        granularity=0.1, n_sims=200, rng=np.random.default_rng(5))
        # Ties show up as half-points, so total points land off whole numbers.
        assert coarse["a"]["seed_dist"] != fine["a"]["seed_dist"]


class TestAllPlay:
    def test_beating_everyone_in_a_week_is_an_all_play_sweep(self):
        games = [_game(2020, 1, "a", 200.0, "b", 100.0),
                 _game(2020, 1, "c", 150.0, "d", 120.0)]
        ap = all_play(games, 2020, reg_weeks=1)
        assert ap["a"]["wins"] == 3 and ap["a"]["losses"] == 0
        assert ap["b"]["wins"] == 0 and ap["b"]["losses"] == 3
        assert ap["c"]["wins"] == 2 and ap["c"]["losses"] == 1

    def test_equal_scores_count_as_all_play_ties(self):
        games = [_game(2020, 1, "a", 100.0, "b", 100.0)]
        ap = all_play(games, 2020, reg_weeks=1)
        assert ap["a"]["ties"] == 1 and ap["a"]["pct"] == 0.5


class TestMonteCarloAgainstEnumeration:
    def test_simulation_matches_exhaustive_enumeration(self):
        """The oracle: with few games left, every outcome can be counted.

        Base points carry distinct quarter-point offsets and granularity is
        turned off, so no two teams can finish level and the comparison tests
        the playoff-cut logic itself rather than the two functions' different
        views of the points-for tiebreak (enumeration knows only today's
        points-for; the simulator accumulates the rest of the season's).
        """
        owners = list("abcd")
        pts = {"a": 7.0, "b": 6.25, "c": 5.5, "d": 4.75}
        standings = {o: {"wins": int(p), "losses": 0, "ties": 0, "points": p,
                         "pf": 1000.0, "played": int(p)} for o, p in pts.items()}
        remaining = [(13, "a", "b"), (13, "c", "d"), (14, "a", "c"), (14, "b", "d")]
        exact = enumerate_exact(owners, standings, remaining, spots=2)
        # Equal strengths, so each game is the coin flip enumeration assumes.
        sim = simulate(owners, standings, remaining, {o: 180.0 for o in owners},
                       30.0, spots=2, granularity=0, n_sims=40000,
                       rng=np.random.default_rng(7))
        for o in owners:
            assert abs(sim[o]["p"] - exact[o]) < 0.015, (o, sim[o]["p"], exact[o])


@pytest.mark.skipif(not LEAGUE_DATA.exists() or not ESPN.exists(),
                    reason="needs the built league data and ESPN cache")
class TestRealLeague:
    @pytest.fixture(scope="class")
    def games(self):
        data = json.loads(LEAGUE_DATA.read_text(encoding="utf-8"))
        repaired, _ = repair_ties(data["games"], ESPN)
        return repaired

    def test_every_season_reproduces_espn_seed_order(self, games):
        """The anchor. Replayed standings must match ESPN, all 15 seasons."""
        from build.normalize import owner_from_manager
        for season in range(2011, 2026):
            blob = json.loads((ESPN / f"league_{season}.json").read_text(encoding="utf-8"))
            espn = {}
            for t in blob["teams"]:
                o = t["owners"][0]
                espn[owner_from_manager(f"{o['first']} {o['last']}")] = t["standing"]
            fmt = season_format(ESPN, season)
            mine = seed_order(standings_at(games, season, fmt["reg_weeks"]))
            theirs = [o for o, _ in sorted(espn.items(), key=lambda kv: kv[1])]
            assert mine == theirs, f"{season}: {mine} != {theirs}"

    def test_computed_playoff_field_contains_the_curated_champion(self, games):
        """Playoff sheets mix championship and consolation, so who made the
        field is derived from regular-season standings -- never from the mere
        presence of a playoff game."""
        from build.curated import CHAMPIONS
        for season in range(2011, 2026):
            fmt = season_format(ESPN, season)
            field = seed_order(standings_at(games, season, fmt["reg_weeks"]))[:fmt["playoff_spots"]]
            champ = CHAMPIONS[str(season)]["champion"]
            assert champ in field, f"{season}: champion {champ} not in {field}"

    def test_final_week_odds_are_exactly_the_actual_playoff_field(self, games):
        fmt = season_format(ESPN, 2025)
        curves = season_curves(games, 2025, fmt, n_sims=2000)
        last = curves["weeks"][-1]["teams"]
        made = {o for o, v in last.items() if v["p"] == 1.0}
        assert made == set(curves["made_playoffs"])

    def test_preseason_odds_are_uniform(self, games):
        fmt = season_format(ESPN, 2025)
        curves = season_curves(games, 2025, fmt, n_sims=4000)
        first = curves["weeks"][0]["teams"]
        spread = max(v["p"] for v in first.values()) - min(v["p"] for v in first.values())
        assert spread < 0.05, "nothing is known before week 1; odds must be flat"

    def test_odds_sum_to_the_playoff_spots_every_week(self, games):
        fmt = season_format(ESPN, 2023)
        curves = season_curves(games, 2023, fmt, n_sims=4000)
        for wk in curves["weeks"]:
            total = sum(v["p"] for v in wk["teams"].values())
            assert abs(total - fmt["playoff_spots"]) < 0.02, (wk["week"], total)

    def test_remaining_matchups_shrink_as_the_season_runs(self, games):
        fmt = season_format(ESPN, 2022)
        counts = [len(remaining_matchups(games, 2022, w, fmt["reg_weeks"]))
                  for w in range(fmt["reg_weeks"] + 1)]
        assert counts == sorted(counts, reverse=True)
        assert counts[-1] == 0
