Prompt-based archetype enrichment using a fixed 3-shot CM50 prompt, one model, one temperature, one seed, single-pass JSON output.

Baseline
K_SHOTS         = 3
SEED            = 42
MODEL           = "gpt-4o"
TEMPERATURE     = 0.3
RETRY_DELAY     = 2


temp = 0.0 and 0.3

MODELS = [
    "gpt-4o",
    "gemini-2.5-pro",
    "qwen2.5-vl"
]

do not forget!

export OPENAI_API_KEY=sk-...
export GOOGLE_API_KEY=...
export HF_TOKEN=...

# Full matrix (6 runs)
uv run run_experiments.py

# Or single run for testing
uv run enrich_spiral0.py --model gpt-4o --temperature 0.3
uv run enrich_spiral0.py --model qwen2.5-vl --temperature 0.0

# outputs go here
spiral0/
  gpt-4o_t0.0/results.jsonl
  gpt-4o_t0.3/results.jsonl
  gemini-2.5-pro_t0.0/results.jsonl
  gemini-2.5-pro_t0.3/results.jsonl
  qwen2.5-vl_t0.0/results.jsonl
  qwen2.5-vl_t0.3/results.jsonl