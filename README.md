# Beyond Seattle and Vegas: NBA Expansion Market Strategy

## At a glance

- **Question:** Which North American markets are most attractive for an NBA team, which are overlooked, and does expansion pay off for existing owners?
- **Data scope:** 66 U.S. markets. A market is a Census combined statistical area (CSA), so San Jose sits inside the Bay Area and Baltimore inside Washington-Baltimore. Public data only. Mexico City and Vancouver are profiled but not scored.
- **Key numbers:**
  - Seattle ranks **#3** and Las Vegas **#5** among 39 non-NBA markets.
  - **6** non-NBA markets score at or above the median current NBA market (0.31): Raleigh, Omaha, Seattle, Austin, Las Vegas, Cincinnati.
  - Each existing owner's fee share (base) is **$566.7M**, compared with a 20-year NPV of shared-revenue dilution of **$156.6M** (3% growth, 8% discount).
  - Shared revenue would need to grow **14% a year** before dilution outweighs the fee. Reported payout growth is about 7% a year.

![Headline](figures/01_headline_top15.png)

## Approach

The scorecard has four pillars. Every factor is converted to a z-score across the 66 markets; population, GDP and large-establishment counts are logged first. Factors are averaged with equal weights inside each pillar, and the four pillars are averaged with equal weights into a total score. Current NBA markets are scored the same way and serve as the benchmark. CBSA data are aggregated to markets: counts and populations are summed, income is population-weighted, and the 18-44 share is recomputed from counts.

1. **A. Market size and wealth:** population, median household income, share of residents aged 18-44, population growth 2020-25, and GDP.
2. **B. Basketball demand:** NCAA D-I men's home attendance per 1,000 residents, and WNBA presence. G League presence is shown but not scored, because G League teams are mostly NBA-owned affiliates.
3. **C. Corporate money:** establishments with 500+ employees, as a total and per 100k residents.
4. **D. Competition and infrastructure:** NFL, MLB and NHL teams (counted as a negative), and whether the market has an NBA-capable arena (17,000+ seats).

## Data & sources

| Factor | Source | Year |
|---|---|---|
| Population, households, income, age 18-44 | Census ACS 5-year summary file (www2.census.gov) | 2020-2024 |
| Population growth | Census Population Estimates, Vintage 2025 | 2020-2025 |
| GDP | BEA CAGDP1 county GDP summed to market | 2024 |
| Large establishments (500+ employees) | Census County Business Patterns (metro/micro file) | 2023 |
| NCAA D-I men's basketball home attendance | NCAA attendance records PDF | 2025-26 |
| NBA/NFL/MLB/NHL/MLS/WNBA/G League teams | Wikipedia league articles (current teams tables) | accessed 2026-11-05 |
| Arenas 17,000+ seats | Wikipedia: List of indoor arenas in the United States | accessed 2026-11-05 |
| Market definitions | Census CBSA/CSA delineation files | July 2023 |
| Team revenue by stream, central revenue share, national TV per team | Sportico team-finance reporting | 2025-26 |
| Mexico City, Vancouver facts | Wikipedia (population, arena, history) | accessed 2026-11-05 |
| Google Trends; NTTO overseas visitors | Skipped (see DEVIATIONS.md) | - |

**Coverage** (`outputs/coverage.csv`):

| factor | share_with_data | n_markets |
|---|---|---|
| population | 100% | 66 |
| median_hh_income | 100% | 66 |
| share_18_44 | 100% | 66 |
| households | 100% | 66 |
| pop_growth_2020_2025 | 100% | 66 |
| gdp_2024_usd | 98% | 66 |
| ncaa_d1_home_attendance | 100% | 66 |
| has_wnba | 100% | 66 |
| has_g_league | 100% | 66 |
| large_establishments_500plus | 100% | 66 |
| big4_other_leagues | 100% | 66 |
| arena_capable | 100% | 66 |
| google_trends_nba | 0% | 66 |
| overseas_visitors_ntto | 0% | 66 |

## Results

