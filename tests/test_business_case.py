import pandas as pd
from config import OUTPUTS, MANUAL


def test_kpi_dashboard_has_8_with_seattle_vegas():
    k = pd.read_csv(OUTPUTS / "kpi_dashboard.csv")
    assert len(k) == 8
    assert {"Seattle", "Las Vegas"} <= set(k["short_name"])
    assert (k["est_local_revenue_low"] <= k["est_local_revenue_base"]).all()
    assert (k["est_local_revenue_base"] <= k["est_local_revenue_high"]).all()


def test_dilution_math():
    d = pd.read_csv(OUTPUTS / "dilution_payback.csv")
    diff = d["national_rev_per_team_30"] - d["national_rev_per_team_32"]
    assert ((diff - d["annual_dilution_per_existing_team"]).abs() < 1).all()
    assert ((d["fee_received_per_existing_team"] - d["expansion_fee_per_team"] * 2 / 30).abs() < 1).all()


def test_assumptions_labeled():
    a = pd.read_csv(MANUAL / "assumptions.csv")
    ok = a["source_url"].str.startswith("http") | a["source_url"].str.contains("ASSUMPTION – Noah to review") | a["source_url"].eq("NOT SOURCED")
    assert ok.all()
