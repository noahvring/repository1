"""Phase 4 (generated parts): competitive landscape and insight scaffold.

competitive_landscape.csv lists, for each top-8 candidate, the existing pro teams
(from data/manual/teams.csv), D-I basketball schools (ncaa_school_metro.csv) and
17,000+ seat arenas with tenants (arenas.csv). Every row keeps its source URL.
"""
import pandas as pd
from config import MANUAL, OUTPUTS, PROCESSED, RESEARCH


def main():
    k = pd.read_csv(OUTPUTS / "kpi_dashboard.csv")
    focus = pd.read_csv(OUTPUTS / "focus_markets.csv")
    ids = dict(zip(k["market_id"], k["short_name"]))
    # also cover the scored focus markets (Seattle, Las Vegas, Pittsburgh, Louisville, ...)
    for mid, nm in zip(focus["market_id"], focus["short_name"]):
        if not str(mid).startswith("INTL"):
            ids.setdefault(mid, nm)
    # CBSA -> market (CSA or CBSA) lookup written by build_metros.py
    cmap = pd.read_csv(PROCESSED / "cbsa_factors.csv", dtype={"cbsa_code": str}).set_index("cbsa_code")["market_id"]
    teams = pd.read_csv(MANUAL / "teams.csv", dtype=str)
    arenas = pd.read_csv(MANUAL / "arenas.csv", dtype={"cbsa_code": str})
    ncaa = pd.read_csv(PROCESSED / "ncaa_school_metro.csv", dtype={"cbsa_code": str})
    for t in (teams, arenas, ncaa):
        t["market_id"] = t["cbsa_code"].map(cmap)
    rows = []
    for cid, name in ids.items():
        for _, t in teams[teams.market_id == cid].iterrows():
            rows.append({"market_id": cid, "metro": name, "type": "pro team", "league": t.league, "name": t.team,
                         "detail": t.location, "pillar_d_link": "competition count" if t.league in ("NFL", "MLB", "NHL") else "demand (Pillar B)" if t.league in ("WNBA", "G League") else "",
                         "source_url": t.source_url})
        for _, s in ncaa[ncaa.market_id == cid].iterrows():
            rows.append({"market_id": cid, "metro": name, "type": "college (NCAA D-I men's basketball)", "league": "NCAA D-I",
                         "name": s.school, "detail": f"2025-26 home attendance {int(s.attendance):,}", "pillar_d_link": "demand (Pillar B)",
                         "source_url": "https://s3.amazonaws.com/fs.ncaa.org/Docs/stats/m_basketball_RB/Attend.pdf"})
        for _, a in arenas[arenas.market_id == cid].iterrows():
            rows.append({"market_id": cid, "metro": name, "type": "arena 17,000+", "league": "", "name": a.arena,
                         "detail": f"capacity {a.capacity_basketball:,}; tenants: {a.tenants}; opened {a.opened}",
                         "pillar_d_link": "arena-ready" if not a.nba_tenant else "NBA tenant", "source_url": a.source_url})
    rows.append({"market_id": "", "metro": "all", "type": "other leagues' bids", "league": "", "name": "not compiled",
                 "detail": "Bids by other leagues for these metros were not researched in this build", "pillar_d_link": "", "source_url": "NOT SOURCED"})
    intl = pd.read_csv(MANUAL / "international_markets.csv")
    for _, r in intl.iterrows():
        rows.append({"market_id": "INTL-" + r.market, "metro": r.market, "type": "international market fact", "league": "",
                     "name": r["item"], "detail": f"{r.value} ({r.unit})", "pillar_d_link": "not scored", "source_url": r.source_url})
    pd.DataFrame(rows).to_csv(RESEARCH / "competitive_landscape.csv", index=False)

    themes = [
        ("Las Vegas vs Seattle: league focus vs scorecard", "research/trends.csv (ESPN 2026-10-02 rows); outputs/focus_markets.csv (Seattle, Las Vegas)"),
        ("markets outside U.S. data (Mexico City, Vancouver)", "data/manual/international_markets.csv; research/focus_markets.md"),
        ("bidder competition: Las Vegas vs Seattle", "research/bidder_landscape.csv; outputs/bidder_multiples.csv"),
        ("realignment travel: who moves East", "outputs/realignment_travel.csv"),
        ("arena readiness", "outputs/kpi_dashboard.csv (arena_ready, largest_arena_no_nba_tenant); data/manual/arenas.csv"),
        ("corporate base", "outputs/pillar_scores.csv (C_corporate); data/processed/metros.csv (large_establishments_500plus, large_est_per_100k)"),
        ("fan interest without a team", "outputs/pillar_scores.csv (B_basketball_demand); data/processed/ncaa_school_metro.csv"),
        ("dilution vs fee", "outputs/owner_npv.csv (npv_net_of_fee); outputs/owner_breakeven_growth.csv"),
        ("scores driven by one pillar (e.g. Omaha, Raleigh)", "outputs/rankings.csv (top_pillar, top_pillar_share_of_positive)"),
        ("market size and growth", "outputs/pillar_scores.csv (A_size_wealth, z_pop_growth_2020_2025)"),
        ("crowded vs open markets", "data/processed/metros.csv (big4_other_leagues); research/competitive_landscape.csv"),
        ("robustness of rankings", "outputs/sensitivity.csv (top10_frequency, best_rank, worst_rank)"),
        ("scorecard validity", "outputs/validity.csv (diff_nba_minus_non, ci95_low, ci95_high, point_biserial_r)"),
        ("revenue assumptions drive the case", "outputs/tornado.csv (swing); data/manual/assumptions.csv"),
        ("expansion fee inflation across leagues", "research/trends.csv (nhl_expansion, mls_expansion, wnba_expansion rows)"),
    ]
    pd.DataFrame([{"theme": t, "supporting_evidence": e, "implication": "", "confidence": ""} for t, e in themes]).to_csv(RESEARCH / "insights.csv", index=False)
    print("competitive_landscape rows:", len(rows))


if __name__ == "__main__":
    main()
