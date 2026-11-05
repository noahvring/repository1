"""Write README, KEY_NUMBERS, FINAL_REPORT and the memo templates. Every number is read from outputs/."""
import pandas as pd
from config import OUTPUTS, PROCESSED, ROOT, MANUAL, ACCESS_DATE, RESEARCH
import business_case as bc


def md(df, floatfmt=2):
    """Small DataFrame -> markdown table (no extra dependency)."""
    df = df.copy()
    for c in df.columns:
        if df[c].dtype.kind == "f":
            df[c] = df[c].map(lambda v: "" if pd.isna(v) else f"{v:,.{floatfmt}f}")
    df = df.astype(object).where(df.notna(), "")
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    lines += ["| " + " | ".join(map(str, r)) + " |" for r in df.values]
    return "\n".join(lines)


def money(v):
    return f"${v/1e9:,.2f}B" if abs(v) >= 1e9 else f"${v/1e6:,.1f}M"


def load():
    r = pd.read_csv(OUTPUTS / "rankings.csv", dtype={"market_id": str})
    return dict(r=r, m=pd.read_csv(PROCESSED / "metros.csv", dtype={"market_id": str}),
                k=pd.read_csv(OUTPUTS / "kpi_dashboard.csv", dtype={"market_id": str}).sort_values("attractiveness_rank"),
                v=pd.read_csv(OUTPUTS / "validity.csv"), s=pd.read_csv(OUTPUTS / "sensitivity.csv"),
                npv=pd.read_csv(OUTPUTS / "owner_npv.csv"), beg=pd.read_csv(OUTPUTS / "owner_breakeven_growth.csv"),
                focus=pd.read_csv(OUTPUTS / "focus_markets.csv"), chg=pd.read_csv(OUTPUTS / "top10_change.csv"),
                cal=pd.read_csv(OUTPUTS / "business_case_calibration.csv"), cov=pd.read_csv(OUTPUTS / "coverage.csv"),
                pm=pd.read_csv(OUTPUTS / "partial_markets.csv"),
                mc=pd.read_csv(OUTPUTS / "monte_carlo.csv"), fb=pd.read_csv(OUTPUTS / "fan_behavior.csv"),
                cvp=pd.read_csv(OUTPUTS / "college_vs_pro.csv"), bid=pd.read_csv(OUTPUTS / "bidder_multiples.csv"),
                t=pd.read_csv(OUTPUTS / "tornado.csv"))


def npv_base(D):
    """Owner NPV grid for the base case: base fee, all central revenue, gross."""
    n = D["npv"]
    return n[(n.pool_definition == "all_central_revenue") & (n.owner_share == "gross") & (n.fee_scenario == "base")]


def npv_cell(D):
    """Headline NPV cell: base case at 3% growth and 8% discount."""
    nb = npv_base(D)
    return nb[(nb.media_growth == 0.03) & (nb.discount_rate == 0.08)].iloc[0]


