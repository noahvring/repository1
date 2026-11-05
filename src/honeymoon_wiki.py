"""Honeymoon curve: average regular-season home attendance per season from Wikipedia game logs,
indexed to season 1 (= 100). Seasons with < 20 parsed home games are dropped."""
import re
import time
from io import StringIO
import pandas as pd
import requests
from config import RAW, MANUAL, ACCESS_DATE

W = "https://en.wikipedia.org/wiki/"
# team -> (league, first season start year, seasons, page title template, home-team label in NHL logs)
TEAMS = {
    "Vegas Golden Knights (NHL, 2017)": ("NHL", 2017, 8, "{a}–{b}_Vegas_Golden_Knights_season", "Vegas"),
    "Seattle Kraken (NHL, 2021)": ("NHL", 2021, 5, "{a}–{b}_Seattle_Kraken_season", "Seattle"),
    "Toronto Raptors (NBA, 1995)": ("NBA", 1995, 8, "{a}–{b}_Toronto_Raptors_season", None),
    "Vancouver Grizzlies (NBA, 1995)": ("NBA", 1995, 6, "{a}–{b}_Vancouver_Grizzlies_season", None),
}
MONTHS = ("October", "November", "December", "January", "February", "March", "April")


def fetch(title):
    path = RAW / ("wiki_season_" + re.sub(r"[^A-Za-z0-9_]", "_", title) + ".html")
    if not path.exists():
        r = requests.get(W + title, headers={"User-Agent": "nba-expansion-strategy student research"}, timeout=60)
        if r.status_code != 200:
            return None
        path.write_bytes(r.content)
        time.sleep(0.5)
    return path


def num(x):
    m = re.search(r"(\d{1,3}(?:,\d{3})+|\d{4,6})\s*$", str(x).strip())
    return int(m.group(1).replace(",", "")) if m else None


def home_attendance(path, league, home_label):
    vals = []
    raw = re.sub(r'colspan="(\d+),?"', r'colspan="\1"', path.read_text(errors="ignore"))  # fix malformed colspan="1,"
    try:
        tables = pd.read_html(StringIO(raw))
    except ValueError as e:
        print("parse error", path.name, e)
        return vals
    for t in tables:
        if isinstance(t.columns, pd.MultiIndex):
            head = " ".join(map(str, t.columns.get_level_values(0)))
            t.columns = t.columns.get_level_values(-1)
        else:
            head = ""
        cols = [str(c) for c in t.columns]
        if league == "NHL":
            # regular-season monthly tables only
            if not (any(mo in head for mo in MONTHS) and "Home" in cols and "Attendance" in cols) or "reseason" in head or "layoff" in head:
                continue
            for _, r in t.iterrows():
                if str(r["Home"]).strip() == home_label:
                    v = num(r["Attendance"])
                    if v:
                        vals.append(v)
        else:
            if not ({"Game", "Team", "Location Attendance"} <= set(cols)):
                continue
            for _, r in t.iterrows():
                g = pd.to_numeric(r["Game"], errors="coerce")
                if pd.isna(g) or g > 82 or str(r["Team"]).strip().startswith("@"):
                    continue
                v = num(r["Location Attendance"])
                if v:
                    vals.append(v)
    return vals


def main():
    rows = []
    for team, (league, start, n, tmpl, label) in TEAMS.items():
        for k in range(n):
            a = start + k
            title = tmpl.format(a=a, b="2000" if a == 1999 else str(a + 1)[-2:])  # Wikipedia writes 1999–2000
            path = fetch(title)
            if path is None:
                print("missing page", title)
                continue
            vals = home_attendance(path, league, label)
            if len(vals) < 20:
                print(f"skip {title}: only {len(vals)} home games with attendance")
                continue
            rows.append({"team": team, "league": league, "season": f"{a}-{str(a + 1)[-2:]}", "season_number": k + 1,
                         "home_games_parsed": len(vals), "avg_home_attendance": round(sum(vals) / len(vals)),
                         "source_url": W + title, "access_date": ACCESS_DATE})
    df = pd.DataFrame(rows)
    first = df[df.season_number == 1].set_index("team")["avg_home_attendance"]
    df["index_vs_season1"] = 100 * df["avg_home_attendance"] / df["team"].map(first)
    df.to_csv(MANUAL / "expansion_attendance_wiki.csv", index=False)
    print(df.pivot(index="season_number", columns="team", values="avg_home_attendance").to_string())
    return df


if __name__ == "__main__":
    main()
