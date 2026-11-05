"""Phase 5: all figures, one consistent matplotlib style. Every figure carries a source line."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from config import OUTPUTS, FIGURES, PROCESSED, REPO_NAME

BLUE, ORANGE, GRAY, DARK = "#2563eb", "#ea580c", "#9ca3af", "#111827"
PILLAR_COLORS = ["#1d4ed8", "#0d9488", "#7c3aed", "#ca8a04"]
PILLAR_LABELS = {"A_size_wealth": "A Size & wealth", "B_basketball_demand": "B Basketball demand",
                 "C_corporate": "C Corporate", "D_competition_infra": "D Competition & arena"}
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
    ax.set_title("Top 15 non-NBA metros by attractiveness score")


def main():
    FIGURES.mkdir(exist_ok=True)
    r = pd.read_csv(OUTPUTS / "rankings.csv", dtype={"cbsa_code": str})
    k = pd.read_csv(OUTPUTS / "kpi_dashboard.csv", dtype={"cbsa_code": str}).sort_values("attractiveness_rank")
    sens = pd.read_csv(OUTPUTS / "sensitivity.csv", dtype={"cbsa_code": str})
    tor = pd.read_csv(OUTPUTS / "tornado.csv")
    dil = pd.read_csv(OUTPUTS / "dilution_payback.csv")
    m = pd.read_csv(PROCESSED / "metros.csv", dtype={"cbsa_code": str})

    # 1 headline
    fig, ax = plt.subplots(figsize=(9, 6.5)); headline(ax, r); source(fig); fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIGURES / "01_headline_top15.png", dpi=150); plt.close(fig)

    # 2 pillar breakdown (grouped bars)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(k)); w = 0.2
    for i, (col, lab) in enumerate(PILLAR_LABELS.items()):
        ax.bar(x + (i - 1.5) * w, k[col], w, label=lab, color=PILLAR_COLORS[i])
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
    fig.colorbar(im, ax=ax, label="rank among non-NBA metros", shrink=0.7)
    source(fig); fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIGURES / "03_sensitivity_heatmap.png", dpi=150); plt.close(fig)

    # 4 population vs income scatter
    top_ids = set(k["cbsa_code"])
    fig, ax = plt.subplots(figsize=(9, 6.5))
    for mask, col, lab in [(m["nba_metro"], GRAY, "Current NBA metro"), (m["cbsa_code"].isin(top_ids), BLUE, "Top-8 candidate"),
                           (~m["nba_metro"] & ~m["cbsa_code"].isin(top_ids), "#d1d5db", "Other metro")]:
        d = m[mask]; ax.scatter(d["population"] / 1e6, d["median_hh_income"] / 1e3, c=col, label=lab, s=40, edgecolor="white")
    for _, d in m[m["cbsa_code"].isin(top_ids) | (m["population"] > 6e6)].iterrows():
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
        "Local rev $M (L/B/H)": [f"{a/1e6:.0f}/{b/1e6:.0f}/{c/1e6:.0f}" for a, b, c in zip(k.est_local_revenue_low, k.est_local_revenue_base, k.est_local_revenue_high)],
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
    source(fig, "Source: data/manual/assumptions.csv (labeled ASSUMPTION – Noah to review) applied to metro data. Orange = low value, blue = high value. " + REPO_NAME)
    fig.tight_layout(rect=(0, 0.05, 1, 1)); fig.savefig(FIGURES / "06_tornado.png", dpi=150); plt.close(fig)

    # 7 dilution vs fee payback
    fig, ax = plt.subplots(figsize=(9, 5.5))
    years = np.arange(0, 51)
    for (_, row), col in zip(dil.iterrows(), [BLUE, DARK, ORANGE]):
        ax.plot(years, row.annual_dilution_per_existing_team * years / 1e6, color=col, label=f"{row.scenario.replace('_', ' ')}: cumulative dilution (breakeven {row.breakeven_years:.0f} yrs)")
        ax.axhline(row.fee_received_per_existing_team / 1e6, color=col, ls=":", lw=1)
    ax.set_xlabel("Years after expansion (no growth, no discounting)"); ax.set_ylabel("$M per existing team")
    ax.set_title("Expansion fee received vs cumulative national-revenue dilution"); ax.legend(frameon=False, fontsize=8)
    source(fig, "Source: reported $76B/11-yr media deal and $7-10B fee range (data/manual/assumptions.csv); dotted lines = one-time fee share (fee x 2 / 30). " + REPO_NAME)
    fig.tight_layout(rect=(0, 0.05, 1, 1)); fig.savefig(FIGURES / "07_dilution_payback.png", dpi=150); plt.close(fig)

    # 8 LinkedIn summary 1200x1500
    fig = plt.figure(figsize=(8, 10), dpi=150)
    fig.text(0.05, 0.955, "Beyond Seattle and Vegas:", fontsize=20, weight="bold")
    fig.text(0.05, 0.92, "which NBA markets are overlooked?", fontsize=20, weight="bold", color=BLUE)
    ax = fig.add_axes([0.25, 0.32, 0.7, 0.55]); headline(ax, r); ax.set_title("")
    over = int(r["overlooked"].sum())
    sea = int(r.loc[r.short_name == "Seattle", "rank_candidates"].iloc[0]); lv = int(r.loc[r.short_name == "Las Vegas", "rank_candidates"].iloc[0])
    be = dil.loc[dil.scenario == "base", "breakeven_years"].iloc[0]
    nums = [(f"{over}", "non-NBA metros score at or above\nthe median current NBA market"),
            (f"#{sea} / #{lv}", "Seattle / Las Vegas rank\namong non-NBA metros"),
            (f"{be:.0f} yrs", "base-case years for national-revenue\ndilution to equal the fee share")]
    for i, (n, lab) in enumerate(nums):
        x0 = 0.05 + i * 0.31
        fig.text(x0, 0.2, n, fontsize=24, weight="bold", color=ORANGE if i == 1 else BLUE)
        fig.text(x0, 0.13, lab, fontsize=9)
    fig.text(0.05, 0.03, "Scorecard of 56 U.S. metros (4 equal-weight pillars). Scenarios, not forecasts.\n" + SRC, fontsize=6.5, color="#4b5563", wrap=True)
    fig.set_size_inches(8, 10); fig.savefig(FIGURES / "linkedin_summary.png", dpi=150); plt.close(fig)
    print("figures written")


if __name__ == "__main__":
    main()
