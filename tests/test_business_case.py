import numpy as np
import pandas as pd
from config import OUTPUTS, MANUAL


def test_kpi_dashboard_has_8_with_seattle_vegas():
    k = pd.read_csv(OUTPUTS / "kpi_dashboard.csv")
    assert len(k) == 8
    assert {"Seattle", "Las Vegas"} <= set(k["short_name"])
    assert (k["est_local_revenue_low"] <= k["est_local_revenue_base"]).all()
    assert (k["est_local_revenue_base"] <= k["est_local_revenue_high"]).all()


def test_owner_npv_grid_and_math():
    n = pd.read_csv(OUTPUTS / "owner_npv.csv")
    assert set(n["media_growth"]) == {0.0, 0.03, 0.06} and set(n["discount_rate"]) == {0.06, 0.08, 0.10}
    assert ((n["fee_share_per_existing_team"] - n["expansion_fee_per_team"] * 2 / 30).abs() < 1).all()
    # recompute one cell by hand: 20 years, dilution grows at g, discounted at r
    row = n[(n.pool_definition == "all_central_revenue") & (n.owner_share == "gross") & (n.media_growth == 0.03)
            & (n.discount_rate == 0.08) & (n.fee_scenario == "base")].iloc[0]
    t = np.arange(1, 21)
    pv = (row.dilution_first_season * 1.03 ** (t - 1) / 1.08 ** t).sum()
    assert abs(pv - row.npv_dilution_20y) < 1
    assert abs(row.dilution_first_season - row.pool_first_season * (1 / 30 - 1 / 32)) < 1


def test_focus_markets_include_front_runners():
    f = pd.read_csv(OUTPUTS / "focus_markets.csv")
    assert {"Seattle", "Las Vegas", "Mexico City", "Vancouver", "Pittsburgh", "Louisville"} <= set(f["focus_label"])


def test_assumptions_labeled_with_rationale():
    a = pd.read_csv(MANUAL / "assumptions.csv")
    ok = a["source_url"].str.startswith("http") | a["source_url"].str.contains("ASSUMPTION – Noah to review") | a["source_url"].eq("NOT SOURCED")
    assert ok.all()
    placeholders = a[a["source_url"].str.contains("ASSUMPTION")]
    assert placeholders["note"].str.contains("Rationale|requested by Noah|grid", case=False).all()


def test_realignment_travel():
    rt = pd.read_csv(OUTPUTS / "realignment_travel.csv")
    assert len(rt) == 5
    assert (rt.loc[rt.option != "Current 30 teams", ["teams_east", "teams_west"]] == 16).all().all()
    assert ((rt["east_miles"] + rt["west_miles"] - rt["total_miles"]).abs() < 1).all()
