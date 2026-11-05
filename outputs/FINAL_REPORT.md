# Final report

## What was built

- Phase 1: `data/processed/metros.csv` with 67 markets (CSA, else CBSA; San Juan flagged partial data), sourced manual tables in `data/manual/`, and a coverage report in `outputs/coverage.csv`.
- Phase 2: scorecard outputs (`rankings`, `pillar_scores`, `nba_benchmark`, `validity` and `sensitivity` CSVs).
- Phase 3: assumptions table (sourced from Sportico where possible), local revenue scenarios, owner NPV grid (`owner_npv.csv`, `owner_breakeven_growth.csv`), tornado, `kpi_dashboard.csv`, `focus_markets.csv`.
- Phase 4: `research/` (trends, comparables, focus markets, competitive landscape, insights).
- v4: realignment travel proxy, bidder landscape, Seattle vs Las Vegas head-to-head (`memo/HEAD_TO_HEAD.md`), honeymoon curve from Wikipedia game logs.
- Phase 5: 14 figures in `figures/`, including the attractiveness vs ease-of-entry matrix (headline), Monte Carlo robustness, owner NPV heatmap, focus markets, and `linkedin_summary.png`.
- v3: ease of entry (distance to nearest NBA market), Monte Carlo weights, fan-behavior lens, bidder multiples, `memo/EXEC_SUMMARY.md`, `memo/stakeholders.md`.
- Phase 6: README, `memo/MEMO.md` (headings only), `outputs/KEY_NUMBERS.md`, this report, and `run_all.py`.

## Tests

```
.......................                                                  [100%]
23 passed in 1.16s
```

## Runtime

Last `run_all.py` run took 15 seconds (raw downloads cached in `data/raw/`).

## Deviations & skipped sources

All access attempts on 2026-11-05.

| Item | What happened | Action |
|---|---|---|
| Census API (`api.census.gov`) | Returns "Missing Key" for every request (a key is now required). | Used the keyless ACS 2020–2024 5-year **summary files** on `www2.census.gov` instead (same data, bulk download). Population growth uses Vintage 2025 population estimates. |
| Census API first attempt | Network policy blocked all data domains at session start. | Noah allowlisted the domains; work resumed. |
| BEA metro GDP | No key-free metro API. Used BEA county GDP file `CAGDP1.zip` (current-dollar GDP, 2024) summed to CBSA with Census 2023 county delineations. Virginia independent cities that BEA combines with counties were matched by name. | Virginia Beach-Chesapeake-Norfolk GDP stays missing (combination areas could not all be matched). |
| NTTO overseas visitors (`trade.gov`) | City/MSA data is only published in an interactive Power BI dashboard (`powerbi.trade.gov`); no downloadable file link found. | Skipped. Pillar C uses County Business Patterns only. |
| Google Trends | `data/manual/google_trends/` is still empty on the v2 rerun. | Skipped and logged; no DMA crosswalk built (nothing to map). Add the CSV and rerun to include it. |
| Canada (StatCan) | Not attempted, to protect the time budget; comparable ACS/CBP/BEA measures would need a separate crosswalk. | Toronto Raptors are mapped to `CAN-Toronto` and excluded from the U.S. benchmark. Vancouver and Montreal are a limitation. |
| Puerto Rico (San Juan CBSA) | Over 1M people but missing from CBP/BEA metro files. | Excluded from the study set. |
| `www.nba.com`, `apnews.com`, `www.wnba.com` | Proxy returned 403. | Not used; other sources cited instead. |
| NCAA attendance | Latest PDF is the 2025–26 season ("through 2025-26"). Schools mapped to metros by main-campus county (`data/manual/ncaa_school_county.csv`). Schools not listed there count as 0 for their metro. | Mapping covers D-I schools in the study metros only. |
| G League presence | G League teams are mostly NBA-owned affiliates near their parent club, which biased Pillar B toward existing NBA markets. | **v2:** removed from the score; kept as descriptive column `has_g_league`. |
| Per-capita local revenue benchmark | No public per-capita benchmark found. | **v2:** replaced by Sportico's reported team revenue by stream (seating and suites, sponsorship, local media share, other), scaled by market size. |

## v2 changes (2026-11-05)

