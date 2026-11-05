# My working rules for this project (nba-expansion-strategy)

1. I never make up data. Every number comes from a cited source (URL and access date) or is labeled "ASSUMPTION – Noah to review" in the assumptions table, with a short rationale.
2. I inspect every dataset before I use it, and I don't assume what columns or codes mean.
3. If a source is unreachable, behind a paid login, forbids automated access, or can't be mapped to markets, I skip it and log the reason in `DEVIATIONS.md`. Census data is essential: if it is blocked, I stop.
4. I report associations and scenarios, not causal claims. The recommendation, implications and risks are mine to write; the generated docs leave those as headings.
5. I never type results into documents by hand. `src/report.py` generates every number from `outputs/`.
6. I use Python only (pandas, numpy, scipy, statsmodels, matplotlib, requests, pytest), with pinned versions in `requirements.txt`. The code is plain and commented so I can explain every step. No notebooks in the pipeline and no machine learning beyond simple statistics.
7. I commit after each piece of work with a clear message. Raw downloads stay in `data/raw/` (not committed). Small sourced tables live in `data/manual/` with a source column.
8. My unit of analysis is the U.S. market: a Census combined statistical area (CSA), or the metro area (CBSA) if it isn't part of one. Markets with incomplete data (San Juan, Mexico City) are scored on what is available and labeled "partial data".

Pipeline: `python run_all.py` rebuilds everything from `data/raw/` and `data/manual/` and runs the tests (`pytest -q`).
