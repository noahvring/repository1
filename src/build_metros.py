"""Build data/processed/metros.csv: one row per market (CSA, else CBSA) from data/raw/ and data/manual/."""
import zipfile
import numpy as np
import pandas as pd
from config import RAW, MANUAL, PROCESSED, OUTPUTS, NAMED_METROS, POP_THRESHOLD
from geo import load_delineation
from parse_ncaa import parse_ncaa


def read_acs(table):
    """ACS summary-file table (pipe-delimited) -> DataFrame indexed by 5-digit CBSA code."""
    df = pd.read_csv(RAW / f"acs_{table}.dat", sep="|", dtype={"GEO_ID": str})
    df["cbsa_code"] = df["GEO_ID"].str[-5:]
    return df.set_index("cbsa_code")


def check_shells():
    """Check that the ACS variable IDs mean what we assume."""
    sh = pd.read_csv(RAW / "acs_table_shells.txt", sep="|", dtype=str)
    lab = dict(zip(sh["Unique ID"], sh["Label"]))
    assert lab["B01001_007"] == "18 and 19 years" and lab["B01001_014"] == "40 to 44 years"
    assert lab["B01001_031"] == "18 and 19 years" and lab["B01001_038"] == "40 to 44 years"
    assert lab["B19013_001"].lower().startswith("median household income")
    assert lab["B05002_003"] == "Born in state of residence"
    assert lab["B05002_004"].startswith("Born in other state")
    assert lab["B05002_010"] == "Puerto Rico"
    return lab


def acs_block():
    check_shells()
    pop = read_acs("b01003")["B01003_E001"].rename("population")
    inc = read_acs("b19013")["B19013_E001"].rename("median_hh_income")
    hh = read_acs("b11001")["B11001_E001"].rename("households")
    age = read_acs("b01001")
    male = [f"B01001_E{n:03d}" for n in range(7, 15)]     # male 18-19 ... 40-44
    female = [f"B01001_E{n:03d}" for n in range(31, 39)]  # female 18-19 ... 40-44
    age_18_44 = age[male + female].sum(axis=1).rename("pop_18_44")
    pob = read_acs("b05002")  # place of birth
    # in Puerto Rico "born in state" (003) is 0; island-born residents are in 010
    local = pob["B05002_E003"].where(pob["B05002_E003"] > 0, pob["B05002_E010"])
    born = pd.DataFrame({"pob_total": pob["B05002_E001"], "born_in_state": local,
                         "born_other_state": pob["B05002_E004"]})
    out = pd.concat([pop, inc, hh, age_18_44, born], axis=1)
    out.loc[out["median_hh_income"] < 0, "median_hh_income"] = np.nan  # negative = missing
    return out


def popest_block():
    p = pd.read_csv(RAW / "cbsa-est2025-alldata.csv", dtype={"CBSA": str, "MDIV": str, "STCOU": str}, encoding="latin-1")
    # Puerto Rico comes in a separate file
    pr = pd.read_csv(RAW / "prc-cbsa-est2025.csv", dtype={"CBSA": str, "STCOU": str}, encoding="utf-8-sig")
    p = pd.concat([p, pr], ignore_index=True)
    p = p[p["LSAD"].isin(["Metropolitan Statistical Area", "Micropolitan Statistical Area"])].copy()
    return p.set_index("CBSA")[["POPESTIMATE2020", "POPESTIMATE2025"]].rename(columns={"POPESTIMATE2020": "pop_est_2020", "POPESTIMATE2025": "pop_est_2025"})


