# Constraint-Audited Language CAPTCHAs — Reproducibility Artifacts

This repository contains artifacts supporting a **design + pilot study** of *constraint-audited language CAPTCHAs*. The artifacts enable reproduction of the pilot evaluation workflow described in the paper by providing: (i) synthetic task definitions, (ii) deterministic validators, and (iii) scripts to record and summarize results.

These artifacts are intended for **defensive research and evaluation only**. They intentionally exclude solver automation pipelines, prompt optimization strategies, and any code that interacts with deployed CAPTCHA services.

## Contents

- `tasks/`: Synthetic task definitions used in the pilot study
  - `baseline_tasks.json`: simple instruction-following tasks with exact answers
  - `constraint_tasks.json`: constraint-audited tasks with deterministic validators
- `validator.py`: Deterministic validation logic returning pass/fail + error labels
- `run_pilot.py`: Runs the pilot in either manual mode (paste outputs) or from-file mode (JSONL)
- `analyze_results.py`: Summarizes a results CSV into pass rates and failure-mode counts
- `results/`: Example outputs and templates
- `docs/ARTIFACT_APPENDIX.md`: USENIX Artifact Evaluation appendix template

## Requirements

- Python 3.10+ (no external dependencies)

## Reproducing the Pilot

### Step 1: Choose a model and generate outputs

You may use any LLM. For each task prompt, obtain a model output. **Do not** include additional text beyond what the task requests. If your model returns code fences, remove them.

### Step 2: Record results (manual mode)

Manual mode prompts you task-by-task and lets you paste model outputs:

```bash
python run_pilot.py --out results/pilot_results.csv --retries 3 --mode manual
```

### Step 3: Record results (from-file mode)

If you prefer repeatability, put outputs in a JSONL file:

```json
{"task_id":"C1","attempt":1,"output":"{\"a\":2,\"b\":5}"}
```

Then run:

```bash
python run_pilot.py --mode from-file --inputs inputs.jsonl --out results/pilot_results.csv --retries 3
```

### Step 4: Summarize

```bash
python analyze_results.py --in results/pilot_results.csv
```

## Ethical Notes

These artifacts are designed to support reproducible measurement of **challenge/validator behavior** and failure modes under deterministic scoring. They **do not** provide end-to-end solver tooling. All tasks are synthetic and do not correspond to any specific deployed CAPTCHA.
