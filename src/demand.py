"""Demonstrated demand: NBA and NBA-adjacent events in non-NBA markets (2011-12 onward).

Built from saved Wikipedia pages (URL per row). Not scored: the league picks where it plays,
often in markets it is courting, so these counts are a selection-biased signal.
Outputs: data/manual/nba_games_nonmarket.csv, outputs/demand_summary.csv,
outputs/demand_sensitivity.csv (exploratory bonus-factor run).
"""
import html
import json
import re
from io import StringIO
import numpy as np
import pandas as pd
import requests
from config import RAW, MANUAL, OUTPUTS, PROCESSED, ACCESS_DATE
from model import PILLARS, WEIGHTINGS, pillar_scores, total, rank_candidates

W = "https://en.wikipedia.org/wiki/"
PAGES = ["NBA_Global_Games", "2023_NBA_In-Season_Tournament", "2024_NBA_Cup", "2025_NBA_Cup", "NBA_Summer_League",
         "KFC_Yum!_Center", "Moody_Center", "Benchmark_International_Arena", "Enterprise_Center", "Heritage_Bank_Center"]
START = pd.Timestamp("2011-07-01")  # roughly the last 15 seasons
NR = "not reported"
COLS = ["market", "date_or_season", "event_type", "teams", "venue", "attendance", "sellout", "source_url"]


def page(name):
    path = RAW / "demand" / f"{name}.html"
    if not path.exists() or path.stat().st_size < 10_000:
        path.parent.mkdir(exist_ok=True)
        r = requests.get(W + name, headers={"User-Agent": "nba-expansion-strategy student research"}, timeout=60)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path