def gdp_block(delin):
    """BEA county current-dollar GDP (line 3, 2024), summed to CBSA using Census counties."""
    with zipfile.ZipFile(RAW / "bea_CAGDP1.zip") as z:
        name = [n for n in z.namelist() if "ALL_AREAS" in n][0]
        g = pd.read_csv(z.open(name), dtype=str, encoding="latin-1")
    g["GeoFIPS"] = g["GeoFIPS"].str.strip().str.strip('"').str.strip()
    g = g[g["LineCode"].str.strip() == "3"]
    g["gdp_2024_thousands"] = pd.to_numeric(g["2024"], errors="coerce")
    # BEA merges some Virginia independent cities with a county (FIPS 519xx, e.g.
    # "Fairfax, Fairfax City + Falls Church, VA*"): map each Census VA county/city to that area.
    d = delin[["county_fips", "CBSA Code", "County/County Equivalent", "State Name"]].copy()
    d["bea_fips"] = d["county_fips"]
    combos = g[g["GeoFIPS"].str.match(r"519\d\d")]
    for _, row in combos.iterrows():
        pieces = [x.strip().lower() for x in row["GeoName"].replace(", VA*", "").replace("+", ",").split(",")]
        for i, r in d[d["State Name"] == "Virginia"].iterrows():
            nm = r["County/County Equivalent"].lower()
            base = nm.replace(" county", "").replace(" city", "")
            is_city = nm.endswith(" city")
            for pc in pieces:
                pc_city = pc.endswith(" city")
                pc_base = pc.replace(" city", "")
                if base == pc_base and (is_city == pc_city or (is_city and pc == base and not d["County/County Equivalent"].str.lower().eq(base + " county").any())):
                    d.at[i, "bea_fips"] = row["GeoFIPS"]
    m = d[["bea_fips", "CBSA Code"]].drop_duplicates().merge(g[["GeoFIPS", "gdp_2024_thousands"]], left_on="bea_fips", right_on="GeoFIPS", how="left")
    # GDP only if every county matched, otherwise the sum is too low
    agg = m.groupby("CBSA Code").agg(gdp=("gdp_2024_thousands", "sum"), missing=("gdp_2024_thousands", lambda s: s.isna().sum()))
    agg.loc[agg["missing"] > 0, "gdp"] = np.nan
    return (agg["gdp"] * 1000).rename("gdp_2024_usd")


def cbp_block():
    with zipfile.ZipFile(RAW / "cbp23msa.zip") as z:
        c = pd.read_csv(z.open("cbp23msa.txt"), dtype=str)
    c = c[c["naics"] == "------"]  # all industries
    for col in ["n500_999", "n1000", "est"]:
        c[col] = pd.to_numeric(c[col], errors="coerce")
    c["large_establishments_500plus"] = c["n500_999"] + c["n1000"]
    return c.set_index("msa")[["large_establishments_500plus", "est"]].rename(columns={"est": "establishments_total"})


def ncaa_block(delin):
    att = parse_ncaa(RAW / "ncaa_mbb_attend.pdf")
    sc = pd.read_csv(MANUAL / "ncaa_school_county.csv", dtype=str)
    sc["cbsa_code"] = sc["county_fips"].str.zfill(5).map(dict(zip(delin["county_fips"], delin["CBSA Code"])))
    m = sc.merge(att, on="school", how="left")
    missing = m[m["attendance"].isna()]["school"].tolist()
    assert not missing, f"school names not found in NCAA PDF: {missing}"
    m.to_csv(PROCESSED / "ncaa_school_metro.csv", index=False)
    return m.groupby("cbsa_code").agg(ncaa_d1_home_attendance=("attendance", "sum"), ncaa_d1_schools=("school", "count"))


def teams_block():
    t = pd.read_csv(MANUAL / "teams.csv", dtype=str)
    t = t[t["cbsa_code"].notna()]
    counts = t.pivot_table(index="cbsa_code", columns="league", values="team", aggfunc="count", fill_value=0)
    counts.columns = [f"n_{c.lower().replace(' ', '_')}" for c in counts.columns]
    return counts


