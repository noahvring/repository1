import pandas as pd
from config import OUTPUTS
from model import PILLARS


def test_rankings_outputs():
    r = pd.read_csv(OUTPUTS / "rankings.csv")
    assert r["market_id"].is_unique
    assert r["total_score"].notna().all()
    for m in ["Seattle", "Las Vegas"]:
        assert r.loc[r.short_name == m, "rank_candidates"].notna().all()


def test_g_league_not_scored():
    cols = [c for f in PILLARS.values() for c, _, _ in f]
    assert "has_g_league" not in cols
    assert "z_has_g_league" not in pd.read_csv(OUTPUTS / "pillar_scores.csv").columns


def test_sensitivity_has_six_weightings():
    s = pd.read_csv(OUTPUTS / "sensitivity.csv")
    assert len([c for c in s.columns if c.startswith("rank_")]) == 6
    assert s["top10_frequency"].between(0, 6).all()


def test_validity_rows():
    v = pd.read_csv(OUTPUTS / "validity.csv")
    assert set(v["measure"]) >= {"total_score", "A_size_wealth"}
    assert (v["ci95_low"] <= v["ci95_high"]).all()
