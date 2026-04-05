"""
run_experiments.py

Runs the full Spiral 0 experiment matrix:
  models x temperatures

Output structure:
  spiral0/
    gpt-4o_t0.0/
    gpt-4o_t0.3/
    gemini-2.5-pro_t0.0/
    gemini-2.5-pro_t0.3/
    qwen2.5-vl_t0.0/
    qwen2.5-vl_t0.3/
      results.jsonl
      {template_id}_{slug}.json
      ...
"""

from pathlib import Path
from enrich_spiral0 import run_spiral0, MODEL_CONFIGS, BASE_PATH

# ---------------------------------------------------------------------------
# Experiment matrix
# ---------------------------------------------------------------------------

MODELS = [
    "gpt-4o",
    "gemini-2.5-pro",
    "qwen2.5-vl",
]

TEMPERATURES = [0.0, 0.3]

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all() -> None:
    matrix = [(m, t) for m in MODELS for t in TEMPERATURES]

    print(f"Experiment matrix: {len(matrix)} runs")
    for model, temp in matrix:
        print(f"  {model} | temp={temp}")

    for model, temp in matrix:
        label     = f"{model}_t{temp}"
        out_dir   = BASE_PATH / "spiral0" / label

        print(f"\n{'#'*60}")
        print(f"# RUN: {label}")
        print(f"{'#'*60}")

        try:
            run_spiral0(
                model_key=model,
                temperature=temp,
                output_dir=out_dir,
            )
        except EnvironmentError as exc:
            print(f"[SKIP] {label} — {exc}")
            continue

    print(f"\n{'='*60}")
    print("All runs complete.")
    print(f"Results in: {BASE_PATH / 'spiral0'}/")


if __name__ == "__main__":
    run_all()