def key_numbers(D):
    r, v, k, n, beg = D["r"], D["v"], D["k"], D["npv"], D["beg"]
    A = pd.read_csv(MANUAL / "assumptions.csv").set_index("assumption")
    med = r["median_nba_score"].iloc[0]
    rank = lambda name: int(r.loc[r.short_name == name, "rank_candidates"].iloc[0])
    over = r[r["overlooked"]]["short_name"].tolist()
    tot = v[v.measure == "total_score"].iloc[0]
    cell = npv_cell(D)
    worst = n.loc[n["npv_net_of_fee"].idxmin()]
    be = beg[(beg.discount_rate == 0.08) & (beg.fee_scenario == "base")].iloc[0]
    items = [
        ("Markets scored", f"{int((~D['m']['partial_data']).sum())} (+ San Juan and Mexico City as partial-data rows)", "U.S. markets = Census combined statistical areas (CSA), or the metro (CBSA) if not in a CSA; 1M+ people, plus every NBA market and markets named in coverage", "-", "data/processed/metros.csv (row count)"),
        ("Current U.S. NBA markets in benchmark", f"{int(r['nba_metro'].sum())}", "29 U.S. teams in 27 markets (LA and NY have two); Toronto excluded", "-", "outputs/nba_benchmark.csv"),
        ("Median current-NBA-market score", f"{med:.2f}", "Score of the middle current NBA market; the 'overlooked' bar", "equal weights", "outputs/rankings.csv (median_nba_score)"),
        ("Seattle rank among non-NBA markets", f"#{rank('Seattle')}", "Position in the equal-weight ranking", "equal weights", "outputs/rankings.csv (short_name=Seattle)"),
        ("Las Vegas rank among non-NBA markets", f"#{rank('Las Vegas')}", "As above", "equal weights", "outputs/rankings.csv (short_name=Las Vegas)"),
        ("Overlooked markets", f"{len(over)} ({', '.join(over)})", "Non-NBA markets scoring at or above the median current NBA market", "equal weights", "outputs/rankings.csv (overlooked=True)"),
        ("NBA vs non-NBA total-score gap", f"{tot.diff_nba_minus_non:.2f}", "Current NBA markets score higher on average than non-NBA markets (association, not prediction)", f"95% CI {tot.ci95_low:.2f} to {tot.ci95_high:.2f}; point-biserial r = {tot.point_biserial_r:.2f}", "outputs/validity.csv (measure=total_score)"),
        ("National TV payout per team, 2025-26", money(A.at["national_tv_per_team_2025_26_usd", "base"]), "Each team's share of the national media deal (reported)", "reported", "data/manual/assumptions.csv (national_tv_per_team_2025_26_usd)"),
        ("Shared (central) revenue pool, 2025-26", money(A.at["central_revenue_share", "base"] * A.at["team_revenue_2025_26_usd", "base"]), "41% of $13.7B team revenue is league-shared (media, league sponsorship, international, retail)", "reported", "data/manual/assumptions.csv (central_revenue_share x team_revenue_2025_26_usd)"),
        ("Fee share per existing team (base)", money(cell.fee_share_per_existing_team), "One-time payment: fee x 2 new teams / 30 owners (base fee = midpoint of reported $7-10B)", "low $7B / high $10B fee: " + f"{money(7e9*2/30)} / {money(10e9*2/30)}", "outputs/owner_npv.csv (fee_scenario=base)"),
        ("Dilution per existing team, first expansion season", money(cell.dilution_first_season), "Shared revenue each existing team gives up per year when 30 shares become 32", "3% growth from 2025-26", "outputs/owner_npv.csv (all_central_revenue, gross, g=3%, r=8%, base)"),
        ("20-year NPV of dilution (base)", money(cell.npv_dilution_20y), "Present value of 20 years of lost shared revenue per team", "3% growth, 8% discount", "outputs/owner_npv.csv (all_central_revenue, gross, g=3%, r=8%, base)"),
        ("Fee share minus NPV of dilution (base)", money(cell.npv_net_of_fee), "Positive = the one-time fee is worth more to an existing owner than 20 years of dilution", "3% growth, 8% discount", "outputs/owner_npv.csv (same row)"),
        ("Fee share minus NPV of dilution, least favourable cell", money(worst.npv_net_of_fee), "Lowest value across all 108 scenario cells (pool, owner share, growth, discount, fee)", f"{worst.pool_definition}, {worst.owner_share}, g={worst.media_growth:.0%}, r={worst.discount_rate:.0%}, fee={worst.fee_scenario}", "outputs/owner_npv.csv (min npv_net_of_fee)"),
        ("Share of scenario cells where fee covers dilution", f"{n['fee_covers_dilution'].mean():.0%}", "Across all 108 cells", "scenario grid", "outputs/owner_npv.csv (fee_covers_dilution)"),
        ("Break-even growth in shared revenue", f"{be.breakeven_growth:.1%} per year", "Growth needed for 20-year NPV of dilution to equal the fee share; reported payout growth is ~7%/yr", "8% discount, base fee, all central revenue", "outputs/owner_breakeven_growth.csv (r=0.08, base)"),
        ("Revenue elasticity calibration", f"{D['cal'].implied_elasticity.iloc[0]:.2f}", "ln(Warriors/Grizzlies revenue) / ln(their market population ratio); basis for the 0.5 base elasticity", "one pair of teams", "outputs/business_case_calibration.csv"),
    ]
    for _, row in k.iterrows():
        items.append((f"Est. local revenue, {row.short_name}", f"{money(row.est_local_revenue_low)} / {money(row.est_local_revenue_base)} / {money(row.est_local_revenue_high)}",
                      "Gate + sponsorship + local media + other, per year, 2025-26 dollars", "min / base / max across elasticity scenarios", f"outputs/kpi_dashboard.csv (short_name={row.short_name})"))
    for _, row in D["focus"].iterrows():
        if row.scored == "Y" and row.nba_metro != True:
            items.append((f"Focus market rank: {row.focus_label}", f"#{int(row.attractiveness_rank)}", "Rank among non-NBA markets", "equal weights", f"outputs/focus_markets.csv (focus_label={row.focus_label})"))
        elif row.scored != "Y":
            items.append((f"Focus market: {row.focus_label}", f"population {row.population/1e6:.1f}M; not scored", "Outside U.S. data; descriptive facts only", "-", f"data/manual/international_markets.csv (market={row.focus_label})"))
    mc, fb, cvp, bid = D["mc"], D["fb"].set_index("short_name"), D["cvp"].iloc[0], D["bid"]
    for _, row in mc.head(5).iterrows():
        q = r.loc[r.short_name == row.short_name, "quadrant"].iloc[0]
        items.append((f"Monte Carlo: {row.short_name}", f"P(top 10) {row.p_top10:.0%}; P(top 5) {row.p_top5:.0%}; median rank #{row.median_rank:.0f} (90%: #{row.rank_p05:.0f}-#{row.rank_p95:.0f}); quadrant: {q}",
                      "Share of 10,000 random pillar weightings in which the market ranks top 10 / top 5", "Dirichlet(1,1,1), seed 42", f"outputs/monte_carlo.csv (short_name={row.short_name})"))
    for nm in ["Seattle", "Las Vegas"]:
        row = mc[mc.short_name == nm].iloc[0]
        items.append((f"Monte Carlo: {nm}", f"P(top 10) {row.p_top10:.0%}; median rank #{row.median_rank:.0f}", "As above", "Dirichlet(1,1,1), seed 42", f"outputs/monte_carlo.csv (short_name={nm})"))
    prime = r[(~r["nba_metro"]) & (r["quadrant"] == "Prime targets")]["short_name"].tolist()
    items.append(("Prime-target markets", f"{len(prime)} ({', '.join(prime)})", "Non-NBA markets above the NBA median on both attractiveness and ease of entry", "medians of current NBA markets", "outputs/rankings.csv (quadrant)"))
    for nm in ["Raleigh", "Seattle", "Las Vegas"]:
        mi = r.loc[r.short_name == nm, "miles_to_nearest_nba"].iloc[0]
        items.append((f"Miles to nearest NBA market: {nm}", f"{mi:.0f}", "Straight-line distance between market internal points (cannibalization proxy)", "-", f"outputs/rankings.csv (short_name={nm})"))
    for nm in ["Las Vegas", "Seattle"]:
        items.append((f"Transplant share: {nm}", f"{fb.at[nm, 'transplant_share']:.0%}", "Residents born outside their current state (divided-loyalty risk; not scored)",
                      f"{fb.at[nm, 'transplant_share_vs_nba_median']:+.0%} vs median NBA market", f"outputs/fan_behavior.csv (short_name={nm})"))
    items.append(("College attendance vs pro attractiveness (NBA markets)", f"r = {cvp.pearson_r_college_att_vs_score_without_college:.2f} (p = {cvp.p_value:.2f})",
                  "Correlation between college attendance per capita and the score without college, across 27 NBA markets (association only)", "-", "outputs/college_vs_pro.csv"))
    items.append(("Top-10 overlap without college attendance", f"{int(cvp.top10_overlap_equal_vs_no_college)} of 10",
                  f"Dropped: {cvp.dropped_from_top10_without_college}; added: {cvp.added_to_top10_without_college}", "no_college weighting", "outputs/college_vs_pro.csv"))
    lg = bid["league_avg_value_to_revenue"].iloc[0]
    items.append(("Bidder-view prices", "Las Vegas ~$10B (reported expected sale price from active bidding); Seattle ~$6B (sources' valuation estimate, not a bid); others: $8.5B assumed fee", "Price inputs for the multiples; the three price types are not strictly comparable", "reported / estimate / assumption", "outputs/bidder_multiples.csv (price_type, price_basis)"))
    items.append(("League-average franchise value / revenue", f"{lg:.1f}x", "Average franchise value $6.64B / $456M average team revenue (Sportico)", "reported", "outputs/bidder_multiples.csv (league_avg_value_to_revenue)"))
    for _, row in bid.iterrows():
        items.append((f"Price / est. revenue: {row.short_name}", f"{row.price_to_revenue_base:.1f}x ({row.price_to_revenue_range})", f"{row.price_basis}; revenue = local estimate + 1/32 of central revenue",
                      f"{row.premium_vs_league_avg_multiple:+.0%} vs league-average multiple", f"outputs/bidder_multiples.csv (short_name={row.short_name})"))
    for _, row in D["pm"].iterrows():
        items.append((f"Partial-data market: {row.short_name}", f"score {row.total_score:.2f} (would rank #{int(row.rank_if_included)} if included); ease {row.ease_of_entry:.2f}; quadrant {row.quadrant}; {row.miles_to_nearest_nba:,.0f} miles to nearest NBA market",
                      "Scored only on factors with a comparable source; not in rankings or Monte Carlo", f"factors used: {row.factors_used}", f"outputs/partial_markets.csv (short_name={row.short_name})"))
    rt = pd.read_csv(OUTPUTS / "realignment_travel.csv")
    cur = rt[rt.option == "Current 30 teams"].iloc[0]
    items.append(("Avg conference travel per team, current 30 teams", f"{cur.avg_miles_per_team:,.0f} miles", "Proxy: one round trip to each conference opponent, straight-line", "simplified proxy", "outputs/realignment_travel.csv (Current 30 teams)"))
    for _, row in rt[rt.moved_team.notna() & (rt.moved_team != "")].iterrows():
        items.append((f"Realignment: {row.moved_team} move East", f"league avg {row.avg_miles_per_team:,.0f} mi/team; mover {row.moved_team_miles:,.0f} mi (vs {row.moved_team_miles_if_stayed_west:,.0f} if it stayed West)",
                      "32 teams, Seattle and Las Vegas in the West", "simplified proxy", f"outputs/realignment_travel.csv ({row.option})"))
    hm = pd.read_csv(MANUAL / "expansion_attendance_wiki.csv")
    for team, g in hm.groupby("team"):
        items.append((f"Honeymoon: {team}", f"min index {g.index_vs_season1.min():.0f}, last season index {g.sort_values('season_number').index_vs_season1.iloc[-1]:.0f} (season 1 = 100; {len(g)} seasons)",
                      "Average home attendance relative to the first season; capped by arena capacity, so sellouts show as flat lines", "Wikipedia game logs", f"data/manual/expansion_attendance_wiki.csv (team={team})"))
    bl = pd.read_csv(RESEARCH / "bidder_landscape.csv")
    items.append(("Reported bidding groups", "; ".join(f"{mk}: {n}" for mk, n in bl.groupby("market").size().items()), "Groups named or reported per market (incl. unidentified)", "reported", "research/bidder_landscape.csv"))
    top = D["t"].iloc[0]
    items.append(("Most influential revenue assumption", f"{top.assumption} (swing {money(top.swing)})", "Moves combined top-8 base local revenue the most", "tornado", "outputs/tornado.csv (row 1)"))
    t = pd.DataFrame(items, columns=["Number", "Value", "Plain-English meaning", "Scenario / CI", "Source file and row"])
    (OUTPUTS / "KEY_NUMBERS.md").write_text("# Key numbers\n\nGenerated by `src/report.py` from `outputs/`. Do not edit by hand.\n\n" + md(t) + "\n")
    return items


