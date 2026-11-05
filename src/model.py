"""Phase 2: market-attractiveness scorecard.

1. Each factor is standardized to a z-score across the study metros (log first for
   population, GDP and large-establishment counts, which are heavily skewed).
2. Competition (teams from other big leagues) enters with a negative sign.
3. Pillar score = mean of its factor z-scores (equal weights, missing factors skipped).
4. Total score = weighted mean of the 4 pillar scores (equal weights by default).
All metros, NBA and non-NBA, are scored the same way so current NBA markets act as a benchmark.
"""
import numpy as np
import pandas as pd
from scipy import stats
from config import PROCESSED, OUTPUTS

# pillar -> list of (column, transform, sign)
PILLARS = {
    "A_size_wealth": [("population", "log", 1), ("median_hh_income", None, 1), ("share_18_44", None, 1),
                      ("pop_growth_2020_2025", None, 1), ("gdp_2024_usd", "log", 1)],
    # G League presence is NOT scored: most G League teams are NBA-owned affiliates near their parent
    # club, so it would flatter existing NBA markets. It stays in metros.csv as a descriptive column.
    "B_basketball_demand": [("ncaa_att_per_1k", None, 1), ("has_wnba", None, 1)],
    "C_corporate": [("large_establishments_500plus", "log", 1), ("large_est_per_100k", None, 1)],
    "D_competition_infra": [("big4_other_leagues", None, -1), ("arena_capable", None, 1)],
}
PILLAR_NAMES = list(PILLARS)

WEIGHTINGS = {  # weights on pillars A, B, C, D
    "equal": [0.25, 0.25, 0.25, 0.25],
    "size_heavy": [0.5, 1 / 6, 1 / 6, 1 / 6],
    "wealth_corporate_heavy": [1 / 6, 1 / 6, 0.5, 1 / 6],
    "demand_heavy": [1 / 6, 0.5, 1 / 6, 1 / 6],
    "ignore_competition": "ignore_competition",   # equal weights, D pillar without competition factor
    "arena_required": "arena_required",           # equal weights, only arena-ready candidates ranked
}


def zscore(s):
    return (s - s.mean()) / s.std(ddof=0)


def factor_z(df, ignore_competition=False, pillars=None):
    z = pd.DataFrame(index=df.index)
    for pillar, factors in (pillars or PILLARS).items():
        for col, tr, sign in factors:
            if ignore_competition and col == "big4_other_leagues":
                continue
            x = np.log(df[col]) if tr == "log" else df[col].astype(float)
            z[f"z_{col}"] = sign * zscore(x)
    return z


def pillar_scores(df, ignore_competition=False, pillars=None):
    pillars = pillars or PILLARS
    z = factor_z(df, ignore_competition, pillars)
    out = pd.DataFrame(index=df.index)
    for pillar, factors in pillars.items():
        cols = [f"z_{c}" for c, _, _ in factors if f"z_{c}" in z.columns]
        out[pillar] = z[cols].mean(axis=1, skipna=True)
    return out, z


def total(p, w):
    return (p[PILLAR_NAMES] * np.array(w)).sum(axis=1)


def rank_candidates(df, score):
    """Rank among non-NBA metros only (1 = most attractive)."""
    s = score[~df["nba_metro"]]
    return s.rank(ascending=False, method="min")


def welch_ci(a, b):
    """Difference in means (a - b) with a Welch 95% confidence interval."""
    d = a.mean() - b.mean()
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = np.sqrt(va + vb)
    dof = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    t = stats.t.ppf(0.975, dof)
    return d, d - t * se, d + t * se


