import pytest

from build.games import build_games
from build.curated import CHAMPIONS
from build.dominance import (
    WEIGHTS, season_dominance, franchise_dominance, dynasty_windows,
    never_won, build_dominance,
)


_CACHE = {}


@pytest.fixture
def games(league_history_path):
    # league_history_path is function-scoped in conftest; cache the parsed
    # games ourselves so the xlsx is only read once for this module.
    if "games" not in _CACHE:
        _CACHE["games"] = build_games(league_history_path)
    return _CACHE["games"]


# ---------- season_dominance ----------

def test_season_dominance_covers_every_team_season(games):
    rows = season_dominance(games, CHAMPIONS)
    # 10 teams 2011-14, 12 teams 2015-25 => 4*10 + 11*12 = 172
    assert len(rows) == 172
    by_season = {}
    for r in rows:
        by_season.setdefault(r["season"], []).append(r)
    assert len(by_season[2011]) == 10
    assert len(by_season[2025]) == 12
    assert sorted(by_season) == list(range(2011, 2026))


def test_season_dominance_row_shape(games):
    r = season_dominance(games, CHAMPIONS)[0]
    for key in ("season", "owner", "team", "wins", "losses", "ties", "win_pct",
                "ppg", "z", "all_play_pct", "expected_wins", "playoff_wins",
                "playoff_losses", "point_diff", "avg_margin", "worst_loss",
                "title", "dom"):
        assert key in r, f"missing {key}"
    assert isinstance(r["title"], bool)
    assert r["team"]  # every team-season has a team name


def test_season_dominance_z_scores_center_on_zero_each_season(games):
    rows = season_dominance(games, CHAMPIONS)
    by_season = {}
    for r in rows:
        by_season.setdefault(r["season"], []).append(r)
    for season, rs in by_season.items():
        # z is measured within the season, so it must sum to ~0 there
        assert abs(sum(r["z"] for r in rs)) < 0.05, season


def test_season_dominance_point_diff_is_zero_sum_within_season(games):
    rows = season_dominance(games, CHAMPIONS)
    by_season = {}
    for r in rows:
        by_season.setdefault(r["season"], []).append(r)
    for season, rs in by_season.items():
        # every point scored is a point allowed for somebody
        assert abs(sum(r["point_diff"] for r in rs)) < 0.5, season


def test_season_dominance_titles_match_curated(games):
    rows = season_dominance(games, CHAMPIONS)
    flagged = {r["season"]: r["owner"] for r in rows if r["title"]}
    assert len(flagged) == 15
    for season, champ in CHAMPIONS.items():
        assert flagged[int(season)] == champ["champion"]


def test_dom_recomputes_from_its_own_published_columns(games):
    """The DOM column must be reproducible from the columns beside it, so the
    formula note on the dashboard can be audited against the table."""
    for r in season_dominance(games, CHAMPIONS):
        expected = (WEIGHTS["z"] * r["z"]
                    + WEIGHTS["all_play"] * (r["all_play_pct"] - 0.5) * 2
                    + WEIGHTS["win_pct"] * (r["win_pct"] - 0.5) * 2
                    + WEIGHTS["title"] * (1 if r["title"] else 0)
                    + WEIGHTS["playoff_win"] * r["playoff_wins"])
        assert r["dom"] == pytest.approx(expected, abs=0.01)


def test_2011_walter_is_the_most_dominant_season_by_dom(games):
    rows = sorted(season_dominance(games, CHAMPIONS), key=lambda r: -r["dom"])
    top = rows[0]
    assert (top["season"], top["owner"]) == (2011, "Walter")
    # 10-4 but 2.1 SDs clear of the league in scoring, then 3-0 in the bracket
    assert (top["wins"], top["losses"]) == (10, 4)
    assert (top["playoff_wins"], top["playoff_losses"]) == (3, 0)
    assert top["title"] is True
    assert top["z"] > 2.0


def test_a_title_outranks_a_marginal_edge_but_cannot_rescue_a_weak_season(games):
    """The title weight is the one deliberate thumb on the scale: it lifts
    2011 Walter over 2021 Reid (13-1, best all-play ever, no ring) without
    letting every champion float to the top."""
    rows = {(r["season"], r["owner"]): r for r in season_dominance(games, CHAMPIONS)}
    assert rows[(2011, "Walter")]["dom"] > rows[(2021, "Reid")]["dom"]
    # ...and Reid still outranks the majority of champions
    champs = [r for r in rows.values() if r["title"]]
    beaten = [c for c in champs if c["dom"] < rows[(2021, "Reid")]["dom"]]
    assert len(beaten) > len(champs) / 2


