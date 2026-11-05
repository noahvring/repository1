"""Phase 5: all figures, one consistent matplotlib style. Every figure carries a source line."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from config import OUTPUTS, FIGURES, PROCESSED, REPO_NAME

BLUE, ORANGE, GRAY, DARK = "#2563eb", "#ea580c", "#9ca3af", "#111827"
PILLAR_COLORS = ["#1d4ed8", "#0d9488", "#7c3aed"]
PILLAR_LABELS = {"A_size_wealth": "A Size & wealth", "B_basketball_demand": "B Basketball demand",
                 "C_corporate": "C Corporate"}
SRC = "Source: Census ACS 2020-24, Census PEP V2025, BEA 2024, Census CBP 2023, NCAA 2025-26, Wikipedia team/arena lists. Analysis: " + REPO_NAME
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlesize": 13, "figure.dpi": 100})


def source(fig, text=SRC):
    fig.text(0.01, 0.01, text, fontsize=7, color="#4b5563", ha="left", va="bottom", wrap=True)


def headline(ax, r):
    c = r[~r["nba_metro"]].sort_values("total_score", ascending=False).head(15).iloc[::-1]
    med = r["median_nba_score"].iloc[0]
    colors = [ORANGE if n in ("Seattle", "Las Vegas") else BLUE for n in c["short_name"]]
    ax.barh(c["short_name"], c["total_score"], color=colors)
    ax.axvline(med, color=DARK, ls="--", lw=1)
    ax.text(med, len(c) - 0.4, f" median current NBA market ({med:.2f})", fontsize=8, va="bottom")
    ax.set_xlabel("Attractiveness score (mean of pillar z-scores)")
    ax.set_title("Top 15 non-NBA markets by attractiveness score")


def matrix(ax, r, small=False):
    """Attractiveness (y) vs ease of entry (x); dividing lines at the current-NBA-market medians."""
    a_med, e_med = r["median_nba_score"].iloc[0], r["ease_median_nba"].iloc[0]
    nba, c = r[r["nba_metro"]], r[~r["nba_metro"]]
    ax.scatter(nba["ease_of_entry"], nba["total_score"], s=18, c="#e5e7eb", edgecolor=GRAY, lw=0.5, label="Current NBA market", zorder=1)
    size = (c["population"] / 1e6) * (40 if small else 60)
    cols = [ORANGE if n in ("Seattle", "Las Vegas") else BLUE for n in c["short_name"]]
    ax.scatter(c["ease_of_entry"], c["total_score"], s=size, c=cols, alpha=0.75, edgecolor="white", lw=0.8, zorder=2)
    ax.axvline(e_med, color=DARK, lw=0.8, ls="--"); ax.axhline(a_med, color=DARK, lw=0.8, ls="--")
    top = set(c.sort_values("total_score", ascending=False).head(12)["short_name"]) | {"Seattle", "Las Vegas", "Pittsburgh", "Louisville", "Kansas City", "St. Louis"}
    for _, d in c[c["short_name"].isin(top)].iterrows():
        ax.annotate(d["short_name"], (d["ease_of_entry"], d["total_score"]), fontsize=7 if small else 8, xytext=(4, 3), textcoords="offset points",
                    weight="bold" if d["short_name"] in ("Seattle", "Las Vegas") else "normal")
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    kw = dict(fontsize=9 if small else 11, weight="bold", color="#374151", alpha=0.9)
    ax.text(x1, y1, "Prime targets", ha="right", va="top", **kw); ax.text(x0, y1, "Attractive but hard to enter", ha="left", va="top", **kw)
    ax.text(x1, y0, "Easy but small", ha="right", va="bottom", **kw); ax.text(x0, y0, "Deprioritize", ha="left", va="bottom", **kw)
    ax.set_xlabel("Ease of entry (arena available, distance to nearest NBA market, fewer big-league rivals)")
    ax.set_ylabel("Attractiveness (size & wealth, basketball demand, corporate base)")


def main():
    FIGURES.mkdir(exist_ok=True)
    r = pd.read_csv(OUTPUTS / "rankings.csv", dtype={"market_id": str})
    k = pd.read_csv(OUTPUTS / "kpi_dashboard.csv", dtype={"market_id": str}).sort_values("attractiveness_rank")
    sens = pd.read_csv(OUTPUTS / "sensitivity.csv", dtype={"market_id": str})
    tor = pd.read_csv(OUTPUTS / "tornado.csv")
    npv = pd.read_csv(OUTPUTS / "owner_npv.csv")
    beg = pd.read_csv(OUTPUTS / "owner_breakeven_growth.csv")
    focus = pd.read_csv(OUTPUTS / "focus_markets.csv")
    m = pd.read_csv(PROCESSED / "metros.csv", dtype={"market_id": str})

    # 0 headline matrix
    fig, ax = plt.subplots(figsize=(10, 7.5)); matrix(ax, r)
    ax.set_title("Where should the NBA expand? Attractiveness vs ease of entry")
    fig.text(0.01, 0.035, "Bubble size = population. Dashed lines = median current NBA market. Orange = Seattle, Las Vegas. Grey = current NBA markets.", fontsize=8)
    source(fig); fig.tight_layout(rect=(0, 0.06, 1, 1)); fig.savefig(FIGURES / "00_matrix_attractiveness_vs_ease.png", dpi=150); plt.close(fig)

    # 0b Monte Carlo robustness: P(top 10) with median rank and 90% interval
    mc = pd.read_csv(OUTPUTS / "monte_carlo.csv").head(15).iloc[::-1]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 6.5), sharey=True, gridspec_kw={"width_ratios": [1.2, 1]})
    cols = [ORANGE if n in ("Seattle", "Las Vegas") else BLUE for n in mc["short_name"]]
    a1.barh(mc["short_name"], mc["p_top10"], color=cols); a1.set_xlim(0, 1)
    for y, v in enumerate(mc["p_top10"]):
        a1.text(v + 0.01, y, f"{v:.0%}", va="center", fontsize=8)
    a1.set_xlabel("Probability of ranking in the top 10"); a1.set_title("P(top 10)")
    a2.hlines(range(len(mc)), mc["rank_p05"], mc["rank_p95"], color=GRAY, lw=3)
    a2.scatter(mc["median_rank"], range(len(mc)), color=cols, zorder=3)
    a2.invert_xaxis(); a2.set_xlabel("Rank (median, 90% interval)"); a2.set_title("Rank range")
    fig.suptitle("How robust is the ranking? 10,000 random pillar weightings", weight="bold", fontsize=13)
    source(fig, "Weights ~ Dirichlet(1,1,1), seed 42, over pillars A-C; ranks among non-NBA markets. outputs/monte_carlo.csv. " + SRC)
    fig.tight_layout(rect=(0, 0.05, 1, 1)); fig.savefig(FIGURES / "09_monte_carlo_robustness.png", dpi=150); plt.close(fig)

    # 1 headline
    fig, ax = plt.subplots(figsize=(9, 6.5)); headline(ax, r); source(fig); fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIGURES / "01_headline_top15.png", dpi=150); plt.close(fig)

    # 2 pillar breakdown (grouped bars)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(k)); w = 0.2
    for i, (col, lab) in enumerate(PILLAR_LABELS.items()):
        ax.bar(x + (i - 1) * 0.26, k[col], 0.26, label=lab, color=PILLAR_COLORS[i])
    ax.axhline(0, color=DARK, lw=0.8); ax.set_xticks(x, k["short_name"], rotation=20)
    ax.set_ylabel("Pillar score (z)"); ax.set_title("Pillar scores for the top 8 candidate markets"); ax.legend(ncol=4, fontsize=8, frameon=False)
    source(fig); fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIGURES / "02_pillar_breakdown_top8.png", dpi=150); plt.close(fig)

    # 3 sensitivity heatmap (top 15 by equal weights)
    s = sens.sort_values("rank_equal").head(15)
    cols = [c for c in s.columns if c.startswith("rank_")]
    data = s[cols].to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(9, 7))
    im = ax.imshow(np.where(np.isnan(data), np.nan, data), cmap="Blues_r", aspect="auto", vmin=1, vmax=29)
    ax.set_xticks(range(len(cols)), [c.replace("rank_", "").replace("_", "\n") for c in cols], fontsize=8)
    ax.set_yticks(range(len(s)), s["short_name"])
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            ax.text(j, i, "–" if np.isnan(v) else int(v), ha="center", va="center", fontsize=8, color="white" if (not np.isnan(v) and v < 10) else DARK)
    ax.set_title("Candidate rank under six weightings (– = not arena-ready)")
    fig.colorbar(im, ax=ax, label="rank among non-NBA markets", shrink=0.7)
    source(fig); fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIGURES / "03_sensitivity_heatmap.png", dpi=150); plt.close(fig)

    # 4 population vs income scatter
    top_ids = set(k["market_id"])
    fig, ax = plt.subplots(figsize=(9, 6.5))
    for mask, col, lab in [(m["nba_metro"], GRAY, "Current NBA market"), (m["market_id"].isin(top_ids), BLUE, "Top-8 candidate"),
                           (~m["nba_metro"] & ~m["market_id"].isin(top_ids), "#d1d5db", "Other market")]:
        d = m[mask]; ax.scatter(d["population"] / 1e6, d["median_hh_income"] / 1e3, c=col, label=lab, s=40, edgecolor="white")
    for _, d in m[m["market_id"].isin(top_ids) | (m["population"] > 6e6)].iterrows():
        ax.annotate(d["short_name"], (d["population"] / 1e6, d["median_hh_income"] / 1e3), fontsize=7, xytext=(3, 3), textcoords="offset points")
    ax.set_xscale("log"); ax.set_xlabel("Population, millions (log scale)"); ax.set_ylabel("Median household income ($000)")
    ax.set_title("Market size vs income"); ax.legend(frameon=False, fontsize=8)
    source(fig); fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIGURES / "04_population_vs_income.png", dpi=150); plt.close(fig)

    # 5 KPI table image
    t = pd.DataFrame({
        "Metro": k["short_name"], "Rank": k["attractiveness_rank"].astype(int), "Score": k["total_score"].round(2),
        "Top-10 freq (of 6)": k["top10_frequency"].astype(int), "Pop (M)": (k["population"] / 1e6).round(2),
        "Income ($k)": (k["median_hh_income"] / 1e3).round(0).astype(int), "Growth 20-25": (k["pop_growth_2020_2025"] * 100).round(1).astype(str) + "%",
        "500+ est/100k": k["large_est_per_100k"].round(1), "Fan index": k["fan_interest_index"].round(2),
        "Competing teams": k["competing_teams"].astype(int), "Arena ready": k["arena_ready"],
        "Local rev $M (min/base/max)": [f"{a/1e6:.0f}/{b/1e6:.0f}/{c/1e6:.0f}" for a, b, c in zip(k.est_local_revenue_low, k.est_local_revenue_base, k.est_local_revenue_high)],
    })
    fig, ax = plt.subplots(figsize=(14, 3.8)); ax.axis("off")
    tb = ax.table(cellText=t.values, colLabels=t.columns, loc="center", cellLoc="center"); tb.auto_set_font_size(False); tb.set_fontsize(8); tb.scale(1, 1.5)
    for (i, j), cell in tb.get_celld().items():
        if i == 0: cell.set_facecolor("#e5e7eb"); cell.set_text_props(weight="bold")
    ax.set_title("KPI dashboard: top 8 candidate markets (revenue = scenario estimates from labeled assumptions)")
    source(fig); fig.savefig(FIGURES / "05_kpi_dashboard.png", dpi=150, bbox_inches="tight"); plt.close(fig)

    # 6 tornado
    tt = tor.sort_values("swing")
    base = tt["base_total"].iloc[0] / 1e6
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, (_, row) in enumerate(tt.iterrows()):
        lo, hi = row.total_at_low / 1e6, row.total_at_high / 1e6
        ax.barh(i, hi - base, left=base, color=BLUE); ax.barh(i, lo - base, left=base, color=ORANGE)
    ax.set_yticks(range(len(tt)), tt["assumption"].str.replace("_", " ")); ax.axvline(base, color=DARK, lw=1)
    ax.set_xlabel("Base-case local revenue, top 8 combined ($M/yr)"); ax.set_title("Which assumptions move local revenue most")
    source(fig, "Source: Sportico revenue splits + labeled elasticity assumptions (data/manual/assumptions.csv). Orange = low value, blue = high value. " + REPO_NAME)
    fig.tight_layout(rect=(0, 0.05, 1, 1)); fig.savefig(FIGURES / "06_tornado.png", dpi=150); plt.close(fig)

    # 7 owner NPV heatmap: growth x discount -> fee share minus NPV of 20-year dilution
    b = npv[(npv.pool_definition == "all_central_revenue") & (npv.owner_share == "gross") & (npv.fee_scenario == "base")]
    grid = b.pivot(index="media_growth", columns="discount_rate", values="npv_net_of_fee") / 1e6
    fig, ax = plt.subplots(figsize=(8, 5.5))
    im = ax.imshow(grid.values, cmap="Blues", aspect="auto", origin="lower")
    ax.set_xticks(range(grid.shape[1]), [f"{c:.0%}" for c in grid.columns]); ax.set_yticks(range(grid.shape[0]), [f"{g:.0%}" for g in grid.index])
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            ax.text(j, i, f"+${grid.values[i, j]:,.0f}M" if grid.values[i, j] >= 0 else f"-${-grid.values[i, j]:,.0f}M", ha="center", va="center", fontsize=10, color=DARK)
    ax.set_xlabel("Discount rate"); ax.set_ylabel("Annual growth in shared league revenue")
    ax.set_title("Owner view: fee share minus 20-year NPV of dilution\n(base fee, all central revenue, per existing team)")
    fig.colorbar(im, ax=ax, label="$M per existing team", shrink=0.8)
    source(fig, "Source: Sportico (central revenue 41% of USD 13.7B team revenue, 2025-26); reported USD 7-10B fee range; growth/discount grid = scenarios. outputs/owner_npv.csv. " + REPO_NAME)
    fig.tight_layout(rect=(0, 0.05, 1, 1)); fig.savefig(FIGURES / "07_owner_npv_heatmap.png", dpi=150); plt.close(fig)

    # 8b focus markets: league front-runners and markets to watch
    fs = focus[focus["scored"] == "Y"].copy()
    fs = fs[fs["nba_metro"] != True].sort_values("total_score")
    med = r["median_nba_score"].iloc[0]
    fig, ax = plt.subplots(figsize=(9, 6.5))
    cols = [ORANGE if n in ("Seattle", "Las Vegas") else BLUE for n in fs["short_name"]]
    ax.barh([f"{n} (#{int(k)})" for n, k in zip(fs["short_name"], fs["attractiveness_rank"])], fs["total_score"], color=cols)
    ax.axvline(med, color=DARK, ls="--", lw=1); ax.text(med, len(fs) - 0.4, f" median NBA market ({med:.2f})", fontsize=8)
    intl = focus[focus["scored"] != "Y"]
    note = "Not scored (outside U.S. data): " + "; ".join(f"{n}, pop. {p/1e6:.1f}M" for n, p in zip(intl["short_name"], intl["population"]))
    ax.set_title("Focus markets: attractiveness score (rank among non-NBA markets)")
    ax.set_xlabel("Attractiveness score"); fig.text(0.01, 0.045, note + " - see data/manual/international_markets.csv", fontsize=8)
    source(fig); fig.tight_layout(rect=(0, 0.08, 1, 1)); fig.savefig(FIGURES / "08_focus_markets.png", dpi=150); plt.close(fig)

    # 8 LinkedIn summary 1200x1500, matrix as centrepiece
    mc = pd.read_csv(OUTPUTS / "monte_carlo.csv").set_index("short_name")
    fig = plt.figure(figsize=(8, 10), dpi=150)
    fig.text(0.05, 0.955, "Beyond Seattle and Vegas:", fontsize=20, weight="bold")
    fig.text(0.05, 0.918, "where should the NBA expand next?", fontsize=20, weight="bold", color=BLUE)
    ax = fig.add_axes([0.11, 0.33, 0.85, 0.55]); matrix(ax, r, small=True)
    ax.set_xlabel("Ease of entry", fontsize=9); ax.set_ylabel("Attractiveness", fontsize=9)
    prime = r[(~r["nba_metro"]) & (r["quadrant"] == "Prime targets")]["short_name"].tolist()
    be = beg.loc[(beg.discount_rate == 0.08) & (beg.fee_scenario == "base"), "breakeven_growth"].iloc[0]
    nums = [(f"{mc.at['Seattle', 'p_top10']:.0%} / {mc.at['Las Vegas', 'p_top10']:.0%}", "Seattle / Las Vegas chance of a\ntop-10 rank (10,000 weightings)"),
            (f"{len(prime)}", "'prime target' markets:\n" + ", ".join(prime)),
            (f"{be:.0%}", "shared-revenue growth per year\nneeded for dilution to outweigh\nthe fee (8% discount rate)")]
    for i, (n, lab) in enumerate(nums):
        x0 = 0.05 + i * 0.31
        fig.text(x0, 0.215, n, fontsize=22, weight="bold", color=ORANGE if i == 0 else BLUE)
        fig.text(x0, 0.13, lab, fontsize=8.5)
    fig.text(0.05, 0.03, f"{len(m)} U.S. markets (Census combined statistical areas). Bubble = population; dashed = median NBA market. Scenarios, not forecasts.\n" + SRC, fontsize=6.5, color="#4b5563", wrap=True)
    fig.savefig(FIGURES / "linkedin_summary.png", dpi=150); plt.close(fig)
    print("figures written")


if __name__ == "__main__":
    main()
