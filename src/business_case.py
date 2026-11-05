"""Scenario business case for the top-8 candidates, owner economics and bidder multiples.

Local revenue (2025-26 USD/yr) = average NBA team revenue by stream (Sportico), scaled by how
the market compares with the median NBA market:
  gate (seating & suites)  = avg x (pop index x income index) ^ e
  sponsorship              = avg x (large-establishment index) ^ e
  local media              = avg x (pop index) ^ e x fan multiplier (Pillar B)
  other (concessions etc.) = avg x (pop index) ^ e
where e = revenue elasticity.

Owners: each existing team gets fee x 2 / 30 once and loses pool x (1/30 - 1/32) a year
(pool = shared league revenue); 20-year NPV under growth x discount scenarios.
"""
import numpy as np
import pandas as pd
from config import MANUAL, OUTPUTS, PROCESSED

SCEN = ["low", "base", "high"]
# reported front-runners plus markets often named in coverage
FOCUS_US = ["Seattle", "Las Vegas", "Pittsburgh", "Louisville", "Kansas City", "Nashville", "Austin",
            "San Diego", "St. Louis", "Columbus, OH", "Cincinnati", "Raleigh", "Tampa", "Baltimore", "Omaha"]
STREAMS = ["gate", "sponsorship", "local_media", "other"]


def load_assumptions():
    """Scenario name -> {assumption: value}."""
    a = pd.read_csv(MANUAL / "assumptions.csv").set_index("assumption")
    return {s: a[s].to_dict() for s in SCEN}


def averages(A):
    """Average NBA team revenue by stream (USD/yr), from reported league totals / 30."""
    return {"gate": A["seating_suites_revenue_usd"] / 30, "sponsorship": A["sponsorship_revenue_usd"] / 30,
            "local_media": A["local_media_share"] * A["team_revenue_2025_26_usd"] / 30,
            "other": A["other_local_revenue_usd"] / 30}


def local_revenue(m, ref, A, elast=None):
    """elast: optional {stream: elasticity} override, used by the tornado."""
    e = {s: A["revenue_elasticity"] for s in STREAMS} | (elast or {})
    avg = averages(A)
    pop_i = m["population"] / ref["population"]
    inc_i = m["median_hh_income"] / ref["median_hh_income"]
    est_i = m["large_establishments_500plus"] / ref["large_establishments_500plus"]
    fan = (1 + A["fan_multiplier_slope"] * m["B_basketball_demand"]).clip(0.5, 1.5)
    out = pd.DataFrame({
        "gate": avg["gate"] * (pop_i * inc_i) ** e["gate"],
        "sponsorship": avg["sponsorship"] * est_i ** e["sponsorship"],
        "local_media": avg["local_media"] * pop_i ** e["local_media"] * fan,
        "other": avg["other"] * pop_i ** e["other"],
    })
    out["total"] = out[STREAMS].sum(axis=1)
    return out


def pick_top8(r):
    cand = r[~r["nba_metro"]].sort_values("rank_candidates")
    top = cand.head(8)
    for must in ["Seattle", "Las Vegas"]:
        if must not in set(top["short_name"]):
            top = pd.concat([top.iloc[:-1], cand[cand.short_name == must]])
    return top.index.tolist()


