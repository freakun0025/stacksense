"""Assembles the Section 9.3 submission folder next to the repository:

    StackSense26_Kunal_Mittal/
    ├── source/                    every git-tracked file (README.md at its root, .env.example, no secrets)
    ├── outputs/P1..P6_output.json engine output for the public scenarios (regenerated now)
    └── Report_Kunal_Mittal.pdf    built by report/build_report.py

Usage: python tools/package_submission.py [--out <parent dir>]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from stacksense_engine.recommend import recommend, to_json  # noqa: E402

FOLDER = "StackSense26_Kunal_Mittal"
REPORT = "Report_Kunal_Mittal.pdf"
FORBIDDEN = ("node_modules", ".venv", "venv", "__pycache__", ".env")


def tracked_files():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.dirname(ROOT))
    args = ap.parse_args()
    dest = os.path.join(args.out, FOLDER)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    src_dest = os.path.join(dest, "source")
    files = tracked_files()
    untracked_needed = [f for f in ("README.md",) if f not in files]
    if untracked_needed:
        raise SystemExit(f"commit these first: {untracked_needed}")
    for rel in files:
        if any(part in FORBIDDEN for part in rel.replace("\\", "/").split("/")):
            raise SystemExit(f"refusing to package {rel}")
        target = os.path.join(src_dest, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(os.path.join(ROOT, rel), target)
    out_dir = os.path.join(dest, "outputs")
    os.makedirs(out_dir)
    for i in range(1, 7):
        with open(os.path.join(ROOT, "scenarios", "public", f"P{i}.json"), encoding="utf-8") as f:
            res = recommend(json.load(f))
        with open(os.path.join(out_dir, f"P{i}_output.json"), "w", encoding="utf-8", newline="\n") as f:
            f.write(to_json(res) + "\n")
    report = os.path.join(ROOT, "report", "build", REPORT)
    if not os.path.isfile(report):
        raise SystemExit("report missing: run `python report/build_report.py` first")
    shutil.copy2(report, os.path.join(dest, REPORT))
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(dest) for f in fs)
    print(f"{dest}\n  source files: {len(files)}\n  outputs: 6\n  report: {REPORT}\n  total size: {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