def focus_md(D):
    f = D["focus"]
    intl = pd.read_csv(MANUAL / "international_markets.csv")
    sc = f[f.scored == "Y"][["focus_label", "short_name", "market_title", "attractiveness_rank", "total_score", "top10_frequency", "arena_ready",
                             "largest_arena_no_nba_tenant", "competing_teams", "est_local_revenue_base", "nba_metro"]].copy()
    sc["est_local_revenue_base"] = sc["est_local_revenue_base"].map(money)
    txt = "# Focus markets\n\nGenerated by `src/report.py`. These are the league's reported front-runners (Seattle, Las Vegas), Mexico City, and markets often named in coverage. Scores come from `outputs/focus_markets.csv`. Baltimore is part of the Washington-Baltimore CSA, an existing NBA market.\n\n"
    txt += "## Scored U.S. markets\n\n" + md(sc) + "\n\n"
    txt += "## Markets outside the U.S. data (not scored)\n\n" + md(intl[["market", "item", "value", "unit", "source_url", "note"]].fillna("")) + "\n\n"
    txt += "Reported league focus is in `research/trends.csv` (ESPN, 2026-10-02: Las Vegas ahead of Seattle; Seattle in a holding pattern).\n\n"
    for name in ["Seattle", "Las Vegas", "Mexico City"]:
        txt += f"## {name}\n\n### What this suggests\n\n"
    txt += "## Markets the league may be overlooking\n\n### What this suggests\n"
    (RESEARCH / "focus_markets.md").write_text(txt)


