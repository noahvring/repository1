"""Market scorecard: attractiveness (pillars A-C) and ease of entry, both as means of factor z-scores.

Skewed counts are logged first. NBA and non-NBA markets are scored the same way, so current
NBA markets act as the benchmark. Partial-data markets are scored separately at the end.
"""
import numpy as np
import pandas as pd
from scipy import stats
from config import PROCESSED, OUTPUTS, MANUAL
from build_metros import haversine_miles

# pillar -> list of (column, transform, sign)
PILLARS = {
    "A_size_wealth": [("population", "log", 1), ("median_hh_income", None, 1), ("share_18_44", None, 1),
                      ("pop_growth_2020_2025", None, 1), ("gdp_2024_usd", "log", 1)],
    # G League is not scored: most teams are NBA-owned affiliates near their parent club
    "B_basketball_demand": [("ncaa_att_per_1k", None, 1), ("has_wnba", None, 1)],
    "C_corporate": [("large_establishments_500plus", "log", 1), ("large_est_per_100k", None, 1)],
}
PILLAR_NAMES = list(PILLARS)
NO_COLLEGE = {**PILLARS, "B_basketball_demand": [("has_wnba", None, 1)]}
WITH_G_LEAGUE = {**PILLARS, "B_basketball_demand": PILLARS["B_basketball_demand"] + [("has_g_league", None, 1)]}

# separate axis so competition is not double-counted; distance proxies fan cannibalization
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
    out = pd.DataFrame({name: z[[f"z_{c}" for c, _, _ in factors]].mean(axis=1) for name, factors in pillars.items()})
    return out, z


def total(p, w):
    return (p[PILLAR_NAMES] * np.array(w)).sum(axis=1)


def rank_candidates(df, score):
    """Rank among non-NBA markets (1 = most attractive)."""
    return score[~df["nba_metro"]].rank(ascending=False, method="min")


def quadrant(score, ease, a_med, e_med):
    return np.select([(score >= a_med) & (ease >= e_med), (score >= a_med) & (ease < e_med), (score < a_med) & (ease >= e_med)],
                     ["Prime targets", "Attractive but hard to enter", "Easy but small"], "Deprioritize")


def monte_carlo(df, p):
    """Rank non-NBA markets under 10,000 Dirichlet(1,1,1) pillar weightings (mean weight 1/3 each)."""
    W = np.random.default_rng(SEED).dirichlet(np.ones(len(PILLAR_NAMES)), size=N_DRAWS)  # draws x pillars
    cand = p.loc[~df["nba_metro"], PILLAR_NAMES]
    ranks = (-(cand.to_numpy() @ W.T)).argsort(axis=0).argsort(axis=0) + 1  # markets x draws, 1 = best
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


def fan_behavior(df, p, sens):
    """Descriptive, not scored: transplant share, and whether college attendance tracks the
    score without college among NBA markets (association only)."""
    score_nc = total(pillar_scores(df, NO_COLLEGE)[0], WEIGHTINGS["equal"])
    nba = df["nba_metro"]
    r, pval = stats.pearsonr(df.loc[nba, "ncaa_att_per_1k"], score_nc[nba])
    top_eq, top_nc = set(sens.index[sens["rank_equal"] <= 10]), set(sens.index[sens["rank_no_college"] <= 10])
    pd.DataFrame([{"n_nba_markets": int(nba.sum()), "pearson_r_college_att_vs_score_without_college": r, "p_value": pval,
                   "top10_overlap_equal_vs_no_college": len(top_eq & top_nc),
                   "dropped_from_top10_without_college": "; ".join(sorted(df.loc[list(top_eq - top_nc), "short_name"])),
                   "added_to_top10_without_college": "; ".join(sorted(df.loc[list(top_nc - top_eq), "short_name"]))}]
                 ).to_csv(OUTPUTS / "college_vs_pro.csv", index=False)
    fb = df.loc[~nba, ["short_name", "transplant_share", "born_other_us_state_share", "ncaa_att_per_1k"]].copy()
    fb[["rank_equal", "rank_no_college"]] = sens[["rank_equal", "rank_no_college"]]
    fb["rank_change_without_college"] = fb["rank_no_college"] - fb["rank_equal"]
    fb["transplant_share_vs_nba_median"] = fb["transplant_share"] - df.loc[nba, "transplant_share"].median()
    fb.sort_values("rank_equal").to_csv(OUTPUTS / "fan_behavior.csv")


