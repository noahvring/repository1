"""Build the sourced team and arena tables from saved Wikipedia pages.

Each league's Wikipedia article has a current-teams table (inspected by hand: the
column names differ by league, see LEAGUE_TABLES). We read it with pandas.read_html,
keep team name + location, resolve location -> CBSA, and record the source URL and
access date on every row. Output is written to data/manual/ and committed.
"""
import re
import pandas as pd
from config import RAW, MANUAL, SOURCES, ACCESS_DATE
from geo import Resolver

# league -> (source key, list of table indexes, team column, location column)
# Indexes were found by inspecting pd.read_html() output for each saved page.
LEAGUE_TABLES = {
    "NBA": ("wiki_nba", [1], "Team", "Location"),
    "NFL": ("wiki_nfl", [2], "Team[53]", "City"),
    "MLB": ("wiki_mlb", [1], "Team", "City"),
    "NHL": ("wiki_nhl", [2], "Team", "City"),
    "MLS": ("wiki_mls", [1], "Club", "Location"),
    "WNBA": ("wiki_wnba", [2], "Team", "City"),
    "G League": ("wiki_gleague", [1, 2], "Team", "City"),
}
EXPECTED = {"NBA": 30, "NFL": 32, "MLB": 30, "NHL": 32, "MLS": 30}


def clean(s):
    """Drop footnote markers like '[a]' and stray symbols."""
    return re.sub(r"\[.*?\]", "", str(s)).replace("*", "").replace("‡", "").replace("†", "").strip()


def find_col(df, prefix):
    for c in df.columns:
        if str(c).startswith(prefix.split("[")[0]):
            return c
    raise KeyError(prefix)


def build_teams(res):
    rows = []
    for league, (key, idxs, tcol, lcol) in LEAGUE_TABLES.items():
        url, fname = SOURCES[key]
        tables = pd.read_html(RAW / fname)
        for i in idxs:
            t = tables[i]
            tc, lc = find_col(t, tcol), find_col(t, lcol)
            for _, r in t.iterrows():
                team, loc = clean(r[tc]), clean(r[lc])
                if not team or team == "nan" or team == clean(r[t.columns[0]]) and league not in ("G League",) and team.lower().startswith(("eastern", "western")):
                    continue
                rows.append({"league": league, "team": team, "location": loc,
                             "cbsa_code": res.resolve(loc), "source_url": url, "access_date": ACCESS_DATE})
    df = pd.DataFrame(rows).drop_duplicates(["league", "team"])
    for lg, n in EXPECTED.items():
        got = (df.league == lg).sum()
        print(f"{lg}: {got} teams parsed (expected {n})")
    return df


def build_arenas(res):
    url, fname = SOURCES["wiki_arenas"]
    tables = pd.read_html(RAW / fname)
    keep = []
    for t in tables:
        if {"Arena/venue", "City", "State", "Max.", "Basket."}.issubset(t.columns):
            keep.append(t)
    a = pd.concat(keep, ignore_index=True)
    a["arena"] = a["Arena/venue"].map(clean)
    for c in ["Max.", "Basket."]:
        a[c] = pd.to_numeric(a[c].astype(str).str.replace(",", "").str.extract(r"(\d+)")[0], errors="coerce")
    # basketball capacity when listed, otherwise the arena's maximum capacity
    a["capacity_basketball"] = a["Basket."].fillna(a["Max."])
    a = a[a["capacity_basketball"] >= 17000].drop_duplicates("arena")
    out = pd.DataFrame({
        "arena": a["arena"],
        "city": a["City"].map(clean), "state": a["State"].map(clean),
        "capacity_basketball": a["capacity_basketball"].astype(int),
        "tenants": a["Major tenant(s)"].map(clean),
        "opened": a["Open"].map(clean),
    })
    out["cbsa_code"] = [res.resolve(f"{c}, {s}") for c, s in zip(out.city, out.state)]
    out["nba_tenant"] = out["tenants"].str.contains(r"\(NBA\)", regex=True)
    out["nhl_tenant"] = out["tenants"].str.contains(r"\(NHL\)", regex=True)
    out["source_url"] = url
    out["access_date"] = ACCESS_DATE
    return out.reset_index(drop=True)


def main():
    res = Resolver()
    teams = build_teams(res)
    arenas = build_arenas(res)
    teams.to_csv(MANUAL / "teams.csv", index=False)
    arenas.to_csv(MANUAL / "arenas.csv", index=False)
    print(f"teams: {len(teams)} rows; arenas >=17k: {len(arenas)} rows")
    if res.unmatched:
        print("UNMATCHED places (add to place_overrides.csv if relevant):", sorted(res.unmatched))
    return teams, arenas


if __name__ == "__main__":
    main()
