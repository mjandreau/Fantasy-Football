import pytest
from build.curated import CHAMPIONS, validate_curated
from build.normalize import OWNERS

def test_all_seasons_present():
    assert [int(y) for y in CHAMPIONS] == list(range(2011, 2026))
    assert CHAMPIONS["2025"] == {"champion": "Walter", "last_place": "Devin"}
    assert CHAMPIONS["2023"]["champion"] == "Buffalo Joe"

def test_curated_names_are_valid_owners():
    validate_curated(OWNERS)  # should not raise

def test_validate_curated_rejects_unknown():
    with pytest.raises(ValueError):
        validate_curated(["OnlyOneGuy"])
