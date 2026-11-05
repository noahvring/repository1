# Deviations and skipped sources

All access attempts on 2026-11-05.

| Item | What happened | Action |
|---|---|---|
| Census API (`api.census.gov`) | Returns "Missing Key" for every request (a key is now required). | Used the keyless ACS 2020–2024 5-year **summary files** on `www2.census.gov` instead (same data, bulk download). Population growth uses Vintage 2025 population estimates. |
| Census API first attempt | Network policy blocked all data domains at session start. | Noah allowlisted the domains; work resumed. |
| BEA metro GDP | No key-free metro API. Used BEA county GDP file `CAGDP1.zip` (current-dollar GDP, 2024) summed to CBSA with Census 2023 county delineations. Virginia independent cities that BEA combines with counties were matched by name. | Virginia Beach-Chesapeake-Norfolk GDP stays missing (combination areas could not all be matched). |
| NTTO overseas visitors (`trade.gov`) | City/MSA data is only published in an interactive Power BI dashboard (`powerbi.trade.gov`); no downloadable file link found. | Skipped. Pillar C uses County Business Patterns only. |
| Google Trends | `data/manual/google_trends/` is empty. | Skipped and logged; no DMA→CBSA crosswalk was built (nothing to map). |
| Canada (StatCan) | Not attempted, to protect the time budget; comparable ACS/CBP/BEA measures would need a separate crosswalk. | Toronto Raptors are mapped to `CAN-Toronto` and excluded from the U.S. benchmark. Vancouver and Montreal are a limitation. |
| Puerto Rico (San Juan CBSA) | Over 1M people but missing from CBP/BEA metro files. | Excluded from the study set. |
| `www.nba.com`, `apnews.com`, `www.wnba.com` | Proxy returned 403. | Not used; other sources cited instead. |
| NCAA attendance | Latest PDF is the 2025–26 season ("through 2025-26"). Schools mapped to metros by main-campus county (`data/manual/ncaa_school_county.csv`). Schools not listed there count as 0 for their metro. | Mapping covers D-I schools in the study metros only. |
| G League presence | G League teams are NBA affiliates, so presence partly reflects existing NBA teams. | Kept as a factor as specified; flagged in Limitations. |
| Per-capita local revenue benchmark | No public, sourced benchmark found. | Row kept in assumptions.csv as NOT SOURCED and not used. |
