"""Parse the NCAA men's basketball attendance PDF (Division I team-by-team table).

The PDF lays out rows like "School G Attendance Average", sometimes two per text line.
We use a regular expression to pull every (school, games, attendance, average) group
from the team-by-team pages and keep one row per school.
"""
import re
import pdfplumber
import pandas as pd

ROW = re.compile(r"(?:\d+\.\s)?([A-Z][A-Za-z&.'()\-\s]*?)\s(\d{1,2})\s(\d{1,3}(?:,\d{3})*)\s(\d{1,3}(?:,\d{3})?)(?=\s|$)")


def parse_ncaa(pdf_path):
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        in_d1 = False
        for page in pdf.pages:
            text = page.extract_text() or ""
            # The Division I team-by-team table starts on the page titled
            # "Division I Team-by-Team" and ends where the Division II table starts.
            if "Division I Team-by-Team" in text:
                in_d1 = True
            if "Division II Team-by-Team" in text:
                break
            if not in_d1:
                continue
            for line in text.split("\n"):
                for m in ROW.finditer(line):
                    school = m.group(1).strip()
                    # remove column headings that the PDF text glues onto names
                    for junk in ["Team Leaders ", "School G Attendance Average ", "Rank School Games Attendance Average "]:
                        school = school.replace(junk, "")
                    games, att, avg = int(m.group(2)), int(m.group(3).replace(",", "")), int(m.group(4).replace(",", ""))
                    # sanity check: attendance / games should be close to the printed average
                    if games > 0 and abs(att / games - avg) <= 2:
                        rows.append((school, games, att, avg))
    df = pd.DataFrame(rows, columns=["school", "games", "attendance", "avg_attendance"])
    df = df.drop_duplicates("school").sort_values("school").reset_index(drop=True)
    return df


if __name__ == "__main__":
    d = parse_ncaa("data/raw/ncaa_mbb_attend.pdf")
    print(len(d)); print(d.to_string())
