"""Phase 1 data checks. Run after `python run_all.py` (needs data/processed and outputs)."""
import pandas as pd
from config import PROCESSED, MANUAL, OUTPUTS


def metros():
    return pd.read_csv(PROCESSED / "metros.csv", dtype={"cbsa_code": str})


def test_no_duplicate_cbsas():
    m = metros()
    assert m["cbsa_code"].is_unique


def test_all_30_nba_teams_mapped():
    t = pd.read_csv(MANUAL / "teams.csv", dtype=str)
    nba = t[t["league"] == "NBA"]
    assert len(nba) == 30
    assert nba["cbsa_code"].notna().all()            # Toronto maps to 'CAN-Toronto'
    us = nba[~nba["cbsa_code"].str.startswith("CAN")]
    assert set(us["cbsa_code"]).issubset(set(metros()["cbsa_code"]))


def test_every_manual_row_has_source_url():
    for f in MANUAL.glob("*.csv"):
        df = pd.read_csv(f, dtype=str)
        col = "source_url" if "source_url" in df.columns else "source"
        assert col in df.columns, f"{f.name} has no source column"
        vals = df[col].fillna("")
        ok = vals.str.startswith("http") | vals.str.contains("ASSUMPTION – Noah to review")
        assert ok.all(), f"{f.name}: rows without source: {df[~ok].index.tolist()}"


def test_named_metros_present():
    names = set(metros()["short_name"])
    for n in ["Las Vegas", "Seattle", "Kansas City", "Louisville", "Nashville", "Austin", "San Diego",
              "Pittsburgh", "Tampa", "St. Louis", "Columbus", "Cincinnati", "Raleigh", "Baltimore"]:
        assert n in names


def test_coverage_report_written():
    cov = pd.read_csv(OUTPUTS / "coverage.csv")
    print("\n" + cov.to_string(index=False))
    assert {"factor", "share_with_data"}.issubset(cov.columns)
    assert cov.loc[cov.factor == "population", "share_with_data"].iloc[0] == 1.0
