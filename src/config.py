"""Central configuration: paths, source URLs and access dates."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANUAL = ROOT / "data" / "manual"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
FIGURES = ROOT / "figures"
RESEARCH = ROOT / "research"

ACCESS_DATE = "2026-11-05"  # date every source below was downloaded
REPO_NAME = "nba-expansion-strategy"

ACS_BASE = "https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/"
WIKI = "https://en.wikipedia.org/wiki/"

# name -> (url, local filename). ACS tables are filtered to metro rows while downloading.
SOURCES = {
    "acs_b01003": (ACS_BASE + "acsdt5y2024-b01003.dat", "acs_b01003.dat"),  # total population
    "acs_b01001": (ACS_BASE + "acsdt5y2024-b01001.dat", "acs_b01001.dat"),  # sex by age
    "acs_b11001": (ACS_BASE + "acsdt5y2024-b11001.dat", "acs_b11001.dat"),  # households
    "acs_b19013": (ACS_BASE + "acsdt5y2024-b19013.dat", "acs_b19013.dat"),  # median household income
    "acs_shells": ("https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/documentation/ACS20245YR_Table_Shells.txt", "acs_table_shells.txt"),
    "popest": ("https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/metro/totals/cbsa-est2025-alldata.csv", "cbsa-est2025-alldata.csv"),
    "delineation": ("https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx", "cbsa_delineation_2023.xlsx"),
    "principal_cities": ("https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list2_2023.xlsx", "cbsa_principal_cities_2023.xlsx"),
    "bea_gdp": ("https://apps.bea.gov/regional/zip/CAGDP1.zip", "bea_CAGDP1.zip"),
    "cbp": ("https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23msa.zip", "cbp23msa.zip"),
    "ncaa": ("https://s3.amazonaws.com/fs.ncaa.org/Docs/stats/m_basketball_RB/Attend.pdf", "ncaa_mbb_attend.pdf"),
    "wiki_nba": (WIKI + "National_Basketball_Association", "wiki_nba.html"),
    "wiki_nfl": (WIKI + "National_Football_League", "wiki_nfl.html"),
    "wiki_mlb": (WIKI + "Major_League_Baseball", "wiki_mlb.html"),
    "wiki_nhl": (WIKI + "National_Hockey_League", "wiki_nhl.html"),
    "wiki_mls": (WIKI + "Major_League_Soccer", "wiki_mls.html"),
    "wiki_wnba": (WIKI + "Women%27s_National_Basketball_Association", "wiki_wnba.html"),
    "wiki_gleague": (WIKI + "NBA_G_League", "wiki_gleague.html"),
    "wiki_arenas": (WIKI + "List_of_indoor_arenas_in_the_United_States", "wiki_arenas.html"),
}

# Metros named in expansion coverage that must be in the study set even if < 1M people.
NAMED_METROS = ["Las Vegas, NV", "Seattle, WA", "Kansas City, MO", "Louisville, KY", "Nashville, TN",
                "Austin, TX", "San Diego, CA", "Pittsburgh, PA", "Tampa, FL", "St. Louis, MO",
                "Columbus, OH", "Cincinnati, OH", "Raleigh, NC", "Baltimore, MD"]
POP_THRESHOLD = 1_000_000