def owner_npv(S):
    """NPV of dilution vs fee share over a grid of pool definitions, growth, discount and fee."""
    b = S["base"]
    pools = {"national_tv_only": b["national_tv_per_team_2025_26_usd"] * 30,
             "all_central_revenue": b["central_revenue_share"] * b["team_revenue_2025_26_usd"]}
    owner_shares = {"gross": 1.0, "net_of_player_share": 1 - b["player_share_of_bri"]}
    years_to_start = int(b["first_expansion_season"]) - 2025  # pool is reported for 2025-26
    horizon = int(b["npv_horizon_years"])
    rows = []
    for pool_name, pool0 in pools.items():
        for own_name, own in owner_shares.items():
            for g in sorted({S[s]["media_growth"] for s in SCEN}):
                for r in sorted({S[s]["discount_rate"] for s in SCEN}):
                    for fee_s in SCEN:
                        fee = S[fee_s]["expansion_fee_per_team_usd"]
                        fee_share = fee * 2 / 30
                        pool_start = pool0 * (1 + g) ** years_to_start
                        t = np.arange(1, horizon + 1)
                        dil = own * pool_start * (1 + g) ** (t - 1) * (1 / 30 - 1 / 32)
                        pv = (dil / (1 + r) ** t).sum()
                        rows.append({"pool_definition": pool_name, "owner_share": own_name, "media_growth": g,
                                     "discount_rate": r, "fee_scenario": fee_s, "expansion_fee_per_team": fee,
                                     "fee_share_per_existing_team": fee_share, "pool_first_season": pool_start,
                                     "dilution_first_season": dil[0], "dilution_year_20": dil[-1],
                                     "npv_dilution_20y": pv, "npv_net_of_fee": fee_share - pv,
                                     "fee_covers_dilution": fee_share >= pv})
    return pd.DataFrame(rows)


def breakeven_growth(S):
    """Annual growth in shared revenue at which 20-year NPV of dilution equals the fee share
    (bisection search), for each discount rate and fee scenario; all central revenue, gross."""
    b = S["base"]
    pool0 = b["central_revenue_share"] * b["team_revenue_2025_26_usd"]
    yrs = int(b["first_expansion_season"]) - 2025
    t = np.arange(1, int(b["npv_horizon_years"]) + 1)
    rows = []
    for r in sorted({S[s]["discount_rate"] for s in SCEN}):
        for fee_s in SCEN:
            fee_share = S[fee_s]["expansion_fee_per_team_usd"] * 2 / 30
            npv = lambda g: (pool0 * (1 + g) ** yrs * (1 + g) ** (t - 1) * (1 / 30 - 1 / 32) / (1 + r) ** t).sum()
            lo, hi = 0.0, 1.0
            for _ in range(60):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if npv(mid) < fee_share else (lo, mid)
            rows.append({"discount_rate": r, "fee_scenario": fee_s, "fee_share_per_existing_team": fee_share,
                         "breakeven_growth": (lo + hi) / 2})
    return pd.DataFrame(rows)


def bidder_multiples(m, ref, S, ids):
    """Price / estimated revenue vs league-average value / revenue (Sportico).
    Revenue = local estimate + 1/32 of central revenue."""
    b = S["base"]
    central_share = b["central_revenue_share"] * b["team_revenue_2025_26_usd"] / 32
    league_mult = b["avg_franchise_value_usd"] / b["avg_team_revenue_usd"]
    rows = []
    for cid in ids:
        name = m.at[cid, "short_name"]
        local = {s: local_revenue(m.loc[[cid]], ref, S[s])["total"].iloc[0] for s in SCEN}
        lo_l, hi_l = min(local.values()), max(local.values())
        is_lv = name == "Las Vegas"
        price, ptype, basis = {
            "Las Vegas": (b["las_vegas_reported_price_usd"], "reported expected sale price (bid)", "ESPN: franchise expected to go for ~$10B; three competing bids"),
            "Seattle": (b["seattle_reported_valuation_usd"], "reported valuation estimate (not a bid)", "ESPN: sources estimate the leading group's valuation at ~$6B"),
        }.get(name, (b["expansion_fee_per_team_usd"], "assumed fee", "base fee: midpoint of reported $7-10B range"))
        rev_base = local["base"] + central_share
        rows.append({"market_id": cid, "short_name": name,
                     "price_usd": price, "price_type": ptype, "price_basis": basis,
                     "est_revenue_base_usd": rev_base, "est_revenue_low_usd": lo_l + central_share, "est_revenue_high_usd": hi_l + central_share,
                     "central_revenue_share_usd": central_share,
                     "price_to_revenue_base": price / rev_base,
                     "price_to_revenue_range": f"{price / (hi_l + central_share):.1f}x-{price / (lo_l + central_share):.1f}x",
                     "price_incl_arena_to_revenue_base": (price + b["las_vegas_arena_cost_usd"]) / rev_base if is_lv else np.nan,
                     "league_avg_value_to_revenue": league_mult,
                     "premium_vs_league_avg_multiple": price / rev_base / league_mult - 1})
    pd.DataFrame(rows).sort_values("price_to_revenue_base").to_csv(OUTPUTS / "bidder_multiples.csv", index=False)


