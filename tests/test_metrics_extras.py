from build.games import build_games
from build.metrics import head_to_head, record_book, owner_careers
from build.curated import CHAMPIONS


def test_head_to_head_keys_sorted(league_history_path):
    h2h = head_to_head(build_games(league_history_path))
    assert "Matt|Walter" in h2h
    rec = h2h["Matt|Walter"]
    assert rec["a"] == "Matt" and rec["b"] == "Walter"
    assert rec["games"] == rec["a_wins"] + rec["b_wins"] + rec["ties"]
    assert len(rec["meetings"]) == rec["games"]

def test_record_book_highest_score(league_history_path):
    rb = record_book(build_games(league_history_path))
    top = rb["highest_scores"][0]
    assert top["score"] >= 300  # Spark 341 in 2011 is the known all-time high
    assert set(("owner", "score", "season", "week", "phase")).issubset(top)

def test_owner_careers_titles(league_history_path):
    careers = owner_careers(build_games(league_history_path), CHAMPIONS)
    assert set(careers["Walter"]["titles"]) == {2011, 2012, 2025}
    assert 2024 in careers["Matt"]["last_places"]
    assert len(careers["Nolan"]["seasons"]) >= 10