def readme(D):
    r, k, v, s, cov, chg, focus = D["r"], D["k"], D["v"], D["s"], D["cov"], D["chg"], D["focus"]
    med = r["median_nba_score"].iloc[0]
    rank = lambda n: int(r.loc[r.short_name == n, "rank_candidates"].iloc[0])
    nb = npv_base(D)
    cell = npv_cell(D)
    be = D["beg"][(D["beg"].discount_rate == 0.08) & (D["beg"].fee_scenario == "base")].iloc[0]
    top15 = r[~r["nba_metro"]].head(15)[["rank_candidates", "short_name", "market_title", "total_score", "A_size_wealth", "B_basketball_demand", "C_corporate", "ease_of_entry", "quadrant", "overlooked", "top_pillar"]].copy()
    top15["rank_candidates"] = top15["rank_candidates"].astype(int)
    sens = s.head(15)[["short_name"] + [c for c in s.columns if c.startswith("rank_")] + ["top10_frequency"]]
    kp = k[["short_name", "attractiveness_rank", "top10_frequency", "population", "median_hh_income", "competing_teams", "arena_ready",
            "est_local_revenue_low", "est_local_revenue_base", "est_local_revenue_high", "local_revenue_per_capita_base"]].copy()
    for c in ["est_local_revenue_low", "est_local_revenue_base", "est_local_revenue_high"]:
        kp[c] = kp[c].map(money)
    kp["population"] = kp["population"].map(lambda x: f"{x/1e6:.2f}M")
    piv = nb.pivot(index="media_growth", columns="discount_rate", values="npv_net_of_fee")
    grid = pd.DataFrame({"growth / discount": [f"{g:.0%}" for g in piv.index]})
    for c in piv.columns:
        grid[f"{c:.0%}"] = [money(x) for x in piv[c]]
    pools = D["npv"].groupby(["pool_definition", "owner_share"])["npv_net_of_fee"].agg(["min", "max"]).reset_index()
    pools["min"] = pools["min"].map(money); pools["max"] = pools["max"].map(money)
    covt = cov.copy(); covt["share_with_data"] = (covt["share_with_data"] * 100).round(0).astype(int).astype(str) + "%"
    ch = chg.copy()
    for c in ["rank_final_csa_no_gleague", "rank_v1_cbsa_with_gleague", "rank_csa_with_gleague"]:
        ch[c] = ch[c].map(lambda x: "" if pd.isna(x) else f"#{int(x)}")
    fo = focus[["focus_label", "scored", "attractiveness_rank", "total_score", "arena_ready", "population"]].copy()
    fo["attractiveness_rank"] = fo["attractiveness_rank"].map(lambda x: "" if pd.isna(x) else f"#{int(x)}")
    fo["population"] = fo["population"].map(lambda x: f"{x/1e6:.1f}M")
    fo.loc[focus["nba_metro"] == True, "attractiveness_rank"] = "(existing NBA market)"
    mc = D["mc"].set_index("short_name")
    mc_s, mc_v = mc.at["Seattle", "p_top10"], mc.at["Las Vegas", "p_top10"]
    prime = r[(~r["nba_metro"]) & (r["quadrant"] == "Prime targets")]["short_name"].tolist()
    mct = D["mc"].head(15)[["short_name", "p_top5", "p_top10", "median_rank", "rank_p05", "rank_p95"]].copy()
    for c in ["p_top5", "p_top10"]:
        mct[c] = mct[c].map(lambda x: f"{x:.0%}")
    quad = r[~r["nba_metro"]].groupby("quadrant")["short_name"].apply(lambda x: ", ".join(x)).reset_index()
    fbt = D["fb"].head(12)[["short_name", "transplant_share", "transplant_share_vs_nba_median", "ncaa_att_per_1k", "rank_equal", "rank_no_college"]].copy()
    fbt["transplant_share"] = fbt["transplant_share"].map(lambda x: f"{x:.0%}"); fbt["transplant_share_vs_nba_median"] = fbt["transplant_share_vs_nba_median"].map(lambda x: f"{x:+.0%}")
    cvp = D["cvp"].iloc[0]
    bid = D["bid"][["short_name", "price_type", "price_to_revenue_base", "price_to_revenue_range", "league_avg_value_to_revenue", "premium_vs_league_avg_multiple"]].copy()
    bid["premium_vs_league_avg_multiple"] = bid["premium_vs_league_avg_multiple"].map(lambda x: f"{x:+.0%}")
    pmt = D["pm"][["short_name", "market_type", "total_score", "A_size_wealth", "B_basketball_demand", "C_corporate", "ease_of_entry", "quadrant", "rank_if_included", "miles_to_nearest_nba", "factors_used"]].copy()
    pmt["C_corporate"] = pmt["C_corporate"].map(lambda x: "no data" if pd.isna(x) else f"{x:.2f}")
    pmt["short_name"] = pmt["short_name"] + " (partial data)"
    rt = pd.read_csv(OUTPUTS / "realignment_travel.csv")
    rtt = rt[["option", "teams_east", "teams_west", "avg_miles_per_team", "east_avg_per_team", "west_avg_per_team", "moved_team", "moved_team_miles", "moved_team_miles_if_stayed_west"]].copy()
    for c in ["avg_miles_per_team", "east_avg_per_team", "west_avg_per_team", "moved_team_miles", "moved_team_miles_if_stayed_west"]:
        rtt[c] = rtt[c].map(lambda x: "" if pd.isna(x) else f"{x:,.0f}")
    srcs = pd.DataFrame([
        ("Population, households, income, age 18-44", "Census ACS 5-year summary file (www2.census.gov)", "2020-2024"),
        ("Population growth", "Census Population Estimates, Vintage 2025", "2020-2025"),
        ("GDP", "BEA CAGDP1 county GDP summed to market", "2024"),
        ("Large establishments (500+ employees)", "Census County Business Patterns (metro/micro file)", "2023"),
        ("NCAA D-I men's basketball home attendance", "NCAA attendance records PDF", "2025-26"),
        ("NBA/NFL/MLB/NHL/MLS/WNBA/G League teams", "Wikipedia league articles (current teams tables)", f"accessed {ACCESS_DATE}"),
        ("Arenas 17,000+ seats", "Wikipedia: List of indoor arenas in the United States", f"accessed {ACCESS_DATE}"),
        ("Market definitions", "Census CBSA/CSA delineation files", "July 2023"),
        ("Team revenue by stream, central revenue share, national TV per team", "Sportico team-finance reporting", "2025-26"),
        ("Mexico City, Vancouver, Toronto facts", "Wikipedia (population, arena, history, coordinates)", f"accessed {ACCESS_DATE}"),
        ("Market locations", "Census Gazetteer 2024 (CBSA internal points)", "2024"),
        ("Place of birth (transplant share)", "Census ACS 5-year table B05002", "2020-2024"),
        ("Expansion-team attendance (honeymoon)", "Wikipedia season articles (game logs); ESPN NBA attendance (partial)", "1995-2026"),
        ("NBA arena coordinates, conferences", "Wikipedia NBA current-teams table", f"accessed {ACCESS_DATE}"),
        ("Bidder landscape", "ESPN (2026-10-02)", "2026"),
        ("Franchise value, team revenue; Las Vegas price", "Sportico; ESPN (2026-10-02)", "2025-26"),
        ("Google Trends; NTTO overseas visitors", "Skipped (see DEVIATIONS.md)", "-"),
    ], columns=["Factor", "Source", "Year"])
    txt = f"""# Beyond Seattle and Vegas: NBA Expansion Market Strategy

## At a glance

- **Question:** Which North American markets are most attractive for an NBA team, which are overlooked, and does expansion pay off for existing owners?
- **Data scope:** {int((~D['m']['partial_data']).sum())} U.S. markets, plus San Juan and Mexico City as partial-data rows. A market is a Census combined statistical area (CSA), so San Jose sits inside the Bay Area and Baltimore inside Washington-Baltimore. Public data only. Mexico City and San Juan get partial scores; Vancouver is profiled only.
- **Key numbers:**
  - Seattle ranks **#{rank('Seattle')}** and Las Vegas **#{rank('Las Vegas')}** among {int((~r['nba_metro']).sum())} non-NBA markets.
  - **{int(r['overlooked'].sum())}** non-NBA markets score at or above the median current NBA market ({med:.2f}): {', '.join(r[r['overlooked']]['short_name'])}.
  - Each existing owner's fee share (base) is **{money(cell.fee_share_per_existing_team)}**, compared with a 20-year NPV of shared-revenue dilution of **{money(cell.npv_dilution_20y)}** (3% growth, 8% discount).
  - Shared revenue would need to grow **{be.breakeven_growth:.0%} a year** before dilution outweighs the fee. Reported payout growth is about 7% a year.
  - Across 10,000 random pillar weightings, Seattle and Las Vegas land in the top 10 **{mc_s:.0%}** and **{mc_v:.0%}** of the time. Prime targets: **{', '.join(prime)}**.

![Attractiveness vs ease of entry](figures/00_matrix_attractiveness_vs_ease.png)

## Approach

Markets are placed on two separate axes, **attractiveness** and **ease of entry**, and the matrix splits them at the median current NBA market. Attractiveness has three pillars (A-C below). Every factor is converted to a z-score across the {int((~D['m']['partial_data']).sum())} complete U.S. markets; population, GDP and large-establishment counts are logged first. Factors are averaged with equal weights inside each pillar, and the three pillars are averaged with equal weights into the attractiveness score. Current NBA markets are scored the same way and serve as the benchmark. CBSA data are aggregated to markets: counts and populations are summed, income is population-weighted, and the 18-44 share is recomputed from counts.

1. **A. Market size and wealth:** population, median household income, share of residents aged 18-44, population growth 2020-25, and GDP.
2. **B. Basketball demand:** NCAA D-I men's home attendance per 1,000 residents, and WNBA presence. G League presence is shown but not scored, because G League teams are mostly NBA-owned affiliates.
3. **C. Corporate money:** establishments with 500+ employees, as a total and per 100k residents.
**Ease of entry** (separate axis, so nothing is double-counted) combines:
- an available arena (17,000+ seats without an NBA tenant);
- the log of straight-line miles to the nearest other NBA market, a proxy for cannibalizing existing teams' fans;
- NFL, MLB and NHL teams, counted as a negative.

**Robustness:** 10,000 random pillar weightings drawn from a Dirichlet(1,1,1) distribution (seed 42) give each market's probability of a top-5 or top-10 rank, its median rank and a 90% interval (`outputs/monte_carlo.csv`).

## Data & sources

{md(srcs)}

**Coverage** (`outputs/coverage.csv`):

{md(covt)}

## Results

**Matrix quadrants, non-NBA markets** (`outputs/rankings.csv`):

{md(quad)}

**Monte Carlo robustness**, top 15 by P(top 10):

{md(mct, 0)}

![Monte Carlo](figures/09_monte_carlo_robustness.png)

**Top 15 non-NBA markets** (equal weights; `outputs/rankings.csv`):

{md(top15)}

![Top 15](figures/01_headline_top15.png)

**How the top 10 changed from v1.** v1 ranked CBSAs and scored G League presence. The middle column shows the switch to CSAs with G League still scored. The final-rank column is the current v3 model, which also moves competition and arena onto the ease-of-entry axis (`outputs/top10_change.csv`). Omaha was below 1M people as a CBSA, so it was not in the v1 study set.

{md(ch)}

**Does the scorecard recognize existing NBA markets?** Difference in means, NBA minus non-NBA, with Welch 95% CI (`outputs/validity.csv`). This is an association check, not a prediction:

{md(v[['measure','mean_nba','mean_non_nba','diff_nba_minus_non','ci95_low','ci95_high','point_biserial_r','p_value']])}

**Sensitivity:** rank under six weightings (`outputs/sensitivity.csv`). A blank in the arena column means the market is not arena-ready.

{md(sens, 0)}

![Sensitivity](figures/03_sensitivity_heatmap.png)
![Pillars](figures/02_pillar_breakdown_top8.png)
![Scatter](figures/04_population_vs_income.png)

## International options: Mexico City & San Juan (partial data)

These markets are scored **only on the factors that have a comparable source**, standardized against the U.S. markets. Each pillar averages the factors it has, and the total averages the pillars it has. They sit outside the U.S. rankings and the Monte Carlo; "would rank" shows where the score would fall (`outputs/partial_markets.csv`). Sources and conversions are in `data/manual/international_markets.csv` and DEVIATIONS.md.

{md(pmt)}

## Fan behavior & market risk

These are behavioral indicators. They are reported, not scored (`outputs/fan_behavior.csv`, `outputs/college_vs_pro.csv`).

- **Transplant share** is the share of residents born outside their current state. Transplants often keep loyalty to the teams they grew up with, so this is a divided-loyalty risk; its sign is ambiguous.
- **College vs pro:** across the 27 NBA markets, the correlation between college attendance per capita and the attractiveness score without college is r = {cvp.pearson_r_college_att_vs_score_without_college:.2f} (p = {cvp.p_value:.2f}). With college attendance removed, {int(cvp.top10_overlap_equal_vs_no_college)} of the top 10 stay. Dropped: {cvp.dropped_from_top10_without_college}. Added: {cvp.added_to_top10_without_college}.
- **Honeymoon curve:** average home attendance indexed to the first season, from Wikipedia season game logs (`data/manual/expansion_attendance_wiki.csv`). Three teams: Golden Knights, Kraken and Raptors. The Raptors changed arenas mid-1998-99 (SkyDome to Air Canada Centre), so their curve mixes novelty and venue effects. **Sellout cap:** attendance can't exceed capacity. The flat Golden Knights and Kraken lines (index ≈ 100) show sold-out arenas, not evidence that demand stayed flat; any demand above capacity is invisible here.

![Honeymoon](figures/12_honeymoon_curve.png)

{md(fbt, 1)}

## Operations: realignment

Adding Seattle and Las Vegas to the West means one Western team must move East for 16-16 conferences. The proxy assumes each team makes one round trip to every conference opponent, in straight-line miles. It ignores real schedules, inter-conference games, chained road trips and back-to-backs (`outputs/realignment_travel.csv`).

{md(rtt)}

![Realignment](figures/10_realignment_travel.png)

## Seattle vs Las Vegas

See the full side-by-side in [`memo/HEAD_TO_HEAD.md`](memo/HEAD_TO_HEAD.md) and the reported bidding groups in [`research/bidder_landscape.csv`](research/bidder_landscape.csv).

![Head-to-head](figures/11_seattle_vs_las_vegas.png)

## Focus markets

These are the reported front-runners (Seattle, Las Vegas), Mexico City, and markets often named in coverage (`outputs/focus_markets.csv`, `research/focus_markets.md`).

{md(fo)}

![Focus](figures/08_focus_markets.png)

## Business case

Local revenue starts from the average NBA team's reported revenue by stream (Sportico, 2025-26). Each stream is scaled by how the market compares with the median NBA market, using a labeled elasticity assumption. Min and max are taken across the elasticity scenarios.

{md(kp)}

![KPI](figures/05_kpi_dashboard.png)
![Tornado](figures/06_tornado.png)

**Owner economics: fee share minus 20-year NPV of dilution** (base fee, all central revenue, gross; `outputs/owner_npv.csv`):

{md(grid)}

Range of fee share minus NPV by pool definition and owner share (all growth, discount and fee scenarios):

{md(pools)}

![Owner NPV](figures/07_owner_npv_heatmap.png)

**Bidder view: price / estimated revenue vs league average** (`outputs/bidder_multiples.csv`). Revenue = estimated local revenue + 1/32 of central revenue:

Price types differ: Las Vegas is a reported expected sale price, Seattle a valuation estimate, the rest an assumed fee. They are not strictly comparable (see `price_type`).

{md(bid, 1)}

## Market & competitive research

- `research/trends.csv`: dated, sourced facts on the expansion process (including ESPN's 2026-10-02 report that the league is more focused on Las Vegas), fees, the media deal, team revenue, and NHL, WNBA and MLS expansions.
- `research/comparables.md`: Vegas Golden Knights, Seattle Kraken, and recent WNBA expansion teams.
- `research/focus_markets.md`: Seattle, Las Vegas, Mexico City, Vancouver and the markets to watch.
- `research/competitive_landscape.csv`: pro teams, D-I schools and arenas in each top-8 and focus market.
- `research/insights.csv`: themes with linked evidence; implications left for Noah.

## Recommendation

*(Written by Noah.)*

## Limitations & data I'd buy

- **Associations only.** The validity check asks whether the scorecard separates existing NBA markets from the rest. It does not show what causes team success.
- **College basketball per capita can dominate a small market.** Omaha and Raleigh-Durham rank high mostly on Pillar B. See `top_pillar` in `outputs/rankings.csv` and the no-college check above.
- **Distance is a rough proxy for cannibalization.** Ease of entry uses straight-line miles from one point per market, not drive times or TV overlap. Existing teams' fans in a market (e.g. Suns or Lakers fans in Las Vegas) are not measured.
- **Transplant share is inflated where a market crosses state lines** (people born in the neighboring state count as transplants), and it is not scored.
- **Monte Carlo varies only the pillar weights**, not the factor choice or the data.
- **Bidder multiples mix price types that are not strictly comparable.** Las Vegas uses ESPN's reported expected sale price (~$10B, from three competing bids). Seattle uses a sources' valuation estimate (~$6B, with no competing bid yet). Other markets use the $8.5B assumed base fee. Arena costs (except the Las Vegas column) and timing are ignored.
- **Missing data:** Google Trends (folder empty) and NTTO overseas visitors (dashboard only) are not in the scorecard. Mexico City and Vancouver are not scored. Virginia Beach GDP is missing.
- **NCAA mapping:** schools are assigned to markets by main-campus county. Only D-I schools in the study markets are mapped.
- **Business case:** each stream is scaled with an elasticity calibrated on one pair of teams. Dilution assumes expansion teams add no new shared revenue (the media deal is fixed through 2035-36), and years beyond the deal assume renewal.
- **Data I'd buy:** Nielsen TV ratings and DMA viewing households, team-level revenues, ticket prices, sponsorship deals, NBA League Pass and merchandise data.

## Reproduce

```bash
pip install -r requirements.txt
python run_all.py
```

## Tools

Built in Python with the help of Claude Code (AI coding assistant). Research design, assumptions review, interpretation and recommendations are my own.

Libraries: {', '.join(l.split('==')[0] for l in (ROOT / 'requirements.txt').read_text().split())}. Every number in this README is generated by `src/report.py`; my working rules are in [`PROJECT_RULES.md`](PROJECT_RULES.md).
"""
    (ROOT / "README.md").write_text(txt)


