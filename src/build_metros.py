"""Phase 1: build data/processed/metros.csv (one row per CBSA in the study set).

Every column comes from a raw download in data/raw/ or a sourced table in data/manual/.
"""
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
    """Confirm the ACS variable IDs we use mean what we think (rule 2: inspect)."""
    sh = pd.read_csv(RAW / "acs_table_shells.txt", sep="|", dtype=str)
    lab = dict(zip(sh["Unique ID"], sh["Label"]))
    assert lab["B01001_007"] == "18 and 19 years" and lab["B01001_014"] == "40 to 44 years"
    assert lab["B01001_031"] == "18 and 19 years" and lab["B01001_038"] == "40 to 44 years"
    assert lab["B19013_001"].lower().startswith("median household income")
    return lab


def acs_block():
    check_shells()
    pop = read_acs("b01003")["B01003_E001"].rename("population")
    inc = read_acs("b19013")["B19013_E001"].rename("median_hh_income")
    hh = read_acs("b11001")["B11001_E001"].rename("households")
    age = read_acs("b01001")
    male = [f"B01001_E{n:03d}" for n in range(7, 15)]     # male 18-19 ... 40-44
    female = [f"B01001_E{n:03d}" for n in range(31, 39)]  # female 18-19 ... 40-44
    share = (age[male + female].sum(axis=1) / age["B01001_E001"]).rename("share_18_44")
    out = pd.concat([pop, inc, hh, share], axis=1)
    out.loc[out["median_hh_income"] < 0, "median_hh_income"] = np.nan  # negative = Census missing code
    return out


def popest_block():
    p = pd.read_csv(RAW / "cbsa-est2025-alldata.csv", dtype={"CBSA": str, "MDIV": str, "STCOU": str}, encoding="latin-1")
    p = p[p["LSAD"] == "Metropolitan Statistical Area"].copy()
    p["pop_growth_2020_2025"] = p["POPESTIMATE2025"] / p["POPESTIMATE2020"] - 1
    return p.set_index("CBSA")[["POPESTIMATE2025", "pop_growth_2020_2025"]].rename(columns={"POPESTIMATE2025": "pop_est_2025"})


def gdp_block(delin):
    """BEA county current-dollar GDP (line 3, 2024), summed to CBSA using Census counties."""
    with zipfile.ZipFile(RAW / "bea_CAGDP1.zip") as z:
        name = [n for n in z.namelist() if "ALL_AREAS" in n][0]
        g = pd.read_csv(z.open(name), dtype=str, encoding="latin-1")
    g["GeoFIPS"] = g["GeoFIPS"].str.strip().str.strip('"').str.strip()
    g = g[g["LineCode"].str.strip() == "3"]
    g["gdp_2024_thousands"] = pd.to_numeric(g["2024"], errors="coerce")
    # BEA combines many Virginia independent cities with a neighbouring county, e.g.
    # "Fairfax, Fairfax City + Falls Church, VA*" (FIPS 519xx). Map each Census VA county
    # or city to the BEA combination area whose name lists it.
    d = delin[["county_fips", "CBSA Code", "County/County Equivalent", "State Name"]].copy()
    d["bea_fips"] = d["county_fips"]
    combos = g[g["GeoFIPS"].str.match(r"519\d\d")]
    for _, row in combos.iterrows():
        pieces = row["GeoName"].replace(", VA*", "").replace("+", ",").split(",")
        pieces = [x.strip().lower() for x in pieces]
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
    # a CBSA gets GDP only if all its counties matched (otherwise the sum would be too low)
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


def county_to_cbsa(delin):
    return dict(zip(delin["county_fips"], delin["CBSA Code"]))


def ncaa_block(delin):
    att = parse_ncaa(RAW / "ncaa_mbb_attend.pdf")
    sc = pd.read_csv(MANUAL / "ncaa_school_county.csv", dtype=str)
    sc["cbsa_code"] = sc["county_fips"].str.zfill(5).map(county_to_cbsa(delin))
    m = sc.merge(att, on="school", how="left")
    missing = m[m["attendance"].isna()]["school"].tolist()
    assert not missing, f"school names not found in NCAA PDF: {missing}"
    m.to_csv(PROCESSED / "ncaa_school_metro.csv", index=False)
    g = m.groupby("cbsa_code").agg(ncaa_d1_home_attendance=("attendance", "sum"), ncaa_d1_schools=("school", "count"))
    return g


def teams_block():
    t = pd.read_csv(MANUAL / "teams.csv", dtype=str)
    t = t[t["cbsa_code"].notna()]
    counts = t.pivot_table(index="cbsa_code", columns="league", values="team", aggfunc="count", fill_value=0)
    counts.columns = [f"n_{c.lower().replace(' ', '_')}" for c in counts.columns]
    return counts


