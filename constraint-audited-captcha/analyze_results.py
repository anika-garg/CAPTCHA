#!/usr/bin/env python3
"""
Summarize pilot results CSV into pass rates and failure-mode counts.

Example:
  python analyze_results.py --in results/pilot_results.csv
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="results/pilot_results.csv")
    args = ap.parse_args()

    # Keep only final attempt per task (first PASS or last attempt)
    per_task = {}
    attempts = defaultdict(list)

    with open(args.inp, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            row["attempt"] = int(row["attempt"])
            row["passed"] = row["passed"].lower() == "true"
            attempts[row["task_id"]].append(row)

    for tid, rows in attempts.items():
        rows_sorted = sorted(rows, key=lambda x: x["attempt"])
        final = None
        for rr in rows_sorted:
            final = rr
            if rr["passed"]:
                break
        per_task[tid] = final

    # Summaries
    by_type = defaultdict(lambda: {"n":0, "pass":0})
    err_counts = defaultdict(int)

    for tid, row in per_task.items():
        ttype = row["task_type"]
        by_type[ttype]["n"] += 1
        if row["passed"]:
            by_type[ttype]["pass"] += 1
        else:
            err_counts[row["error"]] += 1

    print("Final pass rates (per task):")
    for ttype, s in by_type.items():
        n = s["n"]
        p = s["pass"]
        rate = (p / n * 100) if n else 0
        print(f"  {ttype:10s}: {p}/{n} = {rate:.1f}%")

    print("\nFailure modes (final attempt only):")
    for err, c in sorted(err_counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {err:20s} {c}")

if __name__ == "__main__":
    main()
