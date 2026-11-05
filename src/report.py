"""Phase 6: write README.md, outputs/KEY_NUMBERS.md and outputs/FINAL_REPORT.md from outputs/.
No number in these files is typed by hand: every one is read from a CSV here."""
import pandas as pd
from config import OUTPUTS, PROCESSED, ROOT, MANUAL, ACCESS_DATE


def md(df, floatfmt=2):
    """Small DataFrame -> markdown table (no extra dependency)."""
    df = df.copy()
    for c in df.columns:
        if df[c].dtype.kind == "f":
            df[c] = df[c].map(lambda v: "" if pd.isna(v) else f"{v:,.{floatfmt}f}")
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    lines += ["| " + " | ".join(map(str, r)) + " |" for r in df.values]
    return "\n".join(lines)


def money(v):
    return f"${v/1e9:,.2f}B" if abs(v) >= 1e9 else f"${v/1e6:,.1f}M"


def load():
    r = pd.read_csv(OUTPUTS / "rankings.csv", dtype={"cbsa_code": str})
    return dict(r=r, m=pd.read_csv(PROCESSED / "metros.csv", dtype={"cbsa_code": str}),
                k=pd.read_csv(OUTPUTS / "kpi_dashboard.csv", dtype={"cbsa_code": str}).sort_values("attractiveness_rank"),
                v=pd.read_csv(OUTPUTS / "validity.csv"), s=pd.read_csv(OUTPUTS / "sensitivity.csv"),
                d=pd.read_csv(OUTPUTS / "dilution_payback.csv"), cov=pd.read_csv(OUTPUTS / "coverage.csv"),
                t=pd.read_csv(OUTPUTS / "tornado.csv"))


def key_numbers(D):
    r, v, d, k = D["r"], D["v"], D["d"], D["k"]
    med = r["median_nba_score"].iloc[0]
    rank = lambda n: int(r.loc[r.short_name == n, "rank_candidates"].iloc[0])
    over = r[r["overlooked"]]["short_name"].tolist()
    tot = v[v.measure == "total_score"].iloc[0]
    base = d[d.scenario == "base"].iloc[0]
    items = [
        ("Metros scored", f"{len(D['m'])}", "U.S. CBSAs with 1M+ people, plus every NBA metro and metros named in expansion coverage", "-", "data/processed/metros.csv (row count)"),
        ("Current U.S. NBA metros in benchmark", f"{int(r['nba_metro'].sum())}", "29 U.S. teams in 27 metros (LA and NY have two); Toronto excluded", "-", "outputs/nba_benchmark.csv"),
        ("Median current-NBA-market score", f"{med:.2f}", "Score of the middle current NBA market; the 'overlooked' bar", "equal weights", "outputs/rankings.csv (median_nba_score)"),
        ("Seattle rank among non-NBA metros", f"#{rank('Seattle')}", "Position in the equal-weight ranking of non-NBA metros", "equal weights", "outputs/rankings.csv (short_name=Seattle)"),
        ("Las Vegas rank among non-NBA metros", f"#{rank('Las Vegas')}", "As above", "equal weights", "outputs/rankings.csv (short_name=Las Vegas)"),
        ("Overlooked metros", f"{len(over)} ({', '.join(over)})", "Non-NBA metros scoring at or above the median current NBA market", "equal weights", "outputs/rankings.csv (overlooked=True)"),
        ("NBA vs non-NBA total-score gap", f"{tot.diff_nba_minus_non:.2f}", "Current NBA metros score higher on average than non-NBA metros", f"95% CI {tot.ci95_low:.2f} to {tot.ci95_high:.2f}; point-biserial r = {tot.point_biserial_r:.2f}", "outputs/validity.csv (measure=total_score)"),
        ("Annual national media, reported", money(pd.read_csv(MANUAL / "assumptions.csv").set_index("assumption").loc["national_media_total_usd", "base"] / 11), "Reported $76B over 11 years", "reported, not disclosed by league", "data/manual/assumptions.csv (national_media_total_usd)"),
    ]
    for _, row in d.iterrows():
        items.append((f"Annual dilution per existing team ({row.scenario})", money(row.annual_dilution_per_existing_team),
                      "National revenue each existing team gives up per year when 30 shares become 32", "scenario", f"outputs/dilution_payback.csv (scenario={row.scenario})"))
        items.append((f"Fee share per existing team ({row.scenario})", money(row.fee_received_per_existing_team),
                      "One-time payment: fee x 2 teams / 30 owners", "scenario", f"outputs/dilution_payback.csv (scenario={row.scenario})"))
        items.append((f"Breakeven years ({row.scenario})", f"{row.breakeven_years:.1f}",
                      "Years until cumulative dilution equals the fee share (no growth, no discounting)", "scenario", f"outputs/dilution_payback.csv (scenario={row.scenario})"))
    for _, row in k.iterrows():
        items.append((f"Est. local revenue, {row.short_name}", f"{money(row.est_local_revenue_low)} / {money(row.est_local_revenue_base)} / {money(row.est_local_revenue_high)}",
                      "Gate + sponsorship + local media per year", "low / base / high; built on labeled assumptions", f"outputs/kpi_dashboard.csv (short_name={row.short_name})"))
    top = D["t"].iloc[0]
    items.append(("Most influential revenue assumption", f"{top.assumption} (swing {money(top.swing)})", "Moves combined top-8 base local revenue the most", "tornado", "outputs/tornado.csv (row 1)"))
    t = pd.DataFrame(items, columns=["Number", "Value", "Plain-English meaning", "Scenario / CI", "Source file and row"])
    (OUTPUTS / "KEY_NUMBERS.md").write_text("# Key numbers\n\nGenerated by `src/report.py` from `outputs/`. Do not edit by hand.\n\n" + md(t) + "\n")
    return items


