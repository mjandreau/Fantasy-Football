import re

OWNERS = ["Baker", "Buffalo Joe", "Devin", "Joe Klim", "Joe Ricci", "Luke",
          "Matt", "Nolan", "Pel", "Reid", "Spark", "Walter"]

# Ordered rules: first substring that matches the FIRST listed manager wins.
# Order matters — more specific keys first (e.g. "joseph klim" before "klim").
_RULES = [
    ("kaszubowski", "Buffalo Joe"),
    ("joseph klim", "Joe Klim"),
    ("walter", "Walter"),
    ("villani", "Nolan"),
    ("carpenter", "Spark"),
    ("jandreau", "Matt"),
    ("ricci", "Joe Ricci"),
    ("baker", "Baker"),
    ("zeller", "Devin"),
    ("palma", "Luke"),
    ("peloquin", "Pel"),
    ("roberge", "Reid"),
    ("paleologopoulos", "Reid"),
]

_RECORD_RE = re.compile(r"\s*\((\d+\s*-\s*\d+(?:\s*-\s*\d+)?)\)\s*$")


def owner_from_manager(manager):
    """Map a manager string to a short owner name. Uses only the FIRST listed
    manager (before any comma) so co-managed teams resolve to their primary owner."""
    if not manager:
        raise ValueError("empty manager string")
    first = manager.split(",")[0].strip().lower()
    for key, owner in _RULES:
        if key in first:
            return owner
    raise ValueError(f"unrecognized manager: {manager!r}")


def clean_team_name(raw):
    """Strip a trailing (record) suffix like '(9-4-1)' from a team name."""
    return _RECORD_RE.sub("", raw).strip()