| Item | What changed | Why |
|---|---|---|
| Unit of analysis | **Market = Census Combined Statistical Area (CSA)** when the CBSA is in one, else the CBSA (July 2023 delineations). CBSA factors (metro and micro areas) are aggregated: counts and populations summed, median household income population-weighted (an approximation of the true CSA median), 18-44 share recomputed from counts, GDP summed (missing if any county is unmatched). | San Jose belongs to the Warriors' Bay Area market, and Baltimore to Washington's. 66 markets (61 CSAs). |
| NCAA mapping | Added 46 D-I schools (e.g. Duke, UNC, Michigan, BYU, Kansas) whose counties now fall inside study markets. | CSAs pull in college towns such as Durham, Ann Arbor, Provo and Lawrence. |
| Owner economics | Simple payback replaced by a **20-year NPV** of dilution vs fee share. Grid: growth 0/3/6%, discount 6/8/10%, fee $7B/$8.5B/$10B, shared pool = national TV only ($144M x 30, Sportico) or all central revenue (41% of $13.7B, Sportico), gross or net of the 51% player share. The v1 pool ($76B/11 = $6.9B a year) overstated the 2025-26 national payout, which Sportico reports as $144M per team. | Requested; uses sourced figures. |
| Assumptions | Ticket price, attendance rate, sponsorship per establishment and local media per resident were replaced by Sportico's reported revenue by stream. Remaining placeholders (revenue elasticity, fan multiplier, NPV grid, base fee midpoint) each carry a rationale. | Fewer unsourced inputs. |
| Focus markets | Added `outputs/focus_markets.csv`, `research/focus_markets.md` and `figures/08_focus_markets.png`: Seattle, Las Vegas, Mexico City, Vancouver, Pittsburgh, Louisville and others. Mexico City and Vancouver are **not scored** (no comparable ACS/CBP/BEA data); their sourced facts are in `data/manual/international_markets.csv` (Wikipedia). | Requested. |
| frontofficesports.com | Proxy refused the connection on the v2 re-check, so the Mexico City "looking seriously" quote could not be verified on the page. | Kept with a "not verified on page" note. |
| v1 archive | `outputs/archive/rankings_v1_cbsa.csv` (v1 output) feeds `outputs/top10_change.csv`. | To explain how the top 10 changed. |

## v3 changes (2026-11-05)

| Item | What changed | Why |
|---|---|---|
| Ease of entry | New axis, separate from attractiveness: arena available (17,000+ seats without an NBA tenant; for current NBA markets, their own arena), log miles to the nearest *other* NBA market (cannibalization proxy), and NFL+MLB+NHL teams (negative). **Competition and arena moved out of the attractiveness score**, which is now pillars A-C with equal weights, so the axes don't double-count. | Requested; fixes markets near existing teams (e.g. Raleigh, 138 miles from Charlotte) being scored on attractiveness alone. |
| Market location | Census Gazetteer 2024 publishes CBSA internal points but no CSA file, so each market is placed at the internal point of its largest CBSA. Toronto (Raptors) coordinates come from Wikipedia. Distances are straight-line (haversine), not drive time. | No CSA Gazetteer file found at the expected URL. |
| Sensitivity set | The "ignore competition" weighting no longer applies (competition left the score), so it was replaced by "no college" (Pillar B without NCAA attendance). | Competition is now on the ease axis. |
| Transplant share | ACS 2020-24 table B05002 (place of birth): 1 − born in state of residence ÷ total. **Descriptive only, not scored** (its sign is ambiguous). In markets that cross state lines (e.g. Cincinnati, Kansas City), people born in the neighbouring part of the same market count as transplants, which inflates the share. | Requested behavioural lens. |
| Honeymoon curve | **Skipped; no figure.** ESPN NHL attendance URLs redirect to the NHL home page (no table), so the Golden Knights and Kraken could not be sourced. ESPN shows "--" for the Raptors and Grizzlies 1995-96 to 2000-01. Only 2 teams were sourceable (Bobcats: 7 of 8 seasons; Thunder: 4 of 8), below the 3-team minimum. The partial sourced data is kept in `data/manual/expansion_attendance.csv`. ESPN labels past seasons by current franchise name (Bobcats = "Hornets"). | Rule: fewer than 3 teams → skip and log. Wikipedia season pages or Hockey-Reference could be tried next. |

## v4 changes (2026-11-05)

| Item | What changed | Why |
|---|---|---|
| Realignment travel | `src/realignment.py`: straight-line round trips to every conference opponent. Arena coordinates come from the Wikipedia NBA team table. Seattle and Las Vegas use their Census Gazetteer market points (no arena yet). **Simplified proxy**: ignores the real schedule, inter-conference games, chained road trips and back-to-backs. | Requested operations lens. |
| Bidder landscape | `research/bidder_landscape.csv` from ESPN (2026-10-02), verified on the page; the Mexico City row comes from a search result (frontofficesports.com blocked). | Requested. |
| Seattle bidder multiple | Uses ESPN's reported ~$6B Seattle valuation estimate instead of the $8.5B base fee. | A market-specific price is reported. |
| Honeymoon curve | **Now included** from Wikipedia season game logs: Golden Knights (7 of 8 seasons; 2020-21 excluded with only 14 home games parsed, pandemic limits), Kraken (5), Raptors (8). Vancouver Grizzlies pages had no parseable home attendance, so they are excluded. Measured as average home attendance **indexed to season 1**, not % of capacity, because capacities changed (Raptors in the SkyDome). Data: `data/manual/expansion_attendance_wiki.csv`. | ≥3 teams sourced. |

