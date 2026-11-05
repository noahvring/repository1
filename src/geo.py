"""Map 'City, State' strings to Census CBSA codes.

Principal cities come from Census list2; other places (suburbs, boroughs) from
data/manual/place_overrides.csv via their county FIPS. Canadian cities map to 'CAN-<city>'.
"""
import pandas as pd
from config import RAW, MANUAL

CANADA = {"Ontario", "Quebec", "British Columbia", "Alberta", "Manitoba", "Nova Scotia", "Saskatchewan"}
STATE_ABBR = {"D.C.": "District of Columbia", "DC": "District of Columbia"}


def load_delineation():
    d = pd.read_excel(RAW / "cbsa_delineation_2023.xlsx", header=2, dtype=str)
    d = d[d["CBSA Code"].str.fullmatch(r"\d{5}", na=False)].copy()
    d["county_fips"] = d["FIPS State Code"].str.zfill(2) + d["FIPS County Code"].str.zfill(3)
    return d


def load_principal_cities(delin):
    p = pd.read_excel(RAW / "cbsa_principal_cities_2023.xlsx", header=2, dtype=str)
    p = p[p["CBSA Code"].str.fullmatch(r"\d{5}", na=False)].copy()
    states = delin[["FIPS State Code", "State Name"]].drop_duplicates()
    states["FIPS State Code"] = states["FIPS State Code"].str.zfill(2)
    p["FIPS State Code"] = p["FIPS State Code"].str.zfill(2)
    return p.merge(states, on="FIPS State Code", how="left")


class Resolver:
    def __init__(self):
        self.delin = load_delineation()
        pc = load_principal_cities(self.delin)
        pc = pc[pc["Metropolitan/Micropolitan Statistical Area"].str.startswith("Metropolitan")]
        self.city = {(r["Principal City Name"].lower(), r["State Name"]): r["CBSA Code"] for _, r in pc.iterrows()}
        self.county = dict(zip(self.delin["county_fips"], self.delin["CBSA Code"]))
        ov = pd.read_csv(MANUAL / "place_overrides.csv", dtype=str)
        self.override = {(r.city.lower(), r.state): self.county.get(r.county_fips.zfill(5)) for r in ov.itertuples()}
        self.unmatched = set()

    def resolve(self, place):
        """place like 'Orchard Park, New York' -> CBSA code (str) or None."""
        if not isinstance(place, str):
            return None
        place = place.split("[")[0].strip()
        if "," not in place:
            self.unmatched.add(place)
            return None
        city, state = [x.strip() for x in place.rsplit(",", 1)]
        state = STATE_ABBR.get(state, state)
        if state in CANADA:
            return "CAN-" + city
        key = (city.lower(), state)
        code = self.override.get(key) or self.city.get(key)
        if code is None:
            self.unmatched.add(place)
        return code
