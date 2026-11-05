# Deviations and skipped sources

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