def main():
    df = pd.read_csv(PROCESSED / "metros.csv").set_index("market_id")
    p, z = pillar_scores(df)
    p["total_score"] = total(p, WEIGHTINGS["equal"])
    meta = df[["short_name", "market_title", "market_type", "nba_metro", "arena_ready", "population"]]

    # pillar_scores.csv: factor z-scores and pillar scores for every metro
    pillar_out = meta.join(z).join(p)
    pillar_out.to_csv(OUTPUTS / "pillar_scores.csv")

    # rankings.csv: overall rank, candidate rank, overlooked flag
    median_nba = p.loc[df["nba_metro"], "total_score"].median()
    r = meta.join(p)
    r["rank_all_metros"] = r["total_score"].rank(ascending=False, method="min").astype(int)
    r["rank_candidates"] = rank_candidates(df, p["total_score"])
    r["median_nba_score"] = median_nba
    r["overlooked"] = (~r["nba_metro"]) & (r["total_score"] >= median_nba)
    # which pillar contributes most to a metro's total (concentration check)
    contrib = p[PILLAR_NAMES] * 0.25
    r["top_pillar"] = contrib.idxmax(axis=1)
    r["top_pillar_share_of_positive"] = contrib.clip(lower=0).max(axis=1) / contrib.clip(lower=0).sum(axis=1).replace(0, np.nan)
    r = r.sort_values("total_score", ascending=False)
    r.to_csv(OUTPUTS / "rankings.csv")

    # nba_benchmark.csv: the current NBA metros scored the same way
    bench = r[r["nba_metro"]].copy()
    bench["n_nba_teams"] = df.loc[bench.index, "n_nba"]
    bench.to_csv(OUTPUTS / "nba_benchmark.csv")

    # validity.csv: does the scorecard recognise existing NBA markets?
    rows = []
    for col in PILLAR_NAMES + ["total_score"]:
        a, b = p.loc[df["nba_metro"], col].dropna(), p.loc[~df["nba_metro"], col].dropna()
        d, lo, hi = welch_ci(a, b)
        rpb, pval = stats.pointbiserialr(df["nba_metro"].astype(int), p[col])
        rows.append({"measure": col, "mean_nba": a.mean(), "mean_non_nba": b.mean(), "n_nba": len(a), "n_non_nba": len(b),
                     "diff_nba_minus_non": d, "ci95_low": lo, "ci95_high": hi, "point_biserial_r": rpb, "p_value": pval})
    pd.DataFrame(rows).to_csv(OUTPUTS / "validity.csv", index=False)

    # sensitivity.csv: candidate rank under each weighting
    sens = meta[~meta["nba_metro"]][["short_name", "arena_ready"]].copy()
    for name, w in WEIGHTINGS.items():
        if w == "ignore_competition":
            p2, _ = pillar_scores(df, ignore_competition=True)
            s = total(p2, WEIGHTINGS["equal"])
            sens[f"rank_{name}"] = rank_candidates(df, s)
        elif w == "arena_required":
            s = p["total_score"].where(df["arena_ready"] == 1)
            sens[f"rank_{name}"] = s[~df["nba_metro"]].rank(ascending=False, method="min")
        else:
            sens[f"rank_{name}"] = rank_candidates(df, total(p, w))
    rank_cols = [c for c in sens.columns if c.startswith("rank_")]
    sens["top10_frequency"] = (sens[rank_cols] <= 10).sum(axis=1)
    sens["best_rank"] = sens[rank_cols].min(axis=1)
    sens["worst_rank"] = sens[rank_cols].max(axis=1)
    sens = sens.sort_values("rank_equal")
    sens.to_csv(OUTPUTS / "sensitivity.csv")

    # rank decomposition: how did the top 10 move from v1 (CBSA, G League scored) to now?
    # step 1 = v1 archived output; step 2 = CSA markets but G League still scored; step 3 = final.
    with_gl = dict(PILLARS); with_gl["B_basketball_demand"] = PILLARS["B_basketball_demand"] + [("has_g_league", None, 1)]
    p_gl, _ = pillar_scores(df, pillars=with_gl)
    rank_gl = rank_candidates(df, total(p_gl, WEIGHTINGS["equal"]))
    v1 = pd.read_csv(OUTPUTS / "archive" / "rankings_v1_cbsa.csv")
    v1 = v1[~v1["nba_metro"]].set_index("short_name")["rank_candidates"]
    dec = r[~r["nba_metro"]][["short_name", "market_title", "rank_candidates", "top_pillar"]].copy()
    dec["rank_v1_cbsa_with_gleague"] = dec["short_name"].map(v1)
    dec["rank_csa_with_gleague"] = rank_gl
    dec = dec.rename(columns={"rank_candidates": "rank_final_csa_no_gleague"})
    keep = dec[(dec["rank_final_csa_no_gleague"] <= 10) | (dec["rank_v1_cbsa_with_gleague"] <= 10)]
    v1_lost = v1[(v1 <= 10) & ~v1.index.isin(dec["short_name"])]  # v1 top-10 metros absorbed into a bigger market
    lost = pd.DataFrame({"short_name": v1_lost.index, "rank_v1_cbsa_with_gleague": v1_lost.values,
                         "market_title": "merged into a larger CSA (see metros.csv member_metros)"})
    pd.concat([keep, lost]).sort_values(["rank_final_csa_no_gleague", "rank_v1_cbsa_with_gleague"]).to_csv(OUTPUTS / "top10_change.csv", index=False)

    print(r[["short_name", "nba_metro", "total_score", "rank_candidates", "overlooked", "top_pillar"]].head(25).to_string())
    print("median NBA score", round(median_nba, 3))
    print(pd.read_csv(OUTPUTS / "validity.csv").round(3).to_string())
    return r


if __name__ == "__main__":
    main()
