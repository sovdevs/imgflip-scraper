"""
enrich_spiral0.py

Spiral 0 — Archetype Enrichment (image-grounded, few-shot)

Accepts --model, --temperature, --output-dir for experimental runs.
Called directly or via run_experiments.py.
"""

import argparse
import base64
import json
import os
import random
import time
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

# ---------------------------------------------------------------------------
# Paths (fixed)
# ---------------------------------------------------------------------------

CM50_DIR     = Path("/Users/vmac/prog/PY/semiotic_harm/RawCollection/cm50")
CM50_JSONL   = CM50_DIR / "50_template_info.jsonl"
CM50_IMG_DIR = CM50_DIR / "templates" / "img"

BASE_PATH    = Path("/Users/vmac/prog/PY/semiotic_harm/RawCollection/candidate_templates")

METADATA_FILES = {
    "top30":   BASE_PATH / "top30"   / "metadata_top30_cm50.jsonl",
    "allTime": BASE_PATH / "allTime" / "metadata_allTime_cm50.jsonl",
    "new":     BASE_PATH / "new"     / "metadata_new_cm50.jsonl",
}

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

K_SHOTS     = 3
SEED        = 42
RETRY_DELAY = 2

# ---------------------------------------------------------------------------
# Model routing
# All providers expose an OpenAI-compatible chat/completions endpoint.
# ---------------------------------------------------------------------------

MODEL_CONFIGS = {
    "gpt-4o": {
        "model":        "gpt-4o",
        "base_url":     None,                                # standard OpenAI
        "api_key_env":  "OPENAI_API_KEY",
    },
    "gemini-2.5-pro": {
        "model":        "gemini-2.5-pro-preview-03-25",
        "base_url":     "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env":  "GOOGLE_API_KEY",
    },
    "qwen2.5-vl": {
        "model":        "Qwen/Qwen2.5-VL-7B-Instruct:hyperbolic",
        "base_url":     "https://router.huggingface.co/v1",
        "api_key_env":  "HF_TOKEN",
    },
}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are analyzing blank meme templates at the archetype level.

An archetype is a higher-level communicative pattern or persona that encodes \
a recurring pragmatic function and interpretive framing, shaping how a meme's \
content is understood beyond its literal visual and textual elements. Archetypes \
may be instantiated through one or more meme templates and provide the semantic \
grounding necessary for interpreting implicit meaning.

Your task is to identify the archetype embodied by a template — not to describe \
its visual appearance or origin, but to name the communicative pattern it \
instantiates and how it frames the meaning of any caption placed on it.

You will be shown worked examples, each with the blank template image and a \
factual "about" description. Study how the about informs the reasoning.

Then analyze a new template image and produce the same output.