**Top 15 non-NBA markets** (equal weights; `outputs/rankings.csv`):

| rank_candidates | short_name | market_title | total_score | A_size_wealth | B_basketball_demand | C_corporate | D_competition_infra | overlooked | top_pillar |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Raleigh | Raleigh-Durham-Cary, NC | 0.57 | 0.61 | 1.37 | -0.16 | 0.44 | True | B_basketball_demand |
| 2 | Omaha | Omaha-Fremont, NE-IA | 0.53 | -0.34 | 1.13 | 0.55 | 0.76 | True | B_basketball_demand |
| 3 | Seattle | Seattle-Tacoma, WA | 0.49 | 1.06 | 0.61 | 0.45 | -0.19 | True | A_size_wealth |
| 4 | Austin | Austin-Round Rock-San Marcos, TX | 0.42 | 1.31 | -0.23 | 0.91 | -0.30 | True | A_size_wealth |
| 5 | Las Vegas | Las Vegas-Henderson, NV | 0.32 | 0.00 | 0.66 | 0.50 | 0.13 | True | B_basketball_demand |
| 6 | Cincinnati | Cincinnati-Wilmington, OH-KY-IN | 0.31 | -0.17 | 0.48 | 0.82 | 0.13 | True | C_corporate |
| 7 | Nashville | Nashville-Davidson--Murfreesboro, TN | 0.24 | 0.38 | -0.09 | 0.53 | 0.13 | False | C_corporate |
| 8 | Louisville | Louisville/Jefferson County--Elizabethtown, KY-IN | 0.18 | -0.55 | 0.41 | 0.11 | 0.76 | False | D_competition_infra |
| 9 | Columbus | Columbus-Marion-Zanesville, OH | 0.08 | 0.08 | -0.34 | 0.14 | 0.44 | False | D_competition_infra |
| 10 | Kansas City | Kansas City-Overland Park-Kansas City, MO-KS | 0.06 | -0.03 | -0.16 | 0.30 | 0.13 | False | C_corporate |
| 11 | Knoxville | Knoxville-Morristown-Sevierville, TN | 0.02 | -0.62 | 0.97 | -1.02 | 0.76 | False | B_basketball_demand |
| 12 | San Diego | San Diego-Chula Vista-Carlsbad, CA | -0.04 | 0.58 | -0.32 | 0.19 | -0.62 | False | A_size_wealth |
| 13 | Greensboro | Greensboro--Winston-Salem--High Point, NC | -0.05 | -0.58 | 0.11 | -0.48 | 0.76 | False | D_competition_infra |
| 14 | Richmond | Richmond, VA | -0.06 | -0.10 | 0.23 | -0.08 | -0.30 | False | B_basketball_demand |
| 15 | St. Louis | St. Louis-St. Charles-Farmington, MO-IL | -0.09 | -0.29 | -0.42 | 0.24 | 0.13 | False | C_corporate |

**How the top 10 changed from v1.** v1 ranked CBSAs and scored G League presence. The middle column shows the switch to CSAs with G League still scored; the last column is final (`outputs/top10_change.csv`). Omaha was below 1M people as a CBSA, so it was not in the v1 study set.

| short_name | market_title | rank_final_csa_no_gleague | top_pillar | rank_v1_cbsa_with_gleague | rank_csa_with_gleague |
|---|---|---|---|---|---|
| Raleigh | Raleigh-Durham-Cary, NC | #1 | B_basketball_demand | #9 | #2 |
| Omaha | Omaha-Fremont, NE-IA | #2 | B_basketball_demand |  | #4 |
| Seattle | Seattle-Tacoma, WA | #3 | A_size_wealth | #3 | #3 |
| Austin | Austin-Round Rock-San Marcos, TX | #4 | A_size_wealth | #2 | #1 |
| Las Vegas | Las Vegas-Henderson, NV | #5 | B_basketball_demand | #7 | #6 |
| Cincinnati | Cincinnati-Wilmington, OH-KY-IN | #6 | C_corporate | #5 | #5 |
| Nashville | Nashville-Davidson--Murfreesboro, TN | #7 | C_corporate | #4 | #7 |
| Louisville | Louisville/Jefferson County--Elizabethtown, KY-IN | #8 | D_competition_infra | #8 | #9 |
| Columbus | Columbus-Marion-Zanesville, OH | #9 | D_competition_infra | #6 | #11 |
| Kansas City | Kansas City-Overland Park-Kansas City, MO-KS | #10 | C_corporate | #11 | #12 |
| San Diego | San Diego-Chula Vista-Carlsbad, CA | #12 | A_size_wealth | #10 | #8 |
| San Jose | merged into a larger CSA (see metros.csv member_metros) |  |  | #1 |  |