def welch_ci(a, b):
    """Difference in means (a - b) with a Welch 95% confidence interval."""
    d = a.mean() - b.mean()
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = np.sqrt(va + vb)
    dof = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    t = stats.t.ppf(0.975, dof)
    return d, d - t * se, d + t * se


def mexico_city_row(df):
    """Mexico City on the factors with a comparable source (data/manual/international_markets.csv)."""
    intl = pd.read_csv(MANUAL / "international_markets.csv")
    mx = intl[intl.market == "Mexico City"].set_index("item")["value"]
    lat, lon = float(mx["latitude"]), float(mx["longitude"])
    nba = df[df["nba_metro"]]
    tor = intl[intl.market == "Toronto"].set_index("item")["value"].astype(float)
    d = np.append(haversine_miles(lat, lon, nba["lat"].values, nba["lon"].values),
                  haversine_miles(lat, lon, tor["latitude"], tor["longitude"]))
    return pd.DataFrame([{
        "short_name": "Mexico City", "market_title": "Greater Mexico City (Mexico)", "market_type": "International",
        "nba_metro": False, "partial_data": True, "population": float(mx["metro_population"]),
        "gdp_2024_usd": float(mx["metro_gdp_usd_nominal_2024"]), "has_wnba": 0,
        "big4_other_leagues": int(float(mx["big_league_teams_nfl_mlb_nhl"])),
        "arena_ready": int(float(mx["largest_arena_capacity"]) >= 17000), "arena_available": int(float(mx["largest_arena_capacity"]) >= 17000),
        "max_arena_capacity": float(mx["largest_arena_capacity"]), "has_g_league": 1,
        "lat": lat, "lon": lon, "miles_to_nearest_nba": d.min(), "nba_markets_within_200mi": int((d <= 200).sum()),
    }], index=pd.Index(["INTL-Mexico City"], name="market_id"))


def score_partial(part, ref, r):
    """Score partial-data markets with the U.S. markets' means and SDs (U.S. results unchanged).
    Pillars average the factors present; the total averages the pillars present."""
    out = part[["short_name", "market_title", "market_type", "nba_metro", "arena_ready", "population"]].copy()
    used = {i: [] for i in part.index}
    for pillar, factors in {**PILLARS, "ease": EASE}.items():
        zs = []
        for col, tr, sign in factors:
            xr = np.log(ref[col]) if tr == "log" else ref[col].astype(float)
            x = np.log(part[col]) if tr == "log" else part[col].astype(float)
            zs.append(sign * (x - xr.mean()) / xr.std(ddof=0))
            for i in part.index[x.notna()]:
                used[i].append(col)
        out[pillar if pillar != "ease" else "ease_of_entry"] = pd.concat(zs, axis=1).mean(axis=1)
    out["total_score"] = out[PILLAR_NAMES].mean(axis=1)
    out["factors_used"] = [", ".join(used[i]) for i in out.index]
    cand = r[~r["nba_metro"]]
    out["rank_if_included"] = [int((cand["total_score"] > s).sum() + 1) for s in out["total_score"]]
    a_med, e_med = r["median_nba_score"].iloc[0], r["ease_median_nba"].iloc[0]
    out["quadrant"] = quadrant(out.total_score, out.ease_of_entry, a_med, e_med)
    out["median_nba_score"], out["ease_median_nba"] = a_med, e_med
    out["partial_data"] = True
    for c in ["miles_to_nearest_nba", "nba_markets_within_200mi", "big4_other_leagues", "arena_available", "transplant_share"]:
        out[c] = part.get(c)
    return out


