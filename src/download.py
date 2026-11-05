"""Download every raw source into data/raw/ (skips files that already exist).

ACS summary files are national files covering every geography (100+ MB), so we
stream them and keep only the header plus metro rows (GEO_ID starting '310M').
"""
import requests
from config import RAW, SOURCES

HEADERS = {"User-Agent": "nba-expansion-strategy student research script"}


def fetch(name, url, fname):
    path = RAW / fname
    if path.exists() and path.stat().st_size > 0:
        return "cached"
    r = requests.get(url, headers=HEADERS, timeout=600, stream=True)
    r.raise_for_status()
    if name.startswith("acs_b"):
        with open(path, "w") as out:
            r.encoding = "utf-8"
            for i, line in enumerate(r.iter_lines(decode_unicode=True)):
                line = line.decode("utf-8") if isinstance(line, bytes) else line
                if i == 0 or line.startswith("310M"):
                    out.write(line + "\n")
    else:
        with open(path, "wb") as out:
            for chunk in r.iter_content(1 << 20):
                out.write(chunk)
    return "downloaded"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    status = {}
    for name, (url, fname) in SOURCES.items():
        try:
            status[name] = fetch(name, url, fname)
        except Exception as e:  # log and continue; build step decides what is essential
            status[name] = f"FAILED: {e}"
        print(f"{name:14s} {status[name]}")
    return status


if __name__ == "__main__":
    main()