Respond ONLY with valid JSON. No preamble, no markdown fences.\
"""

# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def encode_image(path: Path) -> str | None:
    if not path.exists():
        print(f"  [WARN] Image not found: {path}")
        return None
    with path.open("rb") as fh:
        return base64.b64encode(fh.read()).decode("utf-8")


def image_block(b64: str) -> dict:
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "low"},
    }

# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_cm50_examples(jsonl_path: Path) -> list[dict]:
    examples = []
    if not jsonl_path.exists():
        print(f"[WARN] CM50 JSONL not found: {jsonl_path}")
        return examples
    with jsonl_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    print(f"[INFO] Loaded {len(examples)} CM50 records")
    return examples


def load_metadata(jsonl_path: Path) -> list[dict]:
    records = []
    if not jsonl_path.exists():
        print(f"[WARN] Not found: {jsonl_path}")
        return records
    with jsonl_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    print(f"[ERROR] {exc}")
    return records

# ---------------------------------------------------------------------------
# Few-shot block (built once per run)
# ---------------------------------------------------------------------------

def build_few_shot_blocks(examples: list[dict]) -> list[dict]:
    blocks = []
    for i, ex in enumerate(examples, 1):
        key   = ex.get("template_key", "")
        title = ex.get("title", key)
        about = ex.get("cm50_about", "")
        alt   = ex.get("alternative_names", [])
        alt_str = ", ".join(alt) if isinstance(alt, list) else str(alt)

        b64 = encode_image(CM50_IMG_DIR / f"{key}.jpg")

        blocks.append({"type": "text", "text": f"--- EXAMPLE {i} ---\nTemplate: {title}"})
        if alt_str:
            blocks.append({"type": "text", "text": f"Also known as: {alt_str}"})
        if b64:
            blocks.append(image_block(b64))
        blocks.append({"type": "text", "text": f"About: {about}"})
        blocks.append({
            "type": "text",
            "text": (
                'Expected output:\n'
                '{\n'
                f'  "template_name": "{title}",\n'
                '  "template_reasoning": "<what this template communicates, grounded in its visual identity and pragmatic function>",\n'
                '  "archetype": "<concise label for the communicative archetype>",\n'
                '  "needs_human_review": false\n'
                '}'
            ),
        })
    return blocks

# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def call_llm(
    record: dict,
    few_shot_blocks: list[dict],
    llm: ChatOpenAI,
) -> str | None:
    title    = record.get("title", record.get("template_id", "unknown"))
    img_path = BASE_PATH / record.get("local_image_path", "")
    b64      = encode_image(img_path)

    target: list[dict] = [
        {"type": "text", "text": "--- NOW ANALYZE THIS TEMPLATE ---"},
        {"type": "text", "text": f"Template: {title}"},
    ]
    if b64:
        target.append(image_block(b64))
    else:
        target.append({"type": "text", "text": "(image unavailable — reason from title only)"})
    target.append({
        "type": "text",
        "text": "Produce strict JSON with keys: template_name, template_reasoning, archetype, needs_human_review",
    })

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=few_shot_blocks + target),
    ]
    try:
        response = llm.invoke(messages)
        return StrOutputParser().invoke(response)
    except Exception as exc:
        print(f"  [ERROR] LLM call failed: {exc}")
        return None

# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def parse_output(raw: str) -> dict | None:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(
            l for l in cleaned.splitlines() if not l.strip().startswith("```")
        ).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None

# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_record_json(record: dict, out_dir: Path) -> None:
    tid  = record.get("template_id", "unknown")
    slug = record.get("slug", record.get("template_key", "template"))
    with (out_dir / f"{tid}_{slug}.json").open("w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)


def append_jsonl(record: dict, jsonl_path: Path) -> None:
    with jsonl_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_spiral0(
    model_key:   str   = "gpt-4o",
    temperature: float = 0.3,
    output_dir:  Path  = BASE_PATH / "spiral0" / "baseline",
) -> None:
    cfg = MODEL_CONFIGS[model_key]

    # Resolve API key
    api_key = os.environ.get(cfg["api_key_env"])
    if not api_key:
        raise EnvironmentError(f"Missing env var: {cfg['api_key_env']}")

    # Build LLM client
    llm_kwargs = dict(model=cfg["model"], temperature=temperature, api_key=api_key)
    if cfg["base_url"]:
        llm_kwargs["base_url"] = cfg["base_url"]
    llm = ChatOpenAI(**llm_kwargs)

    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_out = output_dir / "results.jsonl"
    jsonl_out.write_text("")   # fresh file per run

    print(f"\n{'='*60}")
    print(f"Model       : {cfg['model']}")
    print(f"Temperature : {temperature}")
    print(f"Output      : {output_dir}")
    print(f"{'='*60}\n")

    # Few-shot selection — fixed across all experiments
    all_cm50 = load_cm50_examples(CM50_JSONL)
    random.seed(SEED)
    few_shot_sample = random.sample(all_cm50, min(K_SHOTS, len(all_cm50)))

    print(f"[INFO] Few-shot examples (seed={SEED}):")
    for ex in few_shot_sample:
        print(f"  - {ex.get('title', ex.get('template_key'))}")

    few_shot_blocks = build_few_shot_blocks(few_shot_sample)
    print(f"[INFO] Few-shot block ready ({len(few_shot_blocks)} parts)\n")

    total_done = total_skipped = total_flagged = 0

    for category, jsonl_path in METADATA_FILES.items():
        records = load_metadata(jsonl_path)
        if not records:
            print(f"[WARN] No records for '{category}' — skipping")
            continue

        print(f"\n--- {category} ({len(records)} records) ---")

        for rec in records:
            title = rec.get("title", rec.get("template_id"))

            if rec.get("archetype"):
                print(f"  [SKIP] {title}")
                total_skipped += 1
                continue

            print(f"  [INFO] {title}")

            parsed = None
            for attempt in range(2):
                raw = call_llm(rec, few_shot_blocks, llm)
                if raw:
                    parsed = parse_output(raw)
                if parsed:
                    break
                if attempt == 0:
                    print(f"  [RETRY] ...")
                    time.sleep(RETRY_DELAY)

            if parsed:
                rec["template_reasoning"] = parsed.get("template_reasoning", "")
                rec["archetype"]          = parsed.get("archetype", "")
                rec["needs_human_review"] = parsed.get("needs_human_review", False)
                print(f"  [OK]   {rec['archetype']}")
            else:
                rec["template_reasoning"] = ""
                rec["archetype"]          = ""
                rec["needs_human_review"] = True
                total_flagged += 1
                print(f"  [ERROR] Flagged for review")

            rec["spiral"]      = "0"
            rec["experiment"]  = {"model": cfg["model"], "temperature": temperature}

            write_record_json(rec, output_dir)
            append_jsonl(rec, jsonl_out)
            total_done += 1
            time.sleep(1)

    print(f"\n[OK] Done — {total_done} processed, {total_skipped} skipped, {total_flagged} flagged")
    print(f"     Results: {jsonl_out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spiral 0 archetype enrichment")
    parser.add_argument("--model",       default="gpt-4o",
                        choices=list(MODEL_CONFIGS.keys()))
    parser.add_argument("--temperature", default=0.3, type=float)
    parser.add_argument("--output-dir",  default=None,
                        help="Override output directory")
    args = parser.parse_args()

    out = (
        Path(args.output_dir)
        if args.output_dir
        else BASE_PATH / "spiral0" / f"{args.model}_t{args.temperature}"
    )

    run_spiral0(
        model_key=args.model,
        temperature=args.temperature,
        output_dir=out,
    )