def wikitext(s):
    """'[[Mexico City Arena]], [[Mexico City]]' -> 'Mexico City Arena, Mexico City'."""
    s = re.sub(r"\{\{.*?\}\}", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    return re.sub(r"'''|''", "", s).strip()


def boxes(name):
    """Basketball game boxes (template parameters) with their position in the page."""
    t = page(name).read_text(errors="ignore")
    for m in re.finditer(r"data-mw='([^']*)'", t):
        try:
            parts = json.loads(html.unescape(m.group(1))).get("parts", [])
        except json.JSONDecodeError:
            continue
        for p in parts:
            tp = p.get("template") if isinstance(p, dict) else None
            if tp and "asketballbox" in tp["target"]["wt"]:
                yield m.start(), {k: wikitext(v["wt"]) for k, v in tp["params"].items()}, t


def global_games():
    """Preseason and regular-season games in Mexico City and San Juan (section decides the type)."""
    rows = []
    for pos, b, t in boxes("NBA_Global_Games"):
        city = next((c for c in ["Mexico City", "San Juan"] if c in b.get("place", "")), None)
        date = pd.to_datetime(b.get("date"), errors="coerce")
        if city is None or pd.isna(date) or date < START:
            continue
        kind = "NBA regular season (neutral site)" if pos > t.find('id="List_of_regular_season_games"') else "NBA preseason"
        rows.append([city, date.date().isoformat(), kind, f"{b.get('teamA', '')} vs {b.get('teamB', '')}",
                     b["place"].split(",")[0], b.get("attendance") or NR, NR, W + "NBA_Global_Games"])
    return rows


def cup_knockouts():
    """NBA Cup semifinals and final in Las Vegas; the last game on each page is the final."""
    rows = []
    for name in ["2023_NBA_In-Season_Tournament", "2024_NBA_Cup", "2025_NBA_Cup"]:
        games = [b for _, b, _ in boxes(name) if "Las Vegas" in b.get("place", "") or "Paradise" in b.get("place", "")]
        for i, b in enumerate(games):
            rows.append(["Las Vegas", pd.to_datetime(b["date"]).date().isoformat(),
                         "NBA Cup final" if i == len(games) - 1 else "NBA Cup knockout (semifinal)",
                         f"{b.get('team1', '')} vs {b.get('team2', '')}", b["place"].split(",")[0],
                         b.get("attendance", "").replace(",", "") or NR, NR, W + name])
    return rows


def summer_league():
    t = pd.read_html(page("NBA_Summer_League"))[3]
    t = t[t["League"] == "Las Vegas"]
    return [["Las Vegas", str(r.Year), "NBA Summer League (Las Vegas) championship",
             f"{re.sub(r' [(].*', '', r.Champion)} vs {r['Runner-up']}", "UNLV campus", NR, NR, W + "NBA_Summer_League"]
            for _, r in t.iterrows()]


def louisville_preseason():
    t = next(x for x in pd.read_html(page("KFC_Yum!_Center")) if "Home team" in map(str, x.columns))
    return [["Louisville", pd.to_datetime(r.Date).date().isoformat(), "NBA preseason", f"{r['Home team']} vs {r['Away team']}",
             "KFC Yum! Center", str(r.Attendance), NR, W + "KFC_Yum!_Center"] for _, r in t.iterrows()]


def seattle_preseason():
    """Clippers preseason games at Climate Pledge Arena, from the team's season game logs."""
    rows = []
    for start in range(2022, 2026):
        name = f"{start}–{str(start + 1)[-2:]}_Los_Angeles_Clippers_season"
        raw = re.sub(r'colspan="(\d+),?"', r'colspan="\1"', page(name).read_text(errors="ignore"))
        for t in pd.read_html(StringIO(raw)):
            if isinstance(t.columns, pd.MultiIndex):
                t.columns = t.columns.get_level_values(-1)
            if "Location Attendance" not in t.columns or "Game" not in t.columns:
                continue
            for _, r in t[t["Location Attendance"].astype(str).str.contains("Climate Pledge")].iterrows():
                date = pd.to_datetime(f"{r.Date} {start}", errors="coerce")
                rows.append(["Seattle", date.date().isoformat(), "NBA preseason", f"Los Angeles Clippers vs {r.Team}",
                             "Climate Pledge Arena", r["Location Attendance"].split()[-1].replace(",", ""), NR, W + name])
    return rows


def text_rows():
    """Events stated in arena articles (sentences checked on the saved pages)."""
    moody, tampa = W + "Moody_Center", W + "Benchmark_International_Arena"
    spurs = [("2023-04-06", "Portland Trail Blazers"), ("2023-04-08", "Minnesota Timberwolves"), ("2024-03-15", "Denver Nuggets"),
             ("2024-03-17", "Brooklyn Nets"), ("2025-02-20", "Phoenix Suns"), ("2025-02-21", "Detroit Pistons"),
             ("2026-02-19", "Phoenix Suns"), ("2026-02-21", "Sacramento Kings"), ("2026-10-23", "Houston Rockets")]
    rows = [["Austin", d, "NBA regular season (team home game away from home market)", f"San Antonio Spurs vs {opp}", "Moody Center",
             "16223" if d == "2024-03-15" else NR, NR, moody] for d, opp in spurs]
    rows += [["Tampa", "2020-21", "NBA regular season (temporary home, pandemic)", "Toronto Raptors home games", "Amalie Arena", NR, NR, tampa],
             ["St. Louis", "2014-10-24", "NBA preseason", "Chicago Bulls vs Minnesota Timberwolves", "Scottrade Center (now Enterprise Center)", NR, NR, W + "Enterprise_Center"],
             ["Cincinnati", "2013-14", "NBA preseason", "Cleveland Cavaliers (preseason games)", "U.S. Bank Arena (now Heritage Bank Center)", NR, NR, W + "Heritage_Bank_Center"]]
    return rows


def g_league_rows(markets):
    """Current G League teams in non-NBA markets (teams.csv, Wikipedia)."""
    t = pd.read_csv(MANUAL / "teams.csv", dtype=str)
    t = t[t.league == "G League"]
    cmap = pd.read_csv(PROCESSED / "cbsa_factors.csv", dtype={"cbsa_code": str}).set_index("cbsa_code")["market_id"]
    t["market_id"] = t["cbsa_code"].map(cmap)
    names = markets.set_index("market_id")["short_name"]
    rows = [[names[r.market_id], "2025-26", "G League team", r.team, NR, NR, NR, r.source_url]
            for r in t.itertuples() if r.market_id in names.index]
    rows += [["Mexico City", "2025-26", "G League team", r.team, "Mexico City Arena", NR, NR, r.source_url]
             for r in t.itertuples() if str(r.location).startswith("Mexico City")]
    return rows


def capacities():
    a = pd.read_csv(MANUAL / "arenas.csv").set_index("arena")["capacity_basketball"].to_dict()
    intl = pd.read_csv(MANUAL / "international_markets.csv")
    mx = float(intl[(intl.market == "Mexico City") & (intl.item == "largest_arena_capacity")].value.iloc[0])
    return a | {"Mexico City Arena": mx}


def main():
    m = pd.read_csv(PROCESSED / "metros.csv")
    non_nba = m[~m["nba_metro"]]
    rows = (global_games() + cup_knockouts() + summer_league() + louisville_preseason() + seattle_preseason()
            + text_rows() + g_league_rows(non_nba))
    ev = pd.DataFrame(rows, columns=COLS)
    ev = ev[~(ev["date_or_season"].str.len().eq(10) & (ev["date_or_season"] > ACCESS_DATE))]  # drop scheduled games
    ev["access_date"] = ACCESS_DATE
    ev.to_csv(MANUAL / "nba_games_nonmarket.csv", index=False)

    # per-market summary; % of capacity only where the venue's capacity is sourced
    ev["att"] = pd.to_numeric(ev["attendance"], errors="coerce")
    ev["pct_capacity"] = ev["att"] / ev["venue"].map(capacities())
    ev["year"] = ev["date_or_season"].str[:4].astype(int)
    games = ev[ev.event_type != "G League team"]
    s = ev.groupby("market").agg(events=("event_type", "size"), event_types=("event_type", lambda x: "; ".join(sorted(set(x)))),
                                 latest_year=("year", "max"))
    s["nba_games"] = games.groupby("market").size()
    s["games_with_attendance"] = games.groupby("market")["att"].count()
    s["avg_attendance"] = games.groupby("market")["att"].mean()
    s["avg_pct_capacity"] = games.groupby("market")["pct_capacity"].mean()
    s["sellouts_reported"] = (games["sellout"] == "Y").groupby(games["market"]).sum()
    s = s.fillna({"nba_games": 0, "games_with_attendance": 0}).astype({"nba_games": int, "games_with_attendance": int})
    s.sort_values("events", ascending=False).to_csv(OUTPUTS / "demand_summary.csv")

    # exploratory: NBA games (log 1+n) as a bonus factor in Pillar B; NBA markets count 0 by construction
    df = m[~m["partial_data"]].set_index("market_id")
    df["demand_games"] = df["short_name"].map(s["nba_games"]).fillna(0)
    df["log_demand_games"] = np.log1p(df["demand_games"])
    bonus = PILLARS | {"B_basketball_demand": PILLARS["B_basketball_demand"] + [("log_demand_games", None, 1)]}
    base = rank_candidates(df, total(pillar_scores(df)[0], WEIGHTINGS["equal"]))
    alt = rank_candidates(df, total(pillar_scores(df, bonus)[0], WEIGHTINGS["equal"]))
    out = pd.DataFrame({"short_name": df.loc[base.index, "short_name"], "nba_games": df.loc[base.index, "demand_games"],
                        "rank_base": base, "rank_with_demand_bonus": alt, "rank_change": alt - base})
    out["note"] = ("EXPLORATORY: selection-biased signal (the league chooses where to play); a third Pillar-B factor "
                   "also dilutes the other two, so markets with 0 games can move")
    out.sort_values("rank_base").to_csv(OUTPUTS / "demand_sensitivity.csv")
    print(s.to_string())
    return ev, s


if __name__ == "__main__":
    main()