## v5 changes (2026-11-05): San Juan and Mexico City

| Item | What changed | Why / caveat |
|---|---|---|
| San Juan, PR | Back in `metros.csv` as the San Juan-Bayamón CSA, flagged `partial_data`. Sources: ACS 2020-24 (population, income, age, place of birth), Census PR population estimates (`prc-cbsa-est2025.csv`), Census Gazetteer location, and the Coliseo de Puerto Rico (19,500 seats, Wikipedia) in `data/manual/arenas_supplement.csv`. **No CBP or BEA data exists for Puerto Rico**, so Pillar C and GDP are missing. Transplant share counts Puerto Rico-born residents (ACS B05002_010) as local, because B05002_003 is 0 in PR. | Requested. |
| Partial scoring method | San Juan and Mexico City are standardized against the **complete U.S. markets' means and SDs**, so U.S. scores, ranks, Monte Carlo and validity are unchanged (verified identical). Each pillar averages its available factors and the total averages the available pillars. "Would rank" = position if inserted into the non-NBA ranking. Output: `outputs/partial_markets.csv`. | Keeps the U.S. analysis comparable. |
| Mexico City factors | Population 21.4M (2020, Wikipedia/INEGI census). GDP **US$401.3B nominal, 2024** (Wikipedia infobox: MXN 8.13 trillion, implied ~20.26 MXN/USD). **PPP not used**: the World Bank and OECD APIs are blocked by the proxy and no sourced PPP metro figure was found. Nominal USD is also the basis of BEA's U.S. GDP. WNBA presence 0; NFL/MLB/NHL teams 0 (Liga MX soccer not counted); Arena CDMX 22,300 seats (arena available); distance to the nearest NBA market from Wikipedia coordinates. Not comparable or not sourced: income, age share, growth, NCAA, corporate base, transplant share. | Partial: A uses 2 of 5 factors, B 1 of 2, C none. Its high score comes from size alone. |
| NBA games in Mexico City | From the Arena CDMX Wikipedia article: Jan 2017 (2), Dec 2018 (1), 2019-20 (2 scheduled). Not verified against NBA records; the "NBA Mexico City Game(s)" articles do not exist. | Descriptive only. |
| World Bank, OECD | `api.worldbank.org` and `sdmx.oecd.org` blocked (connection refused). | Allowlist them to add PPP figures. |

## v5 cleanup (2026-11-05)

| Item | What changed |
|---|---|
| Refactor | Code simplified and comments trimmed. Outputs were verified identical to a pre-refactor snapshot (all CSV, MD and PNG files; only runtime and test-timing lines differ). |
| Rules file | `CLAUDE.md` renamed to `PROJECT_RULES.md`, rewritten in first person. |
| Honeymoon caveat | Attendance is capped by capacity, so flat lines (Golden Knights, Kraken) mean sellouts, not flat demand. Noted in the figure, README and KEY_NUMBERS. |
| Price labels | `bidder_multiples.csv` gains `price_type`: Las Vegas = reported expected sale price (bid), Seattle = reported valuation estimate (not a bid), others = assumed fee. Not strictly comparable. |
| Focus-markets bug | `focus_markets.csv` wrongly listed every market in `international_markets.csv` (Toronto, San Juan) as an unscored focus market with no population, which showed as a missing-number placeholder in the README. Now limited to Mexico City and Vancouver; San Juan appears in the partial-data table. |


## What Noah must write

- The memo sections in `memo/MEMO.md`, the headline and recommendation in `memo/EXEC_SUMMARY.md`, the stakeholder grid in `memo/stakeholders.md`, and the Recommendation section of the README.
- The "So what" in `memo/HEAD_TO_HEAD.md`, and the memo sections "Realignment: who moves East?", "Bidder landscape" and "Novelty effect".
- The "What this suggests" sections in `research/comparables.md` and `research/focus_markets.md`.
- The `implication` and `confidence` columns in `research/insights.csv`.
- A review of every row labeled "ASSUMPTION – Noah to review" in `data/manual/assumptions.csv`.
- A check of the reported (not league-confirmed) figures in `research/trends.csv` before citing them.