**Does the scorecard recognize existing NBA markets?** Difference in means, NBA minus non-NBA, with Welch 95% CI (`outputs/validity.csv`). This is an association check, not a prediction:

| measure | mean_nba | mean_non_nba | diff_nba_minus_non | ci95_low | ci95_high | point_biserial_r | p_value |
|---|---|---|---|---|---|---|---|
| A_size_wealth | 0.43 | -0.30 | 0.73 | 0.44 | 1.02 | 0.54 | 0.00 |
| B_basketball_demand | 0.05 | -0.03 | 0.08 | -0.22 | 0.38 | 0.07 | 0.60 |
| C_corporate | 0.56 | -0.39 | 0.95 | 0.55 | 1.35 | 0.51 | 0.00 |
| D_competition_infra | 0.02 | -0.01 | 0.03 | -0.23 | 0.29 | 0.03 | 0.79 |
| total_score | 0.26 | -0.18 | 0.45 | 0.26 | 0.64 | 0.51 | 0.00 |

**Sensitivity:** rank under six weightings (`outputs/sensitivity.csv`). A blank in the arena column means the market is not arena-ready.

| short_name | rank_equal | rank_size_heavy | rank_wealth_corporate_heavy | rank_demand_heavy | rank_ignore_competition | rank_arena_required | top10_frequency |
|---|---|---|---|---|---|---|---|
| Raleigh | 1 | 3 | 7 | 1 | 2 | 1 | 6 |
| Omaha | 2 | 5 | 2 | 2 | 3 | 2 | 6 |
| Seattle | 3 | 2 | 4 | 3 | 1 | 3 | 6 |
| Austin | 4 | 1 | 1 | 8 | 10 |  | 5 |
| Las Vegas | 5 | 6 | 5 | 4 | 4 | 4 | 6 |
| Cincinnati | 6 | 8 | 3 | 5 | 5 | 5 | 6 |
| Nashville | 7 | 4 | 6 | 9 | 6 | 6 | 6 |
| Louisville | 8 | 11 | 8 | 7 | 8 | 7 | 5 |
| Columbus | 9 | 9 | 10 | 15 | 9 | 8 | 5 |
| Kansas City | 10 | 10 | 9 | 14 | 7 | 9 | 5 |
| Knoxville | 11 | 16 | 23 | 6 | 13 | 10 | 2 |
| San Diego | 12 | 7 | 11 | 18 | 19 |  | 1 |
| Greensboro | 13 | 19 | 17 | 13 | 14 | 11 | 0 |
| Richmond | 14 | 12 | 14 | 12 | 21 |  | 0 |
| St. Louis | 15 | 15 | 12 | 21 | 12 | 12 | 0 |

![Sensitivity](figures/03_sensitivity_heatmap.png)
![Pillars](figures/02_pillar_breakdown_top8.png)
![Scatter](figures/04_population_vs_income.png)

## Focus markets

These are the reported front-runners (Seattle, Las Vegas), Mexico City, and markets often named in coverage (`outputs/focus_markets.csv`, `research/focus_markets.md`).

