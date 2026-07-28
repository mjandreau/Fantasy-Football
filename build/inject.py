import json
import re

_MARKER_RE = re.compile(r"/\*DATA_START\*/.*?/\*DATA_END\*/", re.S)


def inject_into_dashboard(data, html_path):
    text = html_path.read_text(encoding="utf-8")
    if not _MARKER_RE.search(text):
        raise ValueError("data markers /*DATA_START*/.../*DATA_END*/ not found in dashboard")
    payload = json.dumps(data, separators=(",", ":"))
    replacement = f"/*DATA_START*/{payload}/*DATA_END*/"
    text = _MARKER_RE.sub(lambda _m: replacement, text, count=1)
    html_path.write_text(text, encoding="utf-8")