def haversine_miles(lat1, lon1, lat2, lon2):
    """Great-circle distance in miles between points given in degrees."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 3958.8 * 2 * np.arcsin(np.sqrt(a))


def add_geography(df):
    """Place each market at its largest CBSA's Gazetteer point; distance to the nearest other NBA market (incl. Toronto)."""
    with zipfile.ZipFile(RAW / "gaz_cbsa.zip") as z:
        g = pd.read_csv(z.open(z.namelist()[0]), sep="\t", dtype={"GEOID": str})
    g.columns = [c.strip() for c in g.columns]
    pts = g.set_index("GEOID")[["INTPTLAT", "INTPTLONG"]]
    df["lat"] = df["lead_cbsa_code"].astype(str).map(pts["INTPTLAT"])
    df["lon"] = df["lead_cbsa_code"].astype(str).map(pts["INTPTLONG"])
    intl = pd.read_csv(MANUAL / "international_markets.csv")
    tor = intl[intl.market == "Toronto"].set_index("item")["value"].astype(float)
    nba = df[df["nba_metro"]][["market_id", "lat", "lon"]].copy()
    nba = pd.concat([nba, pd.DataFrame([{"market_id": "CAN-Toronto", "lat": tor["latitude"], "lon": tor["longitude"]}])])
    near, within = [], []
    for _, r in df.iterrows():
        others = nba[nba.market_id != r.market_id]
        d = haversine_miles(r.lat, r.lon, others.lat.values, others.lon.values)
        near.append(d.min())
        within.append(int((d <= 200).sum()))
    df["miles_to_nearest_nba"] = near
    df["nba_markets_within_200mi"] = within
    return df