| focus_label | scored | attractiveness_rank | total_score | arena_ready | population |
|---|---|---|---|---|---|
| Seattle | Y | #3 | 0.49 | Y | 5.0M |
| Las Vegas | Y | #5 | 0.32 | Y | 2.4M |
| Pittsburgh | Y | #23 | -0.32 | Y | 2.7M |
| Louisville | Y | #8 | 0.18 | Y | 1.5M |
| Kansas City | Y | #10 | 0.06 | Y | 2.6M |
| Nashville | Y | #7 | 0.24 | Y | 2.3M |
| Austin | Y | #4 | 0.42 | N | 2.4M |
| San Diego | Y | #12 | -0.04 | N | 3.3M |
| St. Louis | Y | #15 | -0.09 | Y | 2.9M |
| Columbus, OH | Y | #9 | 0.08 | Y | 2.6M |
| Cincinnati | Y | #6 | 0.31 | Y | 2.3M |
| Raleigh | Y | #1 | 0.57 | Y | 2.3M |
| Tampa | Y | #17 | -0.16 | Y | 3.3M |
| Baltimore | Y | (existing NBA market) | 0.56 | N | 10.1M |
| Omaha | Y | #2 | 0.53 | Y | 1.0M |
| Mexico City | N (outside U.S. data) |  |  |  | 21.4M |
| Vancouver | N (outside U.S. data) |  |  |  | 2.6M |

![Focus](figures/08_focus_markets.png)

## Business case

Local revenue starts from the average NBA team's reported revenue by stream (Sportico, 2025-26). Each stream is scaled by how the market compares with the median NBA market, using a labeled elasticity assumption. Min and max are taken across the elasticity scenarios.

| short_name | attractiveness_rank | top10_frequency | population | median_hh_income | competing_teams | arena_ready | est_local_revenue_low | est_local_revenue_base | est_local_revenue_high | local_revenue_per_capita_base |
|---|---|---|---|---|---|---|---|---|---|---|
| Raleigh | 1.00 | 6 | 2.34M | 92,233.42 | 1 | Y | $178.1M | $205.9M | $238.2M | 88.14 |
| Omaha | 2.00 | 6 | 1.02M | 84,444.28 | 0 | Y | $97.7M | $138.0M | $194.9M | 135.38 |
| Seattle | 3.00 | 6 | 5.01M | 111,229.39 | 3 | Y | $290.2M | $307.7M | $326.7M | 61.42 |
| Austin | 4.00 | 5 | 2.43M | 100,431.00 | 0 | N | $182.8M | $208.6M | $238.2M | 85.97 |
| Las Vegas | 5.00 | 6 | 2.38M | 76,112.78 | 2 | Y | $169.6M | $198.9M | $233.5M | 83.44 |
| Cincinnati | 6.00 | 6 | 2.31M | 80,925.39 | 2 | Y | $170.4M | $199.5M | $233.7M | 86.26 |
| Nashville | 7.00 | 6 | 2.32M | 83,136.24 | 2 | Y | $164.0M | $194.2M | $230.0M | 83.58 |
| Louisville | 8.00 | 5 | 1.50M | 73,326.80 | 0 | Y | $115.7M | $154.0M | $205.2M | 102.72 |

![KPI](figures/05_kpi_dashboard.png)
![Tornado](figures/06_tornado.png)

**Owner economics: fee share minus 20-year NPV of dilution** (base fee, all central revenue, gross; `outputs/owner_npv.csv`):

| growth / discount | 6% | 8% | 10% |
|---|---|---|---|
| 0% | $432.4M | $451.8M | $467.0M |
| 3% | $380.5M | $410.0M | $433.0M |
| 6% | $303.7M | $349.3M | $384.3M |

Range of fee share minus NPV by pool definition and owner share (all growth, discount and fee scenarios):

| pool_definition | owner_share | min | max |
|---|---|---|---|
| all_central_revenue | gross | $203.7M | $567.0M |
| all_central_revenue | net_of_player_share | $337.8M | $617.8M |
| national_tv_only | gross | $264.4M | $590.0M |
| national_tv_only | net_of_player_share | $367.6M | $629.1M |

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

Python (pandas, numpy, statsmodels, scipy, matplotlib, requests, pytest, openpyxl, pdfplumber, lxml). Every number in this README is generated by `src/report.py`.