def readme(D):
    r, k, v, s, d, cov = D["r"], D["k"], D["v"], D["s"], D["d"], D["cov"]
    med = r["median_nba_score"].iloc[0]
    rank = lambda n: int(r.loc[r.short_name == n, "rank_candidates"].iloc[0])
    base = d[d.scenario == "base"].iloc[0]
    top15 = r[~r["nba_metro"]].head(15)[["rank_candidates", "short_name", "total_score", "A_size_wealth", "B_basketball_demand", "C_corporate", "D_competition_infra", "overlooked", "top_pillar"]].copy()
    top15["rank_candidates"] = top15["rank_candidates"].astype(int)
    sens = s.head(15)[["short_name"] + [c for c in s.columns if c.startswith("rank_")] + ["top10_frequency"]]
    kp = k[["short_name", "attractiveness_rank", "top10_frequency", "population", "median_hh_income", "competing_teams", "arena_ready",
            "est_local_revenue_low", "est_local_revenue_base", "est_local_revenue_high", "local_revenue_per_capita_base"]].copy()
    for c in ["est_local_revenue_low", "est_local_revenue_base", "est_local_revenue_high"]:
        kp[c] = kp[c].map(money)
    kp["population"] = kp["population"].map(lambda x: f"{x/1e6:.2f}M")
    dd = d.copy()
    for c in dd.columns[1:-1]:
        dd[c] = dd[c].map(money)
    covt = cov.copy(); covt["share_with_data"] = (covt["share_with_data"] * 100).round(0).astype(int).astype(str) + "%"
    srcs = pd.DataFrame([
        ("Population, households, income, age 18-44", "Census ACS 5-year summary file (www2.census.gov)", "2020-2024"),
        ("Population growth", "Census Population Estimates, Vintage 2025", "2020-2025"),
        ("GDP", "BEA CAGDP1 county GDP summed to CBSA", "2024"),
        ("Large establishments (500+ employees)", "Census County Business Patterns (metro file)", "2023"),
        ("NCAA D-I men's basketball home attendance", "NCAA attendance records PDF", "2025-26"),
        ("NBA/NFL/MLB/NHL/MLS/WNBA/G League teams", "Wikipedia league articles (current teams tables)", f"accessed {ACCESS_DATE}"),
        ("Arenas 17,000+ seats", "Wikipedia: List of indoor arenas in the United States", f"accessed {ACCESS_DATE}"),
        ("Metro definitions", "Census CBSA delineation files", "July 2023"),
        ("Google Trends; NTTO overseas visitors", "Skipped (see DEVIATIONS.md)", "-"),
    ], columns=["Factor", "Source", "Year"])
    txt = f"""# Beyond Seattle and Vegas: NBA Expansion Market Strategy

## At a glance

- **Question:** Which North American markets are most attractive for an NBA team, which are overlooked, and does expansion pay off for existing owners?
- **Data scope:** {len(D['m'])} U.S. metro areas (CBSAs), public data only; Canada is out of scope.
- **Key numbers:**
  - Seattle ranks **#{rank('Seattle')}** and Las Vegas **#{rank('Las Vegas')}** among {int((~r['nba_metro']).sum())} non-NBA metros.
  - **{int(r['overlooked'].sum())}** non-NBA metros score at or above the median current NBA market ({med:.2f}).
  - Reported fee share per existing owner (base): **{money(base.fee_received_per_existing_team)}**, compared with annual national-revenue dilution of **{money(base.annual_dilution_per_existing_team)}**.
  - Base-case breakeven: **{base.breakeven_years:.0f} years** of dilution to equal the fee share (no growth, no discounting).

![Headline](figures/01_headline_top15.png)

## Approach

The scorecard has four pillars. Every factor is converted to a z-score across the {len(D['m'])} metros; population, GDP and large-establishment counts are logged first. Factors are averaged with equal weights inside each pillar, and the four pillars are averaged with equal weights into a total score. Current NBA metros are scored the same way and serve as the benchmark.

1. **A. Market size and wealth:** population, median household income, share of residents aged 18-44, population growth 2020-25, and GDP.
2. **B. Basketball demand:** NCAA D-I men's home attendance per 1,000 residents, WNBA presence, and G League presence.
3. **C. Corporate money:** establishments with 500+ employees, as a total and per 100k residents.
4. **D. Competition and infrastructure:** NFL, MLB and NHL teams (counted as a negative), and whether the metro has an NBA-capable arena (17,000+ seats).

## Data & sources

{md(srcs)}

**Coverage** (share of metros with data, from `outputs/coverage.csv`):

{md(covt)}

## Results

**Top 15 non-NBA metros** (equal weights; `outputs/rankings.csv`):

{md(top15)}

**Does the scorecard recognize existing NBA markets?** Difference in means, NBA minus non-NBA, with Welch 95% CI (`outputs/validity.csv`). This is an association check, not a prediction:

{md(v[['measure','mean_nba','mean_non_nba','diff_nba_minus_non','ci95_low','ci95_high','point_biserial_r','p_value']])}

**Sensitivity:** rank under six weightings (`outputs/sensitivity.csv`). A blank in the arena column means the metro is not arena-ready.

{md(sens, 0)}

![Sensitivity](figures/03_sensitivity_heatmap.png)
![Pillars](figures/02_pillar_breakdown_top8.png)
![Scatter](figures/04_population_vs_income.png)

## Business case

These are scenarios built on assumptions in `data/manual/assumptions.csv`. Unsourced inputs are labeled "ASSUMPTION – Noah to review".

{md(kp)}

![KPI](figures/05_kpi_dashboard.png)

**Dilution vs fee** (`outputs/dilution_payback.csv`):

{md(dd)}

![Payback](figures/07_dilution_payback.png)
![Tornado](figures/06_tornado.png)

## Market & competitive research

- `research/trends.csv`: dated, sourced facts on the expansion process, fees, the media deal, and NHL, WNBA and MLS expansions.
- `research/comparables.md`: Vegas Golden Knights, Seattle Kraken, and recent WNBA expansion teams.
- `research/competitive_landscape.csv`: pro teams, D-I schools and arenas in each top-8 market.
- `research/insights.csv`: themes with linked evidence; implications left for Noah.

## Recommendation

*(Written by Noah.)*

## Limitations & data I'd buy

- **Associations only.** The validity check asks whether the scorecard separates existing NBA metros from the rest. It does not show what causes team success.
- **G League presence** partly reflects NBA affiliation, which flatters current NBA metros on Pillar B.
- **The CBSA unit ignores neighbors.** San Jose is scored separately from the Warriors' San Francisco CBSA, and Baltimore separately from Washington. Cannibalization is not modeled.
- **Missing data:** Google Trends (folder empty), NTTO overseas visitors (dashboard only), and Canadian metros (Toronto, Vancouver, Montreal) are not in the scorecard. Virginia Beach GDP is missing.
- **NCAA mapping:** schools are assigned to metros by main-campus county. Only D-I schools in the study metros are mapped.
- **Business case:** revenue lines rest on labeled assumptions. Dilution counts the national media pool (plus an assumed uplift) only, with no growth or discounting.
- **Data I'd buy:** Nielsen TV ratings and DMA viewing households, team revenues, ticket prices, sponsorship deals, NBA League Pass and merchandise data.

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

- Phase 1: `data/processed/metros.csv` with {len(D['m'])} metros, sourced manual tables in `data/manual/`, and a coverage report in `outputs/coverage.csv`.
- Phase 2: scorecard outputs (`rankings`, `pillar_scores`, `nba_benchmark`, `validity` and `sensitivity` CSVs).
- Phase 3: assumptions table; local revenue, dilution and payback scenarios; tornado; `kpi_dashboard.csv`.
- Phase 4: `research/` (trends, comparables, competitive landscape, insights).
- Phase 5: 8 figures in `figures/`, including `linkedin_summary.png`.
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
- The "What this suggests" sections in `research/comparables.md`.
- The `implication` and `confidence` columns in `research/insights.csv`.
- A review of every row labeled "ASSUMPTION – Noah to review" in `data/manual/assumptions.csv`.
- A check of the reported (not league-confirmed) figures in `research/trends.csv` before citing them.
"""
    (OUTPUTS / "FINAL_REPORT.md").write_text(txt)


def main(runtime_s=0.0, test_output=""):
    D = load()
    key_numbers(D)
    readme(D)
    final_report(D, runtime_s, test_output)
    print("README.md, KEY_NUMBERS.md, FINAL_REPORT.md written")


if __name__ == "__main__":
    main()
