"""Build data/manual/teams.csv and arenas.csv from saved Wikipedia pages (source URL on every row)."""
import re
import pandas as pd
from config import RAW, MANUAL, SOURCES, ACCESS_DATE
from geo import Resolver

# league -> (source key, table indexes, team column, location column); found by inspecting read_html output
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
    """Drop footnote markers like '[a]' and symbols."""
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
            for team, loc in zip(t[tc].map(clean), t[lc].map(clean)):
                if team in ("", "nan") or team.lower().startswith(("eastern", "western")):  # conference header rows
                    continue
                rows.append({"league": league, "team": team, "location": loc,
                             "cbsa_code": res.resolve(loc), "source_url": url, "access_date": ACCESS_DATE})
    df = pd.DataFrame(rows).drop_duplicates(["league", "team"])
    for lg, n in EXPECTED.items():
        print(f"{lg}: {(df.league == lg).sum()} teams parsed (expected {n})")
    return df


def build_arenas(res):
    url, fname = SOURCES["wiki_arenas"]
    cols = {"Arena/venue", "City", "State", "Max.", "Basket."}
    a = pd.concat([t for t in pd.read_html(RAW / fname) if cols.issubset(t.columns)], ignore_index=True)
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
    # arenas missing from the U.S. list (e.g. Puerto Rico)
    sup = pd.read_csv(MANUAL / "arenas_supplement.csv")
    sup["cbsa_code"] = [res.resolve(f"{c}, {s}") for c, s in zip(sup.city, sup.state)]
    sup["nba_tenant"] = sup["nhl_tenant"] = False
    return pd.concat([out, sup[out.columns]], ignore_index=True)


def main():
    res = Resolver()
    teams, arenas = build_teams(res), build_arenas(res)
    teams.to_csv(MANUAL / "teams.csv", index=False)
    arenas.to_csv(MANUAL / "arenas.csv", index=False)
    print(f"teams: {len(teams)} rows; arenas >=17k: {len(arenas)} rows")
    if res.unmatched:
        print("UNMATCHED places (add to place_overrides.csv if relevant):", sorted(res.unmatched))
    return teams, arenas


if __name__ == "__main__":
    main()
