# Project rules (nba-expansion-strategy)

1. NEVER fabricate data. Every data point comes from a cited source (URL plus access date) or is explicitly labeled "ASSUMPTION – Noah to review" in an assumptions table. No silent estimates or placeholders.
2. Inspect every dataset before using it; never assume columns or codes.
3. If a source is unreachable, needs a paid login, its terms forbid automated access, or it can't be mapped to metros: skip it, log it in `DEVIATIONS.md` with the reason, and continue. If an essential source (Census) is blocked, STOP and tell Noah which domain to allowlist.
4. Associations and scenarios only, no causal claims. No strategic conclusions in prose; recommendation, implication and risk sections are headings for Noah to write.
5. Never type results into docs by hand. Generate numbers from `outputs/` with `src/report.py`.
6. Tools: Python only (pandas, numpy, statsmodels, matplotlib, requests, pytest), pinned in `requirements.txt`. Plain, commented code a student can explain. No notebooks as the pipeline, no ML beyond simple statistics.
7. Commit after every phase with a clear message. Raw downloads go in `data/raw/` (gitignored). Small sourced manual tables live in `data/manual/` (committed, with a source column).
8. Unit of analysis: U.S. metropolitan area (Census CBSA). Canadian metros only if comparable StatCan data is quick to get; otherwise log it as a limitation.

Pipeline: `python run_all.py` (download -> build_metros -> model -> business_case -> research checks -> figures -> report). Tests: `pytest -q`.
