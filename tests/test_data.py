"""Phase 1 data checks. Run after `python run_all.py` (needs data/processed and outputs)."""
import pandas as pd
from config import PROCESSED, MANUAL, OUTPUTS


def metros():
    return pd.read_csv(PROCESSED / "metros.csv")


def cbsa_to_market():
    return pd.read_csv(PROCESSED / "cbsa_factors.csv", dtype={"cbsa_code": str}).set_index("cbsa_code")["market_id"]


def test_no_duplicate_markets():
    assert metros()["market_id"].is_unique


def test_csa_merges_bay_area_and_dc_baltimore():
    m = metros().set_index("short_name")
    assert "San Jose" in m.loc["San Francisco", "member_metros"]
    assert "Baltimore" in m.loc["Washington", "member_metros"]
    assert "San Jose" not in m.index and "Baltimore" not in m.index


def test_all_30_nba_teams_mapped():
    t = pd.read_csv(MANUAL / "teams.csv", dtype=str)
    nba = t[t["league"] == "NBA"]
    assert len(nba) == 30
    assert nba["cbsa_code"].notna().all()            # Toronto maps to 'CAN-Toronto'
    us = nba[~nba["cbsa_code"].str.startswith("CAN")]
    markets = us["cbsa_code"].map(cbsa_to_market())
    assert markets.notna().all()
    assert set(markets).issubset(set(metros()["market_id"]))
    assert metros()["nba_metro"].sum() == 27          # 29 U.S. teams, LA and NY have two


def test_every_manual_row_has_source_url():
    for f in MANUAL.glob("*.csv"):
        df = pd.read_csv(f, dtype=str)
        col = "source_url" if "source_url" in df.columns else "source"
        assert col in df.columns, f"{f.name} has no source column"
        vals = df[col].fillna("")
        ok = vals.str.startswith("http") | vals.str.contains("ASSUMPTION – Noah to review") | vals.eq("NOT SOURCED")
        assert ok.all(), f"{f.name}: rows without source: {df[~ok].index.tolist()}"


def test_named_metros_present():
    members = " ".join(metros()["member_metros"].fillna(""))
    for n in ["Las Vegas", "Seattle", "Kansas City", "Louisville", "Nashville", "Austin", "San Diego",
              "Pittsburgh", "Tampa", "St. Louis", "Columbus, OH", "Cincinnati", "Raleigh", "Baltimore"]:
        assert n in members, n


def test_coverage_report_written():
    cov = pd.read_csv(OUTPUTS / "coverage.csv")
    print("\n" + cov.to_string(index=False))
    assert {"factor", "share_with_data"}.issubset(cov.columns)
    assert cov.loc[cov.factor == "population", "share_with_data"].iloc[0] == 1.0
