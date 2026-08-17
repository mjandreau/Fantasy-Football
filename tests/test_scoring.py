import math

from build.scoring import (PRIOR_MEAN, detect_granularity, estimate,
                           point_in_time, pooled_within_sd, shrinkage,
                           team_scores)


def _game(season, week, home, hs, away, aws, phase="regular"):
    return {"season": season, "week": week, "phase": phase,
            "home_owner": home, "home_score": hs,
            "away_owner": away, "away_score": aws,
            "winner": home if hs > aws else away, "tie": hs == aws}


class TestGranularity:
    def test_whole_points(self):
        assert detect_granularity([100.0, 172.0, 88.0]) == 1.0

    def test_half_points(self):
        assert detect_granularity([100.0, 172.5, 88.0]) == 0.5

    def test_tenths(self):
        assert detect_granularity([100.3, 172.5, 88.0]) == 0.1

    def test_empty_defaults_to_finest(self):
        assert detect_granularity([]) == 0.1


class TestPooledSd:
    def test_none_when_no_team_has_two_games(self):
        assert pooled_within_sd({"a": [100.0], "b": [120.0]}) is None

    def test_pools_across_teams(self):
        # Each team varies by +/-10 around its own mean.
        sd = pooled_within_sd({"a": [90.0, 110.0], "b": [190.0, 210.0]})
        assert math.isclose(sd, math.sqrt((200.0 + 200.0) / 2), rel_tol=1e-9)


class TestShrinkage:
    def test_zero_games_ignores_the_team_average_entirely(self):
        assert shrinkage(0, 30.0, 100.0) == 0.0

    def test_no_real_spread_shrinks_fully_to_the_mean(self):
        assert shrinkage(10, 30.0, 0.0) == 0.0

    def test_monotone_in_games_played(self):
        ks = [shrinkage(n, 31.8, 185.0) for n in range(1, 15)]
        assert ks == sorted(ks)
        assert 0.0 < ks[0] < ks[-1] < 1.0

    def test_league_numbers_shrink_week_four_past_halfway(self):
        # sigma 31.8, tau2 13.6^2 -- four games in, most of the signal is noise.
        assert shrinkage(4, 31.8, 13.6 ** 2) < 0.5


class TestEstimate:
    def test_no_games_puts_everyone_at_the_fallback_mean(self):
        out = estimate({"a": [], "b": []}, fallback_mean=175.0)
        assert out["mu"] == {"a": 175.0, "b": 175.0}
        assert out["k"] == {"a": 0.0, "b": 0.0}

    def test_estimates_lie_between_team_average_and_league_mean(self):
        by = {"a": [220.0] * 6, "b": [140.0] * 6, "c": [180.0] * 6}
        out = estimate(by)
        assert out["mean"] == 180.0
        assert 180.0 <= out["mu"]["a"] <= 220.0
        assert 140.0 <= out["mu"]["b"] <= 180.0

    def test_lambda_zero_collapses_every_team_to_the_league_mean(self):
        by = {"a": [220.0] * 6, "b": [140.0] * 6}
        out = estimate(by, lam=0.0)
        assert out["mu"]["a"] == out["mu"]["b"] == out["mean"]

    def test_more_games_shrinks_less(self):
        few = estimate({"a": [220.0] * 3, "b": [140.0] * 3, "c": [180.0] * 3})
        many = estimate({"a": [220.0] * 12, "b": [140.0] * 12, "c": [180.0] * 12})
        assert many["mu"]["a"] > few["mu"]["a"]

    def test_pure_noise_produces_no_separation(self):
        # Identical teams: every mean equal, so there is nothing to spread.
        by = {o: [180.0] * 8 for o in "abcd"}
        out = estimate(by)
        assert out["tau2"] == 0.0
        assert set(out["mu"].values()) == {180.0}


class TestPointInTime:
    def test_only_sees_earlier_weeks(self):
        games = [_game(2020, 1, "a", 200.0, "b", 100.0),
                 _game(2020, 2, "a", 200.0, "b", 100.0),
                 _game(2020, 3, "a", 100.0, "b", 200.0)]
        by = team_scores(games, 2020, before_week=3)
        assert by["a"] == [200.0, 200.0]
        assert by["b"] == [100.0, 100.0]

    def test_week_one_is_uniform_across_owners(self):
        games = [_game(2020, 1, "a", 200.0, "b", 100.0),
                 _game(2020, 2, "a", 210.0, "b", 90.0)]
        out = point_in_time(games, 2020, week=1)
        assert len(set(out["mu"].values())) == 1

    def test_playoff_games_never_feed_the_estimate(self):
        games = [_game(2020, 1, "a", 200.0, "b", 100.0),
                 _game(2020, 15, "a", 999.0, "b", 1.0, phase="playoff")]
        by = team_scores(games, 2020)
        assert by["a"] == [200.0]
