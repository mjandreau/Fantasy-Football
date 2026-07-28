CHAMPIONS = {
    "2011": {"champion": "Walter", "last_place": "Luke"},
    "2012": {"champion": "Walter", "last_place": "Devin"},
    "2013": {"champion": "Matt", "last_place": "Spark"},
    "2014": {"champion": "Luke", "last_place": "Reid"},
    "2015": {"champion": "Matt", "last_place": "Nolan"},
    "2016": {"champion": "Buffalo Joe", "last_place": "Joe Klim"},
    "2017": {"champion": "Nolan", "last_place": "Joe Ricci"},
    "2018": {"champion": "Baker", "last_place": "Reid"},
    "2019": {"champion": "Nolan", "last_place": "Devin"},
    "2020": {"champion": "Nolan", "last_place": "Pel"},
    "2021": {"champion": "Nolan", "last_place": "Joe Ricci"},
    "2022": {"champion": "Buffalo Joe", "last_place": "Baker"},
    "2023": {"champion": "Buffalo Joe", "last_place": "Devin"},
    "2024": {"champion": "Joe Ricci", "last_place": "Matt"},
    "2025": {"champion": "Walter", "last_place": "Devin"},
}


def validate_curated(owners):
    valid = set(owners)
    for season, rec in CHAMPIONS.items():
        for role in ("champion", "last_place"):
            if rec[role] not in valid:
                raise ValueError(f"{season} {role} '{rec[role]}' not a known owner")
