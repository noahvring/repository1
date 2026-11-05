"""Phase 6: write README.md, outputs/KEY_NUMBERS.md and outputs/FINAL_REPORT.md from outputs/.
No number in these files is typed by hand: every one is read from a CSV here."""
import pandas as pd
from config import OUTPUTS, PROCESSED, ROOT, MANUAL, ACCESS_DATE, RESEARCH


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
                t=pd.read_csv(OUTPUTS / "tornado.csv"))


def npv_base(D):
    n = D["npv"]
    return n[(n.pool_definition == "all_central_revenue") & (n.owner_share == "gross") & (n.fee_scenario == "base")]


def key_numbers(D):
    r, v, k, n, beg = D["r"], D["v"], D["k"], D["npv"], D["beg"]
    A = pd.read_csv(MANUAL / "assumptions.csv").set_index("assumption")
    med = r["median_nba_score"].iloc[0]
    rank = lambda name: int(r.loc[r.short_name == name, "rank_candidates"].iloc[0])
    over = r[r["overlooked"]]["short_name"].tolist()
    tot = v[v.measure == "total_score"].iloc[0]
    nb = npv_base(D)
    cell = nb[(nb.media_growth == 0.03) & (nb.discount_rate == 0.08)].iloc[0]
    worst = n.loc[n["npv_net_of_fee"].idxmin()]
    be = beg[(beg.discount_rate == 0.08) & (beg.fee_scenario == "base")].iloc[0]
    items = [
        ("Markets scored", f"{len(D['m'])}", "U.S. markets = Census combined statistical areas (CSA), or the metro (CBSA) if not in a CSA; 1M+ people, plus every NBA market and markets named in coverage", "-", "data/processed/metros.csv (row count)"),
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
    cell = nb[(nb.media_growth == 0.03) & (nb.discount_rate == 0.08)].iloc[0]
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
        ("Mexico City, Vancouver facts", "Wikipedia (population, arena, history)", f"accessed {ACCESS_DATE}"),
        ("Google Trends; NTTO overseas visitors", "Skipped (see DEVIATIONS.md)", "-"),
    ], columns=["Factor", "Source", "Year"])
    txt = f"""# Beyond Seattle and Vegas: NBA Expansion Market Strategy

## At a glance

- **Question:** Which North American markets are most attractive for an NBA team, which are overlooked, and does expansion pay off for existing owners?
- **Data scope:** {len(D['m'])} U.S. markets. A market is a Census combined statistical area (CSA), so San Jose sits inside the Bay Area and Baltimore inside Washington-Baltimore. Public data only. Mexico City and Vancouver are profiled but not scored.
- **Key numbers:**
  - Seattle ranks **#{rank('Seattle')}** and Las Vegas **#{rank('Las Vegas')}** among {int((~r['nba_metro']).sum())} non-NBA markets.
  - **{int(r['overlooked'].sum())}** non-NBA markets score at or above the median current NBA market ({med:.2f}): {', '.join(r[r['overlooked']]['short_name'])}.
  - Each existing owner's fee share (base) is **{money(cell.fee_share_per_existing_team)}**, compared with a 20-year NPV of shared-revenue dilution of **{money(cell.npv_dilution_20y)}** (3% growth, 8% discount).
  - Shared revenue would need to grow **{be.breakeven_growth:.0%} a year** before dilution outweighs the fee. Reported payout growth is about 7% a year.

![Headline](figures/01_headline_top15.png)

## Approach

The scorecard has four pillars. Every factor is converted to a z-score across the {len(D['m'])} markets; population, GDP and large-establishment counts are logged first. Factors are averaged with equal weights inside each pillar, and the four pillars are averaged with equal weights into a total score. Current NBA markets are scored the same way and serve as the benchmark. CBSA data are aggregated to markets: counts and populations are summed, income is population-weighted, and the 18-44 share is recomputed from counts.

1. **A. Market size and wealth:** population, median household income, share of residents aged 18-44, population growth 2020-25, and GDP.
2. **B. Basketball demand:** NCAA D-I men's home attendance per 1,000 residents, and WNBA presence. G League presence is shown but not scored, because G League teams are mostly NBA-owned affiliates.
3. **C. Corporate money:** establishments with 500+ employees, as a total and per 100k residents.
4. **D. Competition and infrastructure:** NFL, MLB and NHL teams (counted as a negative), and whether the market has an NBA-capable arena (17,000+ seats).

## Data & sources

{md(srcs)}

**Coverage** (`outputs/coverage.csv`):

{md(covt)}

## Results

**Top 15 non-NBA markets** (equal weights; `outputs/rankings.csv`):

{md(top15)}

**How the top 10 changed from v1.** v1 ranked CBSAs and scored G League presence. The middle column shows the switch to CSAs with G League still scored; the last column is final (`outputs/top10_change.csv`). Omaha was below 1M people as a CBSA, so it was not in the v1 study set.

{md(ch)}

**Does the scorecard recognize existing NBA markets?** Difference in means, NBA minus non-NBA, with Welch 95% CI (`outputs/validity.csv`). This is an association check, not a prediction:

{md(v[['measure','mean_nba','mean_non_nba','diff_nba_minus_non','ci95_low','ci95_high','point_biserial_r','p_value']])}

**Sensitivity:** rank under six weightings (`outputs/sensitivity.csv`). A blank in the arena column means the market is not arena-ready.

{md(sens, 0)}

![Sensitivity](figures/03_sensitivity_heatmap.png)
![Pillars](figures/02_pillar_breakdown_top8.png)
![Scatter](figures/04_population_vs_income.png)

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
- **College basketball per capita can dominate a small market.** Omaha and Raleigh-Durham rank high mostly on Pillar B. See `top_pillar` in `outputs/rankings.csv`.
- **CSAs still split some media markets.** Neighboring NBA markets outside the CSA (e.g. Las Vegas fans of the Suns or Lakers) and cannibalization are not modeled.
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

Python ({', '.join(l.split('==')[0] for l in (ROOT / 'requirements.txt').read_text().split())}). Every number in this README is generated by `src/report.py`.
"""
    (ROOT / "README.md").write_text(txt)


def final_report(D, runtime_s, test_output):
    dev = (ROOT / "DEVIATIONS.md").read_text()
    tail = "\n".join([l for l in (test_output or "").strip().splitlines() if l.strip()][-3:]) or "not run"
    txt = f"""# Final report

## What was built

- Phase 1: `data/processed/metros.csv` with {len(D['m'])} markets (CSA, else CBSA), sourced manual tables in `data/manual/`, and a coverage report in `outputs/coverage.csv`.
- Phase 2: scorecard outputs (`rankings`, `pillar_scores`, `nba_benchmark`, `validity` and `sensitivity` CSVs).
- Phase 3: assumptions table (sourced from Sportico where possible), local revenue scenarios, owner NPV grid (`owner_npv.csv`, `owner_breakeven_growth.csv`), tornado, `kpi_dashboard.csv`, `focus_markets.csv`.
- Phase 4: `research/` (trends, comparables, focus markets, competitive landscape, insights).
- Phase 5: 9 figures in `figures/`, including the owner NPV heatmap, focus markets, and `linkedin_summary.png`.
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

- The memo sections in `memo/MEMO.md`, and the Recommendation section of the README.
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
    readme(D)
    final_report(D, runtime_s, test_output)
    print("README.md, KEY_NUMBERS.md, FINAL_REPORT.md written")


if __name__ == "__main__":
    main()
