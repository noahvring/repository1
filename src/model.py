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

# ATTRACTIVENESS: how valuable is the market? pillar -> list of (column, transform, sign)
PILLARS = {
    "A_size_wealth": [("population", "log", 1), ("median_hh_income", None, 1), ("share_18_44", None, 1),
                      ("pop_growth_2020_2025", None, 1), ("gdp_2024_usd", "log", 1)],
    # G League presence is NOT scored: most G League teams are NBA-owned affiliates near their parent
    # club, so it would flatter existing NBA markets. It stays in metros.csv as a descriptive column.
    "B_basketball_demand": [("ncaa_att_per_1k", None, 1), ("has_wnba", None, 1)],
    "C_corporate": [("large_establishments_500plus", "log", 1), ("large_est_per_100k", None, 1)],
}
PILLAR_NAMES = list(PILLARS)

# EASE OF ENTRY: how hard is it to get in? Kept on its own axis (v3) so competition is not
# double-counted in attractiveness. Distance to the nearest other NBA market proxies for
# cannibalization of existing teams' fans (farther = easier).
EASE = [("arena_available", None, 1), ("miles_to_nearest_nba", "log", 1), ("big4_other_leagues", None, -1)]

WEIGHTINGS = {  # weights on pillars A, B, C
    "equal": [1 / 3, 1 / 3, 1 / 3],
    "size_heavy": [0.5, 0.25, 0.25],
    "wealth_corporate_heavy": [0.25, 0.25, 0.5],
    "demand_heavy": [0.25, 0.5, 0.25],
    "no_college": "no_college",          # equal weights, Pillar B without NCAA attendance
    "arena_required": "arena_required",  # equal weights, only arena-ready candidates ranked
}
N_DRAWS, SEED = 10_000, 42


def zscore(s):
    return (s - s.mean()) / s.std(ddof=0)


def factor_z(df, pillars=None):
    z = pd.DataFrame(index=df.index)
    for pillar, factors in (pillars or PILLARS).items():
        for col, tr, sign in factors:
            x = np.log(df[col]) if tr == "log" else df[col].astype(float)
            z[f"z_{col}"] = sign * zscore(x)
    return z


def pillar_scores(df, pillars=None):
    pillars = pillars or PILLARS
    z = factor_z(df, pillars)
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


def monte_carlo(df, p):
    """10,000 random pillar weightings drawn from a Dirichlet(1,1,1): every weighting is equally
    likely and expected weights are equal (1/3 each). Rank non-NBA markets under each draw."""
    rng = np.random.default_rng(SEED)
    W = rng.dirichlet(np.ones(len(PILLAR_NAMES)), size=N_DRAWS)          # draws x pillars
    cand = p.loc[~df["nba_metro"], PILLAR_NAMES]
    scores = cand.to_numpy() @ W.T                                         # markets x draws
    ranks = (-scores).argsort(axis=0).argsort(axis=0) + 1                  # 1 = best in each draw
    out = pd.DataFrame(index=cand.index)
    out["short_name"] = df.loc[cand.index, "short_name"]
    out["p_top5"] = (ranks <= 5).mean(axis=1)
    out["p_top10"] = (ranks <= 10).mean(axis=1)
    out["median_rank"] = np.median(ranks, axis=1)
    out["rank_p05"] = np.percentile(ranks, 5, axis=1)
    out["rank_p95"] = np.percentile(ranks, 95, axis=1)
    out["n_draws"], out["seed"] = N_DRAWS, SEED
    out.sort_values(["p_top10", "median_rank"], ascending=[False, True]).to_csv(OUTPUTS / "monte_carlo.csv")
    return out


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
    # arena available: a 17,000+ seat arena without an NBA tenant (candidates) or the existing
    # NBA arena (current NBA markets), so the benchmark is comparable
    df["arena_available"] = np.where(df["nba_metro"], df["arena_capable"], df["arena_ready"])
    p, z = pillar_scores(df)
    p["total_score"] = total(p, WEIGHTINGS["equal"])
    ez, _ = pillar_scores(df, {"ease": EASE})
    p["ease_of_entry"] = ez["ease"]
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
    contrib = p[PILLAR_NAMES] / 3
    r["top_pillar"] = contrib.idxmax(axis=1)
    r["top_pillar_share_of_positive"] = contrib.clip(lower=0).max(axis=1) / contrib.clip(lower=0).sum(axis=1).replace(0, np.nan)
    nba_mask = df["nba_metro"]
    a_med, e_med = p.loc[nba_mask, "total_score"].median(), p.loc[nba_mask, "ease_of_entry"].median()
    r["ease_median_nba"] = e_med
    r["quadrant"] = np.select(
        [(r.total_score >= a_med) & (r.ease_of_entry >= e_med), (r.total_score >= a_med) & (r.ease_of_entry < e_med),
         (r.total_score < a_med) & (r.ease_of_entry >= e_med)],
        ["Prime targets", "Attractive but hard to enter", "Easy but small"], "Deprioritize")
    r = r.join(df[["miles_to_nearest_nba", "nba_markets_within_200mi", "big4_other_leagues", "arena_available"]])
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
        if w == "no_college":
            nc = dict(PILLARS); nc["B_basketball_demand"] = [f for f in PILLARS["B_basketball_demand"] if f[0] != "ncaa_att_per_1k"]
            p2, _ = pillar_scores(df, nc)
            sens[f"rank_{name}"] = rank_candidates(df, total(p2, WEIGHTINGS["equal"]))
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

    monte_carlo(df, p)

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