def exec_summary(D):
    r, mc, fb = D["r"], D["mc"], D["fb"].set_index("market_id")
    cell = npv_cell(D)
    be = D["beg"][(D["beg"].discount_rate == 0.08) & (D["beg"].fee_scenario == "base")].iloc[0]
    m = D["m"].set_index("market_id")
    prime = r[(~r["nba_metro"]) & (r["quadrant"] == "Prime targets")]["short_name"].tolist()
    rr = r.set_index("market_id")
    top = mc.head(5).set_index("market_id")
    # base local revenue for the top-5 (same model as kpi_dashboard)
    S = bc.load_assumptions()
    mm = m.join(rr[["A_size_wealth", "B_basketball_demand", "C_corporate"]])
    ref = m[m["nba_metro"]][["population", "median_hh_income", "large_establishments_500plus"]].median()
    rev = bc.local_revenue(mm.loc[top.index], ref, S["base"])["total"]
    t = pd.DataFrame({"Market": top["short_name"], "Rank (equal weights)": rr.loc[top.index, "rank_candidates"].astype(int),
                      "P(top 10)": top["p_top10"].map(lambda x: f"{x:.0%}"), "Ease of entry": rr.loc[top.index, "ease_of_entry"].round(2),
                      "Quadrant": rr.loc[top.index, "quadrant"], "Est. local revenue (base)": rev.map(money),
                      "Transplant share": fb.loc[top.index, "transplant_share"].map(lambda x: f"{x:.0%}")})
    txt = f"""# Executive summary

*Template. Headline and recommendation written by Noah. Numbers generated by `src/report.py`.*

## Headline

## Key numbers

1. **Seattle / Las Vegas:** rank #{int(rr[rr.short_name == 'Seattle'].rank_candidates.iloc[0])} / #{int(rr[rr.short_name == 'Las Vegas'].rank_candidates.iloc[0])} among {int((~r.nba_metro).sum())} non-NBA markets. Chance of a top-10 rank across 10,000 random weightings: {mc[mc.short_name == 'Seattle'].p_top10.iloc[0]:.0%} / {mc[mc.short_name == 'Las Vegas'].p_top10.iloc[0]:.0%}.
2. **Prime targets** (above the NBA median on both attractiveness and ease of entry): {len(prime)}, namely {', '.join(prime)}.
3. **Owner economics:** fee share {money(cell.fee_share_per_existing_team)} per existing team vs a 20-year NPV of dilution of {money(cell.npv_dilution_20y)} (3% growth, 8% discount). Shared revenue would need to grow {be.breakeven_growth:.0%} a year before dilution outweighs the fee.
4. **Bidder view** (price types differ): Las Vegas at its reported expected sale price (~$10B) is {D['bid'].set_index('short_name').at['Las Vegas', 'price_to_revenue_base']:.1f}x estimated revenue, and Seattle at a reported valuation estimate (~$6B, not a bid) is {D['bid'].set_index('short_name').at['Seattle', 'price_to_revenue_base']:.1f}x, vs a league-average value/revenue of {D['bid'].league_avg_value_to_revenue.iloc[0]:.1f}x.

![Matrix](../figures/00_matrix_attractiveness_vs_ease.png)

## Top 5 by probability of a top-10 rank

{md(t.reset_index(drop=True))}

## Recommendation
"""
    (ROOT / "memo" / "EXEC_SUMMARY.md").write_text(txt)
    rows = ["League office", "Existing owners", "Players' union (NBPA)", "Host cities & taxpayers", "Bidding groups", "Broadcasters", "Fans"]
    st = pd.DataFrame({"Stakeholder": rows, "What they want": "", "Influence (H/M/L)": "", "Interest (H/M/L)": "", "Implication": ""})
    (ROOT / "memo" / "stakeholders.md").write_text("# Stakeholder grid\n\n*Template for Noah. Evidence: `research/trends.csv`, `outputs/owner_npv.csv`, `outputs/bidder_multiples.csv`.*\n\n" + md(st) + "\n")