def arena_block():
    a = pd.read_csv(MANUAL / "arenas.csv", dtype={"cbsa_code": str})
    a = a[a["cbsa_code"].notna()]
    g = a.groupby("cbsa_code").agg(max_arena_capacity=("capacity_basketball", "max"),
                                   n_arenas_17k=("arena", "count"))
    free = a[~a["nba_tenant"]].groupby("cbsa_code")["capacity_basketball"].max().rename("max_capacity_no_nba_tenant")
    names = a[~a["nba_tenant"]].sort_values("capacity_basketball", ascending=False).groupby("cbsa_code")["arena"].first().rename("largest_arena_no_nba_tenant")
    return g.join(free, how="left").join(names, how="left")


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    delin = load_delineation()
    titles = delin[delin["Metropolitan/Micropolitan Statistical Area"].str.startswith("Metropolitan")][["CBSA Code", "CBSA Title"]].drop_duplicates().set_index("CBSA Code")
    df = titles.join(acs_block(), how="left").join(popest_block(), how="left").join(gdp_block(delin), how="left")
    df = df.join(cbp_block(), how="left").join(ncaa_block(delin), how="left").join(teams_block(), how="left").join(arena_block(), how="left")
    df.index.name = "cbsa_code"
    df = df.reset_index().rename(columns={"CBSA Title": "cbsa_title"})
    df["short_name"] = df["cbsa_title"].str.split(r"[-,/]").str[0].str.strip()

    # study set: population >= 1M, every NBA metro, every metro named in expansion coverage
    for c in [c for c in df.columns if c.startswith("n_")] + ["ncaa_d1_home_attendance", "ncaa_d1_schools", "n_arenas_17k"]:
        df[c] = df[c].fillna(0).astype(int)
    df = df[~df["cbsa_title"].str.endswith("PR")]  # Puerto Rico: not in BEA/CBP metro files; out of scope
    named = df["cbsa_title"].apply(lambda t: any(t.startswith(n.split(",")[0]) and t.split(", ")[-1].startswith(n.split(", ")[1]) for n in NAMED_METROS))
    df = df[(df["population"] >= POP_THRESHOLD) | (df["n_nba"] > 0) | named].copy()
    missing_named = {n for n in NAMED_METROS if not df["cbsa_title"].str.startswith(n.split(",")[0]).any()}
    assert not missing_named, missing_named

    # derived factors
    df["nba_metro"] = df["n_nba"] > 0
    df["big4_other_leagues"] = df["n_nfl"] + df["n_mlb"] + df["n_nhl"]   # competition an entrant faces
    df["big4_total"] = df["big4_other_leagues"] + df["n_nba"]
    df["large_est_per_100k"] = df["large_establishments_500plus"] / df["population"] * 1e5
    df["gdp_per_capita"] = df["gdp_2024_usd"] / df["population"]
    df["ncaa_att_per_1k"] = df["ncaa_d1_home_attendance"] / df["population"] * 1000
    df["has_wnba"] = (df["n_wnba"] > 0).astype(int)
    df["has_g_league"] = (df["n_g_league"] > 0).astype(int)
    df["arena_capable"] = (df["max_arena_capacity"].fillna(0) >= 17000).astype(int)
    df["arena_ready"] = ((df["max_capacity_no_nba_tenant"].fillna(0) >= 17000) & ~df["nba_metro"]).astype(int)
    df = df.sort_values("population", ascending=False)
    df.to_csv(PROCESSED / "metros.csv", index=False)

    # coverage report: share of study metros with a non-missing value per factor
    factors = ["population", "median_hh_income", "share_18_44", "households", "pop_growth_2020_2025", "gdp_2024_usd",
               "ncaa_d1_home_attendance", "has_wnba", "has_g_league", "large_establishments_500plus",
               "big4_other_leagues", "arena_capable"]
    cov = pd.DataFrame({"factor": factors, "share_with_data": [df[f].notna().mean() for f in factors],
                        "n_metros": len(df)})
    cov = pd.concat([cov, pd.DataFrame([
        {"factor": "google_trends_nba", "share_with_data": 0.0, "n_metros": len(df)},
        {"factor": "overseas_visitors_ntto", "share_with_data": 0.0, "n_metros": len(df)}])])
    cov.to_csv(OUTPUTS / "coverage.csv", index=False)
    print(f"metros.csv: {len(df)} metros")
    print(cov.to_string(index=False))
    return df


if __name__ == "__main__":
    main()