def main():
    S = load_assumptions()
    metros = pd.read_csv(PROCESSED / "metros.csv").set_index("market_id")
    rank = pd.read_csv(OUTPUTS / "rankings.csv").set_index("market_id")
    sens = pd.read_csv(OUTPUTS / "sensitivity.csv").set_index("market_id")
    m = metros.join(rank[["A_size_wealth", "B_basketball_demand", "C_corporate", "ease_of_entry", "quadrant", "total_score", "rank_candidates"]])
    ref = m.loc[m["nba_metro"], ["population", "median_hh_income", "large_establishments_500plus"]].median()
    ids = pick_top8(m)

    # elasticity calibration: Warriors' vs Grizzlies' market
    sf, mem = m[m.short_name == "San Francisco"].iloc[0], m[m.short_name == "Memphis"].iloc[0]
    b = S["base"]
    e_cal = np.log(b["team_revenue_max_usd"] / b["team_revenue_min_usd"]) / np.log(sf.population / mem.population)
    pd.DataFrame([{"high_revenue_team_market": sf.market_title, "low_revenue_team_market": mem.market_title,
                   "revenue_ratio": b["team_revenue_max_usd"] / b["team_revenue_min_usd"], "population_ratio": sf.population / mem.population,
                   "implied_elasticity": e_cal}]).to_csv(OUTPUTS / "business_case_calibration.csv", index=False)

    rev = {s: local_revenue(m.loc[ids], ref, S[s]) for s in SCEN}
    rows = [{"market_id": cid, "short_name": m.at[cid, "short_name"], "scenario": s, **r.to_dict()}
            for s in SCEN for cid, r in rev[s].iterrows()]
    pd.DataFrame(rows).to_csv(OUTPUTS / "local_revenue_scenarios.csv", index=False)

    npv = owner_npv(S)
    npv.to_csv(OUTPUTS / "owner_npv.csv", index=False)
    breakeven_growth(S).to_csv(OUTPUTS / "owner_breakeven_growth.csv", index=False)

    # tornado: swing in combined top-8 base local revenue from each assumption's low/high value
    def total_rev(A, elast=None):
        return local_revenue(m.loc[ids], ref, A, elast)["total"].sum()

    torn = [{"assumption": f"elasticity_{st}", "low_value": S["low"]["revenue_elasticity"], "high_value": S["high"]["revenue_elasticity"],
             "total_at_low": total_rev(S["base"], {st: S["low"]["revenue_elasticity"]}),
             "total_at_high": total_rev(S["base"], {st: S["high"]["revenue_elasticity"]})} for st in STREAMS]
    torn.append({"assumption": "fan_multiplier_slope", "low_value": S["low"]["fan_multiplier_slope"], "high_value": S["high"]["fan_multiplier_slope"],
                 "total_at_low": total_rev(S["base"] | {"fan_multiplier_slope": S["low"]["fan_multiplier_slope"]}),
                 "total_at_high": total_rev(S["base"] | {"fan_multiplier_slope": S["high"]["fan_multiplier_slope"]})})
    t = pd.DataFrame(torn)
    t["base_total"] = rev["base"]["total"].sum()
    t["swing"] = (t.total_at_high - t.total_at_low).abs()
    t.sort_values("swing", ascending=False).to_csv(OUTPUTS / "tornado.csv", index=False)

    def kpis(idx):
        k = m.loc[idx, ["short_name", "market_title", "rank_candidates", "total_score", "A_size_wealth", "B_basketball_demand", "C_corporate",
                        "ease_of_entry", "quadrant", "miles_to_nearest_nba", "population", "median_hh_income", "pop_growth_2020_2025", "large_est_per_100k",
                        "big4_other_leagues", "arena_ready", "largest_arena_no_nba_tenant", "has_g_league", "nba_metro"]].copy()
        k["top10_frequency"] = sens.reindex(idx)["top10_frequency"]
        k["fan_interest_index"] = k["B_basketball_demand"]
        k["arena_ready"] = np.where(k["arena_ready"] == 1, "Y", "N")
        # elasticity lowers revenue for small markets and raises it for large ones, so low/high = min/max
        scen = pd.concat({s: local_revenue(m.loc[idx], ref, S[s])["total"] for s in SCEN}, axis=1)
        k["est_local_revenue_low"] = scen.min(axis=1)
        k["est_local_revenue_base"] = scen["base"]
        k["est_local_revenue_high"] = scen.max(axis=1)
        k["local_revenue_per_capita_base"] = k["est_local_revenue_base"] / k["population"]
        dem = pd.read_csv(OUTPUTS / "demand_summary.csv").set_index("market")
        k["demand_events"] = k["short_name"].map(dem["events"]).fillna(0).astype(int)
        k["demand_nba_games"] = k["short_name"].map(dem["nba_games"]).fillna(0).astype(int)
        return k.rename(columns={"rank_candidates": "attractiveness_rank", "big4_other_leagues": "competing_teams"})

    kpis(ids).sort_values("attractiveness_rank").to_csv(OUTPUTS / "kpi_dashboard.csv")
    bidder_multiples(m, ref, S, ids)

    # focus markets: U.S. ones scored; international ones get sourced facts only
    focus_ids = [i for n in FOCUS_US for i in m.index[m["member_metros"].fillna("").str.contains(n, regex=False)][:1]]
    f = kpis(focus_ids)
    f["focus_label"] = [next(n for n in FOCUS_US if n in m.at[i, "member_metros"]) for i in f.index]
    f["scored"] = "Y"
    intl = pd.read_csv(MANUAL / "international_markets.csv")
    extra = []
    for mk, g in intl[intl.market.isin(["Mexico City", "Vancouver"])].groupby("market", sort=False):
        d = dict(zip(g["item"], g["value"]))
        extra.append({"short_name": mk, "focus_label": mk, "scored": "N (outside U.S. data)",
                      "population": float(d.get("metro_population", np.nan)),
                      "largest_arena_no_nba_tenant": f"capacity {d.get('largest_arena_capacity')} (see international_markets.csv)",
                      "has_g_league": 1 if "g_league_team" in d else 0})
    f = pd.concat([f, pd.DataFrame(extra).set_index(pd.Index(["INTL-" + e["short_name"] for e in extra]))])
    f.index.name = "market_id"
    f.to_csv(OUTPUTS / "focus_markets.csv")
    print(kpis(ids).sort_values("attractiveness_rank")[["short_name", "attractiveness_rank", "est_local_revenue_low", "est_local_revenue_base", "est_local_revenue_high"]].to_string())
    print("elasticity calibration", round(e_cal, 3))
    base = npv[(npv.pool_definition == "all_central_revenue") & (npv.owner_share == "gross") & (npv.fee_scenario == "base")]
    print(base[["media_growth", "discount_rate", "npv_dilution_20y", "npv_net_of_fee"]].to_string())
    print("share of all grid cells where fee covers dilution:", npv["fee_covers_dilution"].mean())
    return m, ref, S, kpis


if __name__ == "__main__":
    main()
