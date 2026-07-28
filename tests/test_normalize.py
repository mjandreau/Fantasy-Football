import pytest
from build.normalize import owner_from_manager, clean_team_name, OWNERS

def test_owner_mapping_basic():
    assert owner_from_manager("Joe Kaszubowski") == "Buffalo Joe"
    assert owner_from_manager("Joseph Klimczak") == "Joe Klim"
    assert owner_from_manager("Walter Klimczak") == "Walter"   # collision resolved on first name
    assert owner_from_manager("nolan villani") == "Nolan"
    assert owner_from_manager("nolan villani, Tucker Bachand") == "Nolan"
    assert owner_from_manager("Mike Paleologopoulos, Reid Roberge") == "Reid"
    assert owner_from_manager("Red Roberge") == "Reid"
    assert owner_from_manager("Ryan Peloquin") == "Pel"
    assert owner_from_manager("joe ricci") == "Joe Ricci"
    assert owner_from_manager("Luke Palma, Michael Baker") == "Luke"  # first listed wins

def test_owner_mapping_unknown_raises():
    with pytest.raises(ValueError):
        owner_from_manager("Some Rando")

def test_clean_team_name():
    assert clean_team_name("MATTY BIG TRAPS(6-7-1)") == "MATTY BIG TRAPS"
    assert clean_team_name("Herbie Fully Loaded(9-4-1)") == "Herbie Fully Loaded"
    assert clean_team_name("CEEDEE's NUTZ!?(8-6-0)") == "CEEDEE's NUTZ!?"
    assert clean_team_name("Plain Name") == "Plain Name"

def test_owners_list():
    assert len(OWNERS) == 12
    assert "Buffalo Joe" in OWNERS and "Joe Klim" in OWNERS
