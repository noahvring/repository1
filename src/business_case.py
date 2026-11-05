"""Phase 3: scenario business case for the top-8 candidate markets.

Local revenue (per year) = gate + sponsorship + local media
  gate        = arena capacity x attendance rate x home games x revenue per attendee x income index
  sponsorship = large establishments (500+ employees) x sponsorship per establishment
  local media = population x local media per resident x fan multiplier
National revenue per team = shared national pool / number of teams (30 before, 32 after).
Dilution = what each existing team gives up per year when the pool is split 32 ways.
Payback = one-time fee each existing team receives (fee x 2 / 30) / annual dilution.
These are scenarios built on labeled assumptions, not forecasts.
"""
import numpy as np
import pandas as pd
from config import MANUAL, OUTPUTS, PROCESSED

SCEN = ["low", "base", "high"]


def load_assumptions():
    a = pd.read_csv(MANUAL / "assumptions.csv").set_index("assumption")
    return {s: a[s].to_dict() for s in SCEN}, a


def local_revenue(m, A, income_ref):
    cap = m["max_capacity_no_nba_tenant"].fillna(A["arena_capacity_if_none"])
    income_index = m["median_hh_income"] / income_ref
    gate = cap * A["attendance_rate"] * A["home_games"] * A["gate_revenue_per_attendee_usd"] * income_index
    spons = m["large_establishments_500plus"] * A["sponsorship_per_large_establishment_usd"]
    fan_mult = (1 + A["fan_multiplier_slope"] * m["B_basketball_demand"]).clip(0.5, 1.5)
    media = m["population"] * A["local_media_per_resident_usd"] * fan_mult
    return pd.DataFrame({"gate": gate, "sponsorship": spons, "local_media": media, "total": gate + spons + media})


def top8():
    r = pd.read_csv(OUTPUTS / "rankings.csv", dtype={"cbsa_code": str})
    cand = r[~r["nba_metro"]].sort_values("rank_candidates")
    top = cand.head(8)
    for must in ["Seattle", "Las Vegas"]:
        if must not in set(top["short_name"]):
            top = pd.concat([top.iloc[:-1], cand[cand.short_name == must]])
    return top["cbsa_code"].tolist()


def main():
    S, table = load_assumptions()
    metros = pd.read_csv(PROCESSED / "metros.csv", dtype={"cbsa_code": str}).set_index("cbsa_code")
    rank = pd.read_csv(OUTPUTS / "rankings.csv", dtype={"cbsa_code": str}).set_index("cbsa_code")
    sens = pd.read_csv(OUTPUTS / "sensitivity.csv", dtype={"cbsa_code": str}).set_index("cbsa_code")
    m = metros.join(rank[["A_size_wealth", "B_basketball_demand", "C_corporate", "D_competition_infra", "total_score", "rank_candidates"]])
    income_ref = metros.loc[metros["nba_metro"], "median_hh_income"].median()  # median NBA-metro income
    ids = top8()

    # ---- local revenue by scenario
    rev = {s: local_revenue(m.loc[ids], S[s], income_ref) for s in SCEN}
    rows = []
    for s in SCEN:
        for cid, r in rev[s].iterrows():
            rows.append({"cbsa_code": cid, "short_name": m.at[cid, "short_name"], "scenario": s, **r.to_dict()})
    pd.DataFrame(rows).to_csv(OUTPUTS / "local_revenue_scenarios.csv", index=False)

    # ---- national revenue, dilution, payback
    out = []
    # owner view: 'low' payback = owner-favourable (high fee, small pool); 'high' = owner-unfavourable
    combos = {"owner_favorable": ("high", "low"), "base": ("base", "base"), "owner_unfavorable": ("low", "high")}
    for name, (fee_s, pool_s) in combos.items():
        media_annual = S[pool_s]["national_media_total_usd"] / S[pool_s]["national_media_years"]
        pool = media_annual * (1 + S[pool_s]["other_shared_revenue_uplift"])
        per30, per32 = pool / 30, pool / 32
        dilution = per30 - per32
        fee = S[fee_s]["expansion_fee_per_team_usd"]
        fee_per_owner = fee * 2 / 30
        out.append({"scenario": name, "expansion_fee_per_team": fee, "shared_pool_annual": pool,
                    "national_rev_per_team_30": per30, "national_rev_per_team_32": per32,
                    "annual_dilution_per_existing_team": dilution, "fee_received_per_existing_team": fee_per_owner,
                    "breakeven_years": fee_per_owner / dilution})
    pd.DataFrame(out).to_csv(OUTPUTS / "dilution_payback.csv", index=False)

    # ---- tornado: swing in base-case local revenue (sum over top 8) per assumption
    base_total = local_revenue(m.loc[ids], S["base"], income_ref)["total"].sum()
    torn = []
    for key in ["arena_capacity_if_none", "attendance_rate", "gate_revenue_per_attendee_usd",
                "sponsorship_per_large_establishment_usd", "local_media_per_resident_usd", "fan_multiplier_slope"]:
        vals = {}
        for s in ["low", "high"]:
            A = dict(S["base"]); A[key] = S[s][key]
            vals[s] = local_revenue(m.loc[ids], A, income_ref)["total"].sum()
        torn.append({"assumption": key, "low_value": S["low"][key], "high_value": S["high"][key],
                     "total_at_low": vals["low"], "total_at_high": vals["high"], "base_total": base_total,
                     "swing": abs(vals["high"] - vals["low"])})
    pd.DataFrame(torn).sort_values("swing", ascending=False).to_csv(OUTPUTS / "tornado.csv", index=False)

    # ---- KPI dashboard
    k = m.loc[ids, ["short_name", "rank_candidates", "total_score", "A_size_wealth", "B_basketball_demand", "C_corporate",
                    "D_competition_infra", "population", "median_hh_income", "pop_growth_2020_2025",
                    "large_est_per_100k", "big4_other_leagues", "arena_ready", "largest_arena_no_nba_tenant"]].copy()
    k["top10_frequency"] = sens.loc[ids, "top10_frequency"]
    k["fan_interest_index"] = k["B_basketball_demand"]  # Pillar B score (Google Trends unavailable)
    k["arena_ready"] = np.where(k["arena_ready"] == 1, "Y", "N")
    for s in SCEN:
        k[f"est_local_revenue_{s}"] = rev[s]["total"]
    k["local_revenue_per_capita_base"] = k["est_local_revenue_base"] / k["population"]
    k = k.rename(columns={"rank_candidates": "attractiveness_rank", "big4_other_leagues": "competing_teams"})
    k.sort_values("attractiveness_rank").to_csv(OUTPUTS / "kpi_dashboard.csv")
    print(k.sort_values("attractiveness_rank")[["short_name", "attractiveness_rank", "est_local_revenue_low", "est_local_revenue_base", "est_local_revenue_high"]].round(-5).to_string())
    print(pd.DataFrame(out).round(2).to_string())
    print(pd.read_csv(OUTPUTS / "tornado.csv")[["assumption", "swing"]].to_string())


if __name__ == "__main__":
    main()
