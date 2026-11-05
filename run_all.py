"""Rebuild everything: python run_all.py

Downloads raw data (cached in data/raw/), rebuilds the sourced team/arena tables,
the metro dataset, model, business case, research tables, figures and docs, then runs tests.
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
import download, build_manual, honeymoon, honeymoon_wiki, build_metros, realignment, model, business_case, research, figures, report  # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    for step in [download, build_manual, honeymoon, honeymoon_wiki, build_metros, model, business_case, realignment, research, figures]:
        print(f"\n=== {step.__name__} ===")
        step.main()
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], capture_output=True, text=True)
    print(tests.stdout[-1500:])
    report.main(runtime_s=time.time() - t0, test_output=tests.stdout)
    sys.exit(tests.returncode)
