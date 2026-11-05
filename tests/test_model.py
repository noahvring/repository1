import pandas as pd
from config import OUTPUTS


def test_rankings_outputs():
    r = pd.read_csv(OUTPUTS / "rankings.csv", dtype={"cbsa_code": str})
    assert r["cbsa_code"].is_unique
    assert r["total_score"].notna().all()
    for m in ["Seattle", "Las Vegas"]:
        assert r.loc[r.short_name == m, "rank_candidates"].notna().all()


def test_sensitivity_has_six_weightings():
    s = pd.read_csv(OUTPUTS / "sensitivity.csv")
    assert len([c for c in s.columns if c.startswith("rank_")]) == 6
    assert s["top10_frequency"].between(0, 6).all()


def test_validity_rows():
    v = pd.read_csv(OUTPUTS / "validity.csv")
    assert set(v["measure"]) >= {"total_score", "A_size_wealth"}
    assert (v["ci95_low"] <= v["ci95_high"]).all()
