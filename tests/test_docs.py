"""Consistency check: every figure / file referenced in the docs exists, and no doc points at
outputs that were retired in earlier versions (stale numbers)."""
import re
from config import ROOT

DOCS = ["README.md", "memo/EXEC_SUMMARY.md", "memo/HEAD_TO_HEAD.md", "outputs/KEY_NUMBERS.md", "outputs/FINAL_REPORT.md", "research/focus_markets.md"]
RETIRED = ["dilution_payback", "07_dilution_payback", "breakeven_years"]


def test_doc_links_and_files_exist():
    for d in DOCS:
        path = ROOT / d
        text = path.read_text()
        for link in re.findall(r"\]\(([^)]+)\)", text):        # markdown links and images
            if link.startswith("http"):
                continue
            assert (path.parent / link).resolve().exists(), f"{d}: missing {link}"
        for ref in set(re.findall(r"`((?:outputs|figures|data|research|memo)/[\w./-]+\.(?:csv|png|md))`", text)):
            assert (ROOT / ref).exists(), f"{d}: missing {ref}"


def test_no_stale_outputs_referenced():
    for d in DOCS:
        text = (ROOT / d).read_text()
        for r in RETIRED:
            assert r not in text, f"{d} references retired output {r}"


def test_every_figure_used_in_readme():
    readme = (ROOT / "README.md").read_text()
    for f in (ROOT / "figures").glob("*.png"):
        if f.name != "linkedin_summary.png":
            assert f"figures/{f.name}" in readme, f"README does not show {f.name}"
