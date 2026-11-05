"""Expansion 'honeymoon' data: home attendance (% of capacity) for a team's first seasons.

Source: ESPN attendance pages (one page per league-season, all teams). The year in the URL
is the season's ending year. Only values read from those pages are kept; every row stores
its URL. Output: data/manual/expansion_attendance.csv (committed, sourced).
"""
import time
import pandas as pd
import requests
from config import RAW, MANUAL, ACCESS_DATE

# team -> (league, ESPN team label, first season ending year, number of seasons available)
TEAMS = {
    # ESPN labels past seasons by the franchise's CURRENT name: the 2004-05 Bobcats appear as
    # "Hornets" (the then New Orleans Hornets appear as "Pelicans"), checked on the 2005 page.
    "Charlotte Bobcats (NBA, 2004)": ("nba", "Hornets", 2005, 8),
    "Oklahoma City Thunder (NBA, relocated 2008)": ("nba", "Thunder", 2009, 8),
}
# Not available (logged in DEVIATIONS.md): ESPN NHL attendance URLs redirect to the NHL home page
# (no table), and ESPN shows '--' for the Raptors/Grizzlies 1995-96 to 2000-01 seasons.
MIN_TEAMS_FOR_FIGURE = 3
HEADERS = {"User-Agent": "Mozilla/5.0 (nba-expansion-strategy student research)"}


def page(league, year):
    url = f"https://www.espn.com/{league}/attendance/_/year/{year}"
    path = RAW / f"espn_{league}_attendance_{year}.html"
    if not path.exists():
        r = requests.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        path.write_bytes(r.content)
        time.sleep(0.5)
    t = pd.read_html(path)[0]
    t.columns = ["rk", "team", "home_gms", "home_total", "home_avg", "home_pct", "road_gms", "road_avg", "road_pct", "gms", "avg", "pct"]
    return url, t.iloc[2:]  # first two rows are headers (inspected)


def main():
    rows = []
    for team, (league, label, first, n) in TEAMS.items():
        for k in range(n):
            year = first + k
            try:
                url, t = page(league, year)
            except Exception as e:
                print(f"skip {team} {year}: {e}")
                continue
            hit = t[t["team"].astype(str).str.strip() == label]
            if hit.empty:
                print(f"skip {team} {year}: label not found")
                continue
            h = hit.iloc[0]
            if str(h["home_pct"]).strip() in ("--", "", "nan"):
                print(f"skip {team} {year}: no attendance reported ('--', e.g. pandemic season)")
                continue
            rows.append({"team": team, "league": league.upper(), "season_end_year": year, "season_number": k + 1,
                         "home_avg_attendance": int(h["home_avg"]), "home_pct_capacity": float(h["home_pct"]),
                         "espn_label": label, "source_url": url, "access_date": ACCESS_DATE})
    df = pd.DataFrame(rows)
    df.to_csv(MANUAL / "expansion_attendance.csv", index=False)
    print(df.pivot(index="season_number", columns="team", values="home_pct_capacity").to_string())
    return df


if __name__ == "__main__":
    main()
