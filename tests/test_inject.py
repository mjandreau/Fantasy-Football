import json
from build.inject import inject_into_dashboard

TEMPLATE = ('<html><body><script id="league-data" type="application/json">'
            '/*DATA_START*/{}/*DATA_END*/</script></body></html>')

def test_inject_replaces_between_markers(tmp_path):
    html = tmp_path / "index.html"
    html.write_text(TEMPLATE, encoding="utf-8")
    inject_into_dashboard({"meta": {"total_games": 1360}}, html)
    text = html.read_text(encoding="utf-8")
    start = text.index("/*DATA_START*/") + len("/*DATA_START*/")
    end = text.index("/*DATA_END*/")
    payload = json.loads(text[start:end])
    assert payload["meta"]["total_games"] == 1360

def test_inject_is_idempotent(tmp_path):
    html = tmp_path / "index.html"
    html.write_text(TEMPLATE, encoding="utf-8")
    inject_into_dashboard({"a": 1}, html)
    inject_into_dashboard({"a": 2}, html)
    text = html.read_text(encoding="utf-8")
    assert text.count("/*DATA_START*/") == 1
    start = text.index("/*DATA_START*/") + len("/*DATA_START*/")
    end = text.index("/*DATA_END*/")
    assert json.loads(text[start:end])["a"] == 2