def head_to_head(D):
    """memo/HEAD_TO_HEAD.md: Seattle vs Las Vegas, plus Mexico City (partial data) where comparable."""
    r, mc, fb = (D[x].set_index("short_name") for x in ("r", "mc", "fb"))
    k, bid, m = (D[x].set_index("short_name") for x in ("k", "bid", "m"))
    pm = D["pm"].set_index("short_name")
    intl = pd.read_csv(MANUAL / "international_markets.csv")
    mx = intl[intl.market == "Mexico City"].set_index("item")["value"]
    bl = pd.read_csv(RESEARCH / "bidder_landscape.csv")
    ar = pd.read_csv(MANUAL / "arenas.csv", dtype={"cbsa_code": str})
    cmap = pd.read_csv(PROCESSED / "cbsa_factors.csv", dtype={"cbsa_code": str}).set_index("cbsa_code")["market_id"]
    ar["market_id"] = ar["cbsa_code"].map(cmap)
    cell = npv_cell(D)
    NA = "not available (partial data)"
    markets = ["Seattle", "Las Vegas", "Mexico City"]
    rows = []

    def add(metric, f, src, mexico=None):
        row = {"Metric": metric}
        for n in markets:
            if n == "Mexico City":
                row[n] = mexico if mexico is not None else NA
            else:
                row[n] = f(n)
        row["Source"] = src
        rows.append(row)

    def arenas(n):
        a = ar[(ar.market_id == m.at[n, "market_id"]) & (~ar.nba_tenant)].sort_values("capacity_basketball", ascending=False)
        return ("Y: " if r.at[n, "arena_ready"] == 1 else "N: ") + "; ".join(
            f"{x.arena} ({x.capacity_basketball:,}; {x.tenants if isinstance(x.tenants, str) else 'no major tenant listed'})" for x in a.itertuples())

    mxs = pm.loc["Mexico City"]
    add("Market", lambda n: m.at[n, "market_title"], "data/processed/metros.csv", "Greater Mexico City (Mexico)")
    add("Population", lambda n: f"{m.at[n, 'population']/1e6:.2f}M", "metros.csv; international_markets.csv", f"{float(mx['metro_population'])/1e6:.2f}M (2020)")
    add("Attractiveness rank (of non-NBA markets)", lambda n: f"#{int(r.at[n, 'rank_candidates'])}", "outputs/rankings.csv; partial_markets.csv", f"would rank #{int(mxs.rank_if_included)} (partial data)")
    add("Attractiveness score", lambda n: f"{r.at[n, 'total_score']:.2f}", "outputs/rankings.csv; partial_markets.csv", f"{mxs.total_score:.2f} (partial: A and B subsets only)")
    for c, lab in [("A_size_wealth", "Pillar A: size & wealth"), ("B_basketball_demand", "Pillar B: basketball demand")]:
        add(lab, lambda n, c=c: f"{r.at[n, c]:.2f}", "outputs/rankings.csv; partial_markets.csv", f"{mxs[c]:.2f} (partial)")
    add("Pillar C: corporate", lambda n: f"{r.at[n, 'C_corporate']:.2f}", "outputs/rankings.csv")
    add("P(top 10) / P(top 5)", lambda n: f"{mc.at[n, 'p_top10']:.0%} / {mc.at[n, 'p_top5']:.0%}", "outputs/monte_carlo.csv", "not in Monte Carlo (partial data)")
    add("Median rank (90% interval)", lambda n: f"#{mc.at[n, 'median_rank']:.0f} (#{mc.at[n, 'rank_p05']:.0f}-#{mc.at[n, 'rank_p95']:.0f})", "outputs/monte_carlo.csv", "not in Monte Carlo (partial data)")
    add("Ease of entry / quadrant", lambda n: f"{r.at[n, 'ease_of_entry']:.2f} / {r.at[n, 'quadrant']}", "outputs/rankings.csv; partial_markets.csv", f"{mxs.ease_of_entry:.2f} / {mxs.quadrant}")
    add("Miles to nearest NBA market", lambda n: f"{r.at[n, 'miles_to_nearest_nba']:.0f}", "outputs/rankings.csv; partial_markets.csv", f"{mxs.miles_to_nearest_nba:.0f}")
    add("NBA markets within 200 miles", lambda n: f"{int(r.at[n, 'nba_markets_within_200mi'])}", "outputs/rankings.csv; partial_markets.csv", f"{int(mxs.nba_markets_within_200mi)}")
    add("Big-league rivals (NFL+MLB+NHL)", lambda n: f"{int(r.at[n, 'big4_other_leagues'])}", "data/processed/metros.csv; international_markets.csv", "0 (Liga MX soccer not counted)")
    add("Arenas 17,000+ seats without NBA tenant (capacity; tenants)", arenas, "data/manual/arenas.csv; international_markets.csv", f"Y: Arena CDMX ({int(float(mx['largest_arena_capacity'])):,}; Mexico City Capitanes, G League)")
    add("G League team", lambda n: "Y" if m.at[n, "has_g_league"] == 1 else "N", "data/manual/teams.csv; international_markets.csv", "Y: Mexico City Capitanes")
    add("Transplant share (divided-loyalty risk)", lambda n: f"{fb.at[n, 'transplant_share']:.0%} ({fb.at[n, 'transplant_share_vs_nba_median']:+.0%} vs NBA median)", "outputs/fan_behavior.csv")
    add("Est. local revenue min / base / max", lambda n: f"{money(k.at[n, 'est_local_revenue_low'])} / {money(k.at[n, 'est_local_revenue_base'])} / {money(k.at[n, 'est_local_revenue_high'])}", "outputs/kpi_dashboard.csv")
    add("Price used (type; not strictly comparable)", lambda n: f"{money(bid.at[n, 'price_usd'])}: {bid.at[n, 'price_type']}", "outputs/bidder_multiples.csv", "not reported")
    add("Price / est. revenue (league avg value/revenue)", lambda n: f"{bid.at[n, 'price_to_revenue_base']:.1f}x ({bid.at[n, 'league_avg_value_to_revenue']:.1f}x)", "outputs/bidder_multiples.csv")
    add("Reported bidders", lambda n: "; ".join(bl[bl.market == n]["group / lead investors"]), "research/bidder_landscape.csv", "; ".join(bl[bl.market == "Mexico City"]["group / lead investors"]))
    add("Owner NPV: fee share − 20y dilution (league-wide, per existing team)", lambda n: f"{money(cell.npv_net_of_fee)} (both markets together; 3% growth, 8% discount)", "outputs/owner_npv.csv")
    t = pd.DataFrame(rows)
    txt = ("# Seattle vs Las Vegas (and Mexico City): head-to-head\n\n*Generated by `src/report.py` from `outputs/`. Interpretation by Noah. "
           "Mexico City has partial data: it is scored only on comparable factors and is not in the rankings or Monte Carlo.*\n\n" + md(t) +
           "\n\n![Head-to-head](../figures/11_seattle_vs_las_vegas.png)\n\nReported league focus: ESPN (2026-10-02) says the NBA and PJT Partners are more focused on Las Vegas, where bidding is more robust (`research/trends.csv`).\n\n## So what\n")
    (ROOT / "memo" / "HEAD_TO_HEAD.md").write_text(txt)


