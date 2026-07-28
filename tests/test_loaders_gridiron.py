from build.loaders import parse_gridiron

def test_parse_gridiron_counts(gridiron_path):
    d = parse_gridiron(gridiron_path)
    # Gridiron Data_Sorted = regular season only, 1117 games
    assert len(d) == 1117
    # 2025 froze at week 9 -> far fewer 2025 keys than a full season
    s25 = [k for k in d if k[0] == 2025]
    assert 40 <= len(s25) <= 55

def test_parse_gridiron_lookup(gridiron_path):
    d = parse_gridiron(gridiron_path)
    key = (2025, 1, frozenset({"Walter", "Buffalo Joe"}))
    assert key in d
    assert d[key]["Buffalo Joe"] == 212.6
