from pathlib import Path
import pytest

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

@pytest.fixture
def league_history_path():
    p = DATA_DIR / "League Schedule History.xlsx"
    if not p.exists():
        pytest.skip("League Schedule History.xlsx not present in data/")
    return p

@pytest.fixture
def gridiron_path():
    p = DATA_DIR / "The Gridiron.xlsx"
    if not p.exists():
        pytest.skip("The Gridiron.xlsx not present in data/")
    return p