def final_report(D, runtime_s, test_output):
    dev = (ROOT / "DEVIATIONS.md").read_text()
    tail = "\n".join([l for l in (test_output or "").strip().splitlines() if l.strip()][-3:]) or "not run"
    txt = f"""# Final report

## What was built

- Phase 1: `data/processed/metros.csv` with {len(D['m'])} markets (CSA, else CBSA; San Juan flagged partial data), sourced manual tables in `data/manual/`, and a coverage report in `outputs/coverage.csv`.
- Phase 2: scorecard outputs (`rankings`, `pillar_scores`, `nba_benchmark`, `validity` and `sensitivity` CSVs).
- Phase 3: assumptions table (sourced from Sportico where possible), local revenue scenarios, owner NPV grid (`owner_npv.csv`, `owner_breakeven_growth.csv`), tornado, `kpi_dashboard.csv`, `focus_markets.csv`.
- Phase 4: `research/` (trends, comparables, focus markets, competitive landscape, insights).
- v4: realignment travel proxy, bidder landscape, Seattle vs Las Vegas head-to-head (`memo/HEAD_TO_HEAD.md`), honeymoon curve from Wikipedia game logs.
- Phase 5: 14 figures in `figures/`, including the attractiveness vs ease-of-entry matrix (headline), Monte Carlo robustness, owner NPV heatmap, focus markets, and `linkedin_summary.png`.
- v3: ease of entry (distance to nearest NBA market), Monte Carlo weights, fan-behavior lens, bidder multiples, `memo/EXEC_SUMMARY.md`, `memo/stakeholders.md`.
- Phase 6: README, `memo/MEMO.md` (headings only), `outputs/KEY_NUMBERS.md`, this report, and `run_all.py`.

## Tests

```
{tail}
```

## Runtime

Last `run_all.py` run took {runtime_s:.0f} seconds (raw downloads cached in `data/raw/`).

## Deviations & skipped sources

{dev.split(chr(10),2)[-1]}

## What Noah must write

- The memo sections in `memo/MEMO.md`, the headline and recommendation in `memo/EXEC_SUMMARY.md`, the stakeholder grid in `memo/stakeholders.md`, and the Recommendation section of the README.
- The "So what" in `memo/HEAD_TO_HEAD.md`, and the memo sections "Realignment: who moves East?", "Bidder landscape" and "Novelty effect".
- The "What this suggests" sections in `research/comparables.md` and `research/focus_markets.md`.
- The `implication` and `confidence` columns in `research/insights.csv`.
- A review of every row labeled "ASSUMPTION – Noah to review" in `data/manual/assumptions.csv`.
- A check of the reported (not league-confirmed) figures in `research/trends.csv` before citing them.
"""
    (OUTPUTS / "FINAL_REPORT.md").write_text(txt)


def main(runtime_s=0.0, test_output=""):
    D = load()
    key_numbers(D)
    focus_md(D)
    exec_summary(D)
    head_to_head(D)
    readme(D)
    final_report(D, runtime_s, test_output)
    print("README.md, KEY_NUMBERS.md, FINAL_REPORT.md written")


if __name__ == "__main__":
    main()
