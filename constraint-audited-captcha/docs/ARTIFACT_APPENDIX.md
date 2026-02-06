# USENIX Artifact Appendix (Template)

This repository is intended to support the *reproducibility* of the pilot evaluation workflow described in the paper.

## Artifact Summary

The artifact provides (i) synthetic task definitions, (ii) deterministic validators that produce pass/fail and error labels, and (iii) scripts to record and summarize results. The artifact intentionally excludes solver automation code and any interaction with deployed CAPTCHA services.

## Artifact Availability

The artifact is intended to be hosted as a public repository. The release should include a tagged version matching the paper submission.

## Hardware Dependencies

None beyond a standard machine capable of running Python 3.10+.

## Software Dependencies

Python 3.10+.
No external packages are required.

## Data Sets

Two synthetic datasets are provided:
- `tasks/baseline_tasks.json` (N=10)
- `tasks/constraint_tasks.json` (N=10)

These datasets contain only synthetic content.

## Execution

To reproduce the pilot evaluation workflow:

1. Generate model outputs for each task prompt (using any LLM).
2. Record and validate outputs:

   - Manual mode:
     `python run_pilot.py --mode manual --retries 3 --out results/pilot_results.csv`

   - From-file mode:
     `python run_pilot.py --mode from-file --inputs inputs.jsonl --retries 3 --out results/pilot_results.csv`

3. Summarize results:
   `python analyze_results.py --in results/pilot_results.csv`

## Expected Output

The primary output is a CSV file listing attempts with pass/fail and error labels, and a textual summary of per-task pass rates and failure-mode counts.

## Notes on Responsible Release

This artifact focuses on challenge generation and validation to enable independent evaluation while reducing the risk of enabling bypass. Solver automation, prompt optimization strategies, and scripts interacting with live CAPTCHA services are intentionally omitted.