def market_map(delin):
    """Market = the CSA a CBSA belongs to (e.g. San Jose + San Francisco), else the CBSA itself."""
    d = delin[["CBSA Code", "CBSA Title", "CSA Code", "CSA Title", "Metropolitan/Micropolitan Statistical Area"]].drop_duplicates("CBSA Code").copy()
    has_csa = d["CSA Code"].notna()
    d["market_id"] = np.where(has_csa, "CSA" + d["CSA Code"].fillna(""), "CBSA" + d["CBSA Code"])
    d["market_title"] = np.where(has_csa, d["CSA Title"], d["CBSA Title"])
    d["market_type"] = np.where(has_csa, "CSA", "CBSA")
    return d.set_index("CBSA Code")


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    delin = load_delineation()
    mm = market_map(delin)

    # 1) build every factor at CBSA level (metro + micro areas)
    cb = mm[["CBSA Title", "Metropolitan/Micropolitan Statistical Area", "market_id", "market_title", "market_type"]]
    cb = cb.join(acs_block(), how="left").join(popest_block(), how="left").join(gdp_block(delin), how="left")
    cb = cb.join(cbp_block(), how="left").join(ncaa_block(delin), how="left").join(teams_block(), how="left")
    count_cols = [c for c in cb.columns if c.startswith("n_")] + ["ncaa_d1_home_attendance", "ncaa_d1_schools"]
    cb[count_cols] = cb[count_cols].fillna(0)
    cb["income_x_pop"] = cb["median_hh_income"].where(cb["median_hh_income"] > 0) * cb["population"]
    cb.index.name = "cbsa_code"
    cb.to_csv(PROCESSED / "cbsa_factors.csv")

    # 2) aggregate to market: sum counts and populations; population-weight income
    g = cb.groupby("market_id")
    df = g[["population", "households", "pop_18_44", "pop_est_2020", "pop_est_2025", "large_establishments_500plus",
            "establishments_total", "income_x_pop", "pob_total", "born_in_state", "born_other_state"] + count_cols].sum(min_count=1)
    df["gdp_2024_usd"] = g["gdp_2024_usd"].sum(min_count=1).where(g["gdp_2024_usd"].apply(lambda s: s.notna().all()))
    df["median_hh_income"] = df["income_x_pop"] / g.apply(lambda x: x.loc[x["median_hh_income"] > 0, "population"].sum())
    df["share_18_44"] = df["pop_18_44"] / df["population"]
    df["pop_growth_2020_2025"] = df["pop_est_2025"] / df["pop_est_2020"] - 1
    # transplant share (descriptive): born outside the current state, incl. abroad
    df["transplant_share"] = 1 - df["born_in_state"] / df["pob_total"]
    df["born_other_us_state_share"] = df["born_other_state"] / df["pob_total"]
    df["market_title"] = g["market_title"].first()
    df["market_type"] = g["market_type"].first()
    # name the market after its largest CBSA
    lead = cb.sort_values("population", ascending=False).groupby("market_id").head(1)
    df["short_name"] = lead.set_index("market_id")["CBSA Title"].str.split(r"[-,/]").str[0].str.strip()
    metro_members = cb[cb["Metropolitan/Micropolitan Statistical Area"].str.startswith("Metropolitan")]
    df["member_metros"] = metro_members.groupby("market_id")["CBSA Title"].apply(lambda s: "; ".join(s))
    df["lead_cbsa_code"] = lead.reset_index().set_index("market_id")["cbsa_code"]

    a = pd.read_csv(MANUAL / "arenas.csv", dtype={"cbsa_code": str})
    a = a[a["cbsa_code"].notna()].copy()
    a["market_id"] = a["cbsa_code"].map(mm["market_id"])
    df["max_arena_capacity"] = a.groupby("market_id")["capacity_basketball"].max()
    df["n_arenas_17k"] = a.groupby("market_id")["arena"].count()
    free = a[~a["nba_tenant"]].sort_values("capacity_basketball", ascending=False).groupby("market_id")
    df["max_capacity_no_nba_tenant"] = free["capacity_basketball"].max()
    df["largest_arena_no_nba_tenant"] = free["arena"].first()
    df.index.name = "market_id"
    df = df.reset_index()
    df["n_arenas_17k"] = df["n_arenas_17k"].fillna(0).astype(int)
    for c in count_cols:
        df[c] = df[c].astype(int)

    # 3) study set: population >= 1M, every NBA market, every market with a named metro.
    # Puerto Rico has no CBP or BEA data, so it is flagged partial
    df["partial_data"] = df["market_title"].str.endswith("PR")
    named = df["member_metros"].fillna("").apply(lambda t: any(
        any(m.startswith(n.split(",")[0]) and m.split(", ")[-1].startswith(n.split(", ")[1]) for m in t.split("; ")) for n in NAMED_METROS))
    df = df[(df["population"] >= POP_THRESHOLD) | (df["n_nba"] > 0) | named].copy()

    # derived factors
    df["nba_metro"] = df["n_nba"] > 0  # column name kept from v1; means "NBA market"
    df["big4_other_leagues"] = df["n_nfl"] + df["n_mlb"] + df["n_nhl"]
    df["big4_total"] = df["big4_other_leagues"] + df["n_nba"]
    df["large_est_per_100k"] = df["large_establishments_500plus"] / df["population"] * 1e5
    df["gdp_per_capita"] = df["gdp_2024_usd"] / df["population"]
    df["ncaa_att_per_1k"] = df["ncaa_d1_home_attendance"] / df["population"] * 1000
    df["has_wnba"] = (df["n_wnba"] > 0).astype(int)
    df["has_g_league"] = (df["n_g_league"] > 0).astype(int)  # descriptive only
    df["arena_capable"] = (df["max_arena_capacity"].fillna(0) >= 17000).astype(int)
    df["arena_ready"] = ((df["max_capacity_no_nba_tenant"].fillna(0) >= 17000) & ~df["nba_metro"]).astype(int)
    df = add_geography(df)
    df = df.drop(columns=["income_x_pop"]).sort_values("population", ascending=False)
    df.to_csv(PROCESSED / "metros.csv", index=False)

    factors = ["population", "median_hh_income", "share_18_44", "households", "pop_growth_2020_2025", "gdp_2024_usd",
               "ncaa_d1_home_attendance", "has_wnba", "has_g_league", "large_establishments_500plus",
               "big4_other_leagues", "arena_capable"]
    cov = pd.DataFrame({"factor": factors, "share_with_data": [df[f].notna().mean() for f in factors], "n_markets": len(df)})
    cov = pd.concat([cov, pd.DataFrame([
        {"factor": "google_trends_nba", "share_with_data": 0.0, "n_markets": len(df)},
        {"factor": "overseas_visitors_ntto", "share_with_data": 0.0, "n_markets": len(df)}])])
    cov.to_csv(OUTPUTS / "coverage.csv", index=False)
    print(f"metros.csv: {len(df)} markets ({(df.market_type == 'CSA').sum()} CSAs)")
    print(cov.to_string(index=False))
    return df


if __name__ == "__main__":
    main()