def main():
    df_all = pd.read_csv(PROCESSED / "metros.csv").set_index("market_id")
    df = df_all[~df_all["partial_data"]].copy()  # partial-data markets are scored at the end
    # NBA markets count their own arena, so the benchmark is comparable
    df["arena_available"] = np.where(df["nba_metro"], df["arena_capable"], df["arena_ready"])
    p, z = pillar_scores(df)
    p["total_score"] = total(p, WEIGHTINGS["equal"])
    p["ease_of_entry"] = pillar_scores(df, {"ease": EASE})[0]["ease"]
    meta = df[["short_name", "market_title", "market_type", "nba_metro", "arena_ready", "population"]]

    meta.join(z).join(p).to_csv(OUTPUTS / "pillar_scores.csv")

    median_nba = p.loc[df["nba_metro"], "total_score"].median()
    r = meta.join(p)
    r["rank_all_metros"] = r["total_score"].rank(ascending=False, method="min").astype(int)
    r["rank_candidates"] = rank_candidates(df, p["total_score"])
    r["median_nba_score"] = median_nba
    r["overlooked"] = (~r["nba_metro"]) & (r["total_score"] >= median_nba)
    # concentration check: which pillar contributes most
    contrib = p[PILLAR_NAMES] / 3
    r["top_pillar"] = contrib.idxmax(axis=1)
    r["top_pillar_share_of_positive"] = contrib.clip(lower=0).max(axis=1) / contrib.clip(lower=0).sum(axis=1).replace(0, np.nan)
    e_med = p.loc[df["nba_metro"], "ease_of_entry"].median()
    r["ease_median_nba"] = e_med
    r["quadrant"] = quadrant(r.total_score, r.ease_of_entry, median_nba, e_med)
    r = r.join(df[["miles_to_nearest_nba", "nba_markets_within_200mi", "big4_other_leagues", "arena_available"]])
    r = r.sort_values("total_score", ascending=False)
    r["partial_data"] = False
    part = df_all[df_all["partial_data"]].copy()
    part["arena_available"] = part["arena_ready"]
    part = pd.concat([part, mexico_city_row(df)])
    score_partial(part, df, r).to_csv(OUTPUTS / "partial_markets.csv")
    r.to_csv(OUTPUTS / "rankings.csv")

    bench = r[r["nba_metro"]].copy()
    bench["n_nba_teams"] = df.loc[bench.index, "n_nba"]
    bench.to_csv(OUTPUTS / "nba_benchmark.csv")

    # validity: does the scorecard separate existing NBA markets from the rest?
    rows = []
    for col in PILLAR_NAMES + ["total_score"]:
        a, b = p.loc[df["nba_metro"], col].dropna(), p.loc[~df["nba_metro"], col].dropna()
        d, lo, hi = welch_ci(a, b)
        rpb, pval = stats.pointbiserialr(df["nba_metro"].astype(int), p[col])
        rows.append({"measure": col, "mean_nba": a.mean(), "mean_non_nba": b.mean(), "n_nba": len(a), "n_non_nba": len(b),
                     "diff_nba_minus_non": d, "ci95_low": lo, "ci95_high": hi, "point_biserial_r": rpb, "p_value": pval})
    pd.DataFrame(rows).to_csv(OUTPUTS / "validity.csv", index=False)

    sens = meta[~meta["nba_metro"]][["short_name", "arena_ready"]].copy()
    for name, w in WEIGHTINGS.items():
        if w == "no_college":
            sens[f"rank_{name}"] = rank_candidates(df, total(pillar_scores(df, NO_COLLEGE)[0], WEIGHTINGS["equal"]))
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
    fan_behavior(df, p, sens)

    # how the top 10 moved: v1 (CBSA, G League scored) -> CSA with G League -> current
    rank_gl = rank_candidates(df, total(pillar_scores(df, WITH_G_LEAGUE)[0], WEIGHTINGS["equal"]))
    v1 = pd.read_csv(OUTPUTS / "archive" / "rankings_v1_cbsa.csv")
    v1 = v1[~v1["nba_metro"]].set_index("short_name")["rank_candidates"]
    dec = r[~r["nba_metro"]][["short_name", "market_title", "rank_candidates", "top_pillar"]].copy()
    dec["rank_v1_cbsa_with_gleague"] = dec["short_name"].map(v1)
    dec["rank_csa_with_gleague"] = rank_gl
    dec = dec.rename(columns={"rank_candidates": "rank_final_csa_no_gleague"})
    keep = dec[(dec["rank_final_csa_no_gleague"] <= 10) | (dec["rank_v1_cbsa_with_gleague"] <= 10)]
    v1_lost = v1[(v1 <= 10) & ~v1.index.isin(dec["short_name"])]  # merged into a bigger market
    lost = pd.DataFrame({"short_name": v1_lost.index, "rank_v1_cbsa_with_gleague": v1_lost.values,
                         "market_title": "merged into a larger CSA (see metros.csv member_metros)"})
    pd.concat([keep, lost]).sort_values(["rank_final_csa_no_gleague", "rank_v1_cbsa_with_gleague"]).to_csv(OUTPUTS / "top10_change.csv", index=False)

    print(r[["short_name", "nba_metro", "total_score", "rank_candidates", "overlooked", "top_pillar"]].head(25).to_string())
    print("median NBA score", round(median_nba, 3))
    print(pd.read_csv(OUTPUTS / "validity.csv").round(3).to_string())
    return r


if __name__ == "__main__":
    main()