def test_2013_matt_leads_point_differential(games):
    """DOM is a blend, but raw differential is its own sortable column and
    2013 Matt owns it: 15-1 overall at +626."""
    rows = season_dominance(games, CHAMPIONS)
    top = max(rows, key=lambda r: r["point_diff"])
    assert (top["season"], top["owner"]) == (2013, "Matt")
    assert (top["wins"], top["losses"]) == (12, 1)
    assert (top["playoff_wins"], top["playoff_losses"]) == (3, 0)
    assert top["point_diff"] == pytest.approx(626.0)
    assert top["worst_loss"] == pytest.approx(-34.0)


def test_playoff_records_only_count_postseason_games(games):
    rows = {(r["season"], r["owner"]): r for r in season_dominance(games, CHAMPIONS)}
    # 2021 Reid went 13-1 in the regular season, then 1-1 in the playoffs
    reid = rows[(2021, "Reid")]
    assert (reid["wins"], reid["losses"]) == (13, 1)
    assert (reid["playoff_wins"], reid["playoff_losses"]) == (1, 1)
    assert reid["title"] is False


# ---------- franchise_dominance ----------

def test_franchise_dominance_one_row_per_owner(games):
    rows = franchise_dominance(games, CHAMPIONS)
    assert len(rows) == 15
    assert len({r["owner"] for r in rows}) == 15


def test_franchise_dominance_row_shape_and_title_counts(games):
    rows = {r["owner"]: r for r in franchise_dominance(games, CHAMPIONS)}
    for key in ("owner", "seasons", "wins", "losses", "ties", "win_pct",
                "avg_z", "all_play_pct", "playoff_wins", "playoff_losses",
                "titles", "title_years", "active", "dom"):
        assert key in rows["Walter"], f"missing {key}"
    assert rows["Nolan"]["titles"] == 4
    assert rows["Nolan"]["title_years"] == [2017, 2019, 2020, 2021]
    assert rows["Reid"]["titles"] == 0
    assert rows["Chris Borea"]["active"] is False
    assert rows["Walter"]["active"] is True


def test_franchise_season_counts_match_the_games_table(games):
    rows = {r["owner"]: r for r in franchise_dominance(games, CHAMPIONS)}
    played = {}
    for g in games:
        for owner in (g["home_owner"], g["away_owner"]):
            played.setdefault(owner, set()).add(g["season"])
    for owner, seasons in played.items():
        assert rows[owner]["seasons"] == len(seasons), owner


def test_walter_is_the_most_dominant_franchise(games):
    rows = sorted(franchise_dominance(games, CHAMPIONS), key=lambda r: -r["dom"])
    assert rows[0]["owner"] == "Walter"


# ---------- dynasty_windows ----------

def test_dynasty_windows_respects_window_length(games):
    for length in (3, 5):
        for w in dynasty_windows(games, CHAMPIONS, length=length):
            assert w["end"] - w["start"] + 1 == length
            assert len(w["seasons"]) == length


def test_dynasty_windows_finds_the_nolan_run(games):
    top = dynasty_windows(games, CHAMPIONS, length=5)[0]
    assert top["owner"] == "Nolan"
    assert top["titles"] == 4
    assert top["title_years"] == [2017, 2019, 2020, 2021]
    assert (top["start"], top["end"]) == (2017, 2021)


def test_dynasty_windows_never_span_a_year_an_owner_did_not_play(games):
    played = {}
    for g in games:
        for owner in (g["home_owner"], g["away_owner"]):
            played.setdefault(owner, set()).add(g["season"])
    for length in (3, 5):
        for w in dynasty_windows(games, CHAMPIONS, length=length):
            assert set(w["seasons"]) <= played[w["owner"]], w


# ---------- never_won ----------

def test_never_won_excludes_champions_and_ranks_by_dom(games):
    rows = never_won(games, CHAMPIONS)
    assert rows, "expected at least one high-DOM season without a title"
    assert all(r["title"] is False for r in rows)
    assert rows == sorted(rows, key=lambda r: -r["dom"])


def test_never_won_is_led_by_2021_reid_and_says_how_it_ended(games):
    top = never_won(games, CHAMPIONS)[0]
    assert (top["season"], top["owner"]) == (2021, "Reid")
    # eliminated by Nolan, who dropped 288.7 in the championship game
    assert top["eliminated_by"] == "Nolan"
    assert top["elimination_score"] == pytest.approx(195.8)
    assert top["elimination_opp_score"] == pytest.approx(288.7)


# ---------- build_dominance ----------

def test_build_dominance_payload_shape(games):
    d = build_dominance(games, CHAMPIONS)
    assert set(d) == {"seasons", "franchises", "dynasties", "never_won", "formula"}
    assert d["formula"]["weights"] == WEIGHTS
    assert d["formula"]["text"]
    assert set(d["dynasties"]) == {"3", "5"}
