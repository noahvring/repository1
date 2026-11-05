"""Operations lens: intra-conference travel under realignment options.

SIMPLIFIED PROXY. Each team makes one round trip to every conference opponent; distance is
straight-line (great-circle) between arenas. It ignores the real schedule (which also has
inter-conference games), road trips that chain cities, and back-to-backs.

Arena locations: Wikipedia NBA current-teams table (Coordinates column, decimal part).
Seattle and Las Vegas: the Census Gazetteer internal point of each market's largest CBSA
(no NBA arena exists yet), taken from data/processed/metros.csv.
"""
import re
import numpy as np
import pandas as pd
from config import RAW, SOURCES, PROCESSED, OUTPUTS
from build_metros import haversine_miles


def nba_arenas():
    t = pd.read_html(RAW / SOURCES["wiki_nba"][1])[1]
    rows = []
    for _, r in t.iterrows():
        m = re.search(r"([\d.]+)°N\s+([\d.]+)°W", str(r["Coordinates"]).split("/")[-1])
        rows.append({"team": re.sub(r"\[.*?\]", "", r["Team"]).strip(), "conference": "East" if r["Conference"].startswith("Eastern") else "West",
                     "lat": float(m.group(1)), "lon": -float(m.group(2)), "location_source": SOURCES["wiki_nba"][0]})
    return pd.DataFrame(rows)


def conference_travel(teams):
    """Total miles if every team makes one round trip to every conference opponent."""
    out = {}
    for conf, g in teams.groupby("conference"):
        lat, lon = g["lat"].to_numpy(), g["lon"].to_numpy()
        d = haversine_miles(lat[:, None], lon[:, None], lat[None, :], lon[None, :])
        per_team = 2 * d.sum(axis=1)                       # round trip to each opponent
        out[conf] = (per_team.sum(), dict(zip(g["team"], per_team)))
    return out


def main():
    a = nba_arenas()
    m = pd.read_csv(PROCESSED / "metros.csv").set_index("short_name")
    new = pd.DataFrame([{"team": f"{n} expansion team", "conference": "West", "lat": m.at[n, "lat"], "lon": m.at[n, "lon"],
                         "location_source": "Census Gazetteer 2024 internal point (market proxy; no arena yet)"} for n in ["Seattle", "Las Vegas"]])
    options = {"Current 30 teams": a}
    for mover in ["Memphis Grizzlies", "Minnesota Timberwolves", "New Orleans Pelicans", "Oklahoma City Thunder"]:
        t = pd.concat([a, new], ignore_index=True)
        t.loc[t.team == mover, "conference"] = "East"
        options[f"32 teams: {mover.split()[-1]} move East"] = t
    rows = []
    for name, t in options.items():
        tr = conference_travel(t)
        n = t.groupby("conference").size()
        mover = next((x for x in t.team if "move East" in name and x.split()[-1] in name), None)
        per = {**tr["East"][1], **tr["West"][1]}
        rows.append({"option": name, "teams_east": int(n["East"]), "teams_west": int(n["West"]),
                     "total_miles": tr["East"][0] + tr["West"][0], "east_miles": tr["East"][0], "west_miles": tr["West"][0],
                     "avg_miles_per_team": (tr["East"][0] + tr["West"][0]) / len(t),
                     "east_avg_per_team": tr["East"][0] / n["East"], "west_avg_per_team": tr["West"][0] / n["West"],
                     "moved_team": mover or "", "moved_team_miles": per.get(mover, np.nan),
                     "moved_team_miles_if_stayed_west": np.nan,
                     "note": "Simplified proxy: one round trip per conference opponent, straight-line miles; ignores real schedules and back-to-backs"})
    df = pd.DataFrame(rows)
    # what the moving team would have travelled had it stayed West (32-team league, 17 West teams)
    for i, r in df.iterrows():
        if r.moved_team:
            t = pd.concat([a, new], ignore_index=True)
            df.at[i, "moved_team_miles_if_stayed_west"] = conference_travel(t)["West"][1][r.moved_team]
    df.to_csv(OUTPUTS / "realignment_travel.csv", index=False)
    a.to_csv(PROCESSED / "nba_arena_locations.csv", index=False)
    print(df[["option", "teams_east", "teams_west", "total_miles", "avg_miles_per_team", "west_avg_per_team", "moved_team_miles", "moved_team_miles_if_stayed_west"]].round(0).to_string())


if __name__ == "__main__":
    main()
