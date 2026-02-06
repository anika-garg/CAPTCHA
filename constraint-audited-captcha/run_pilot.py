#!/usr/bin/env python3
"""
Run the pilot evaluation in a reproducible way without bundling solver automation.

Modes:
  1) manual (default): prints each task prompt and asks you to paste a model output for each attempt.
  2) from-file: reads a JSONL file containing model outputs (for easier reruns).

Outputs a CSV with pass/fail and error labels.

Example (manual):
  python run_pilot.py --out results/pilot_results.csv

Example (from-file):
  python run_pilot.py --mode from-file --inputs inputs.jsonl --out results/pilot_results.csv

JSONL format:
  {"task_id":"C1","attempt":1,"output":"{...}"}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, Any, List, Tuple

from validator import validate

def load_tasks(tasks_dir: str) -> List[Dict[str, Any]]:
    tasks: List[Dict[str, Any]] = []
    for fname in ("baseline_tasks.json", "constraint_tasks.json"):
        path = os.path.join(tasks_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            tasks.extend(json.load(f))
    # stable ordering
    tasks.sort(key=lambda x: x["id"])
    return tasks

def write_csv(rows: List[Dict[str, Any]], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fieldnames = ["task_id", "task_type", "attempt", "passed", "error", "detail"]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        import csv
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def manual_mode(tasks: List[Dict[str, Any]], retries: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    print("Manual mode: paste model outputs exactly as returned.\n"
          "Tip: if your model adds code fences, remove them before pasting.\n", file=sys.stderr)
    for task in tasks:
        print("="*80, file=sys.stderr)
        print(f"Task {task['id']} ({task['type']}):", file=sys.stderr)
        print(task["prompt"], file=sys.stderr)
        for attempt in range(1, retries+1):
            print(f"\nAttempt {attempt}/{retries}. Paste output, then press Enter and Ctrl-D (or Ctrl-Z on Windows):", file=sys.stderr)
            try:
                output = sys.stdin.read()
            except KeyboardInterrupt:
                print("\nInterrupted.", file=sys.stderr)
                return rows
            # reset stdin for next prompt (works in many terminals by reopening)
            # In notebooks/redirect contexts, use from-file mode instead.
            res = validate(task, output.strip("\n"))
            rows.append({
                "task_id": task["id"],
                "task_type": task["type"],
                "attempt": attempt,
                "passed": res.passed,
                "error": res.error,
                "detail": res.detail or ""
            })
            if res.passed:
                break
            else:
                print(f"Validator: FAIL ({res.error}) {('- ' + res.detail) if res.detail else ''}", file=sys.stderr)
        # Re-open stdin for next task prompt (POSIX terminals: /dev/tty)
        try:
            sys.stdin = open("/dev/tty", "r", encoding="utf-8")
        except Exception:
            # If /dev/tty is unavailable, advise user.
            print("\nNote: /dev/tty unavailable. If manual mode breaks, use --mode from-file.", file=sys.stderr)
            break
    return rows

def from_file_mode(tasks: List[Dict[str, Any]], retries: int, inputs_path: str) -> List[Dict[str, Any]]:
    # Index tasks
    task_map = {t["id"]: t for t in tasks}
    # Read inputs
    attempts: Dict[Tuple[str,int], str] = {}
    with open(inputs_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            attempts[(rec["task_id"], int(rec["attempt"]))] = rec["output"]
    rows: List[Dict[str, Any]] = []
    for task in tasks:
        for attempt in range(1, retries+1):
            out = attempts.get((task["id"], attempt))
            if out is None:
                continue
            res = validate(task, out)
            rows.append({
                "task_id": task["id"],
                "task_type": task["type"],
                "attempt": attempt,
                "passed": res.passed,
                "error": res.error,
                "detail": res.detail or ""
            })
            if res.passed:
                break
    return rows

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks-dir", default="tasks", help="Directory containing task JSON files.")
    ap.add_argument("--retries", type=int, default=3, help="Max attempts per task (bounded retry budget).")
    ap.add_argument("--mode", choices=["manual","from-file"], default="manual")
    ap.add_argument("--inputs", default=None, help="JSONL inputs file (required for from-file mode).")
    ap.add_argument("--out", default="results/pilot_results.csv", help="CSV output path.")
    args = ap.parse_args()

    tasks = load_tasks(args.tasks_dir)
    if args.mode == "from-file":
        if not args.inputs:
            raise SystemExit("--inputs is required for from-file mode.")
        rows = from_file_mode(tasks, args.retries, args.inputs)
    else:
        rows = manual_mode(tasks, args.retries)

    write_csv(rows, args.out)
    print(f"Wrote {len(rows)} rows to {args.out}", file=sys.stderr)

if __name__ == "__main__":
    main()
