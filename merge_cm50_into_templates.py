"""
merge_cm50_into_templates.py

Stage 2 of SPEC2:
- Load normalized CM50 JSONL
- Load local template metadata (top30 / allTime / new)
- Enrich matching records with CM50 fields
- Write updated *_cm50.jsonl files (originals preserved)

Matching strategy:
  1. Primary:  template_id
  2. Fallback: image filename — Path(image_url).name vs Path(example_meme_url).name
               e.g. "3tnlfe.jpg" matches across the /4/ CDN subdirectory difference
"""

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CM50_DIR   = Path("/Users/vmac/prog/PY/semiotic_harm/RawCollection/cm50")
CM50_JSONL = CM50_DIR / "50_template_info.jsonl"

# /Users/vmac/prog/PY/semiotic_harm/RawCollection/cm50/50_template_info.jsonl

BASE_PATH  = Path("/Users/vmac/prog/PY/semiotic_harm/RawCollection/candidate_templates")

METADATA_FILES = {
    "top30":   BASE_PATH / "top30"   / "metadata_top30.jsonl",
    "allTime": BASE_PATH / "allTime" / "metadata_allTime.jsonl",
    "new":     BASE_PATH / "new"     / "metadata_new.jsonl",
}

# Fields that belong to the later LLM stage — never touch these
LLM_FIELDS = {
    "archetype", "pragmatic_function", "caption_dependence",
    "template_reasoning", "needs_human_review",
}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_cm50_map(
    jsonl_path: Path,
) -> tuple[dict[str, dict], dict[str, dict]]:
    """
    Load normalized CM50 JSONL and build two lookup indexes.

    Returns:
      id_map  — {template_id: record}       primary match
      img_map — {image_filename: record}    fallback match
        image_filename = Path(example_meme_url).name
        e.g. "3tnlfe.jpg" (ignores the /4/ CDN subdirectory)
    """
    id_map:  dict[str, dict] = {}
    img_map: dict[str, dict] = {}

    with jsonl_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)

                tid = rec.get("template_id", "").strip()
                if tid:
                    id_map[tid] = rec

                example_url = rec.get("example_meme_url", "")
                if example_url:
                    fname = Path(example_url).name   # e.g. "3tnlfe.jpg"
                    if fname:
                        img_map[fname] = rec

            except json.JSONDecodeError as exc:
                print(f"[ERROR] Malformed CM50 JSONL line: {exc}")

    print(
        f"[INFO] Loaded {len(id_map)} CM50 records from {jsonl_path.name} "
        f"({len(img_map)} with image fallback index)"
    )
    return id_map, img_map


def load_local_template_metadata(jsonl_path: Path) -> list[dict]:
    """Load all records from a local template metadata JSONL."""
    records: list[dict] = []
    if not jsonl_path.exists():
        print(f"[WARN] Metadata file not found: {jsonl_path}")
        return records
    with jsonl_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"[ERROR] Malformed line in {jsonl_path.name}: {exc}")
    return records


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def find_cm50_record(
    local: dict,
    id_map: dict[str, dict],
    img_map: dict[str, dict],
) -> tuple[dict | None, str]:
    """
    Look up a CM50 record for a local template.
    Returns (cm50_record | None, match_method).
    match_method is one of: "template_id", "image_filename", "none"
    """
    # Primary: template_id
    tid = str(local.get("template_id", "")).strip()
    if tid and tid in id_map:
        return id_map[tid], "template_id"

    # Fallback: image filename
    image_url = local.get("image_url", "")
    if image_url:
        fname = Path(image_url).name   # strips /4/ prefix, leaves "3tnlfe.jpg"
        if fname and fname in img_map:
            return img_map[fname], "image_filename"

    return None, "none"


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def merge_cm50_into_record(local: dict, cm50: dict) -> dict:
    """
    Enrich a local template record with CM50 fields.
    Never overwrites LLM-stage fields.
    """
    local["isCM50"]                 = True
    local["cm50_about"]             = cm50.get("cm50_about", "")
    local["example_meme_url"]       = cm50.get("example_meme_url", "")
    local["cm50_template_key"]      = cm50.get("template_key", "")
    local["cm50_title"]             = cm50.get("title", "")
    local["cm50_template_url"]      = cm50.get("template_url", "")
    local["cm50_alternative_names"] = cm50.get("alternative_names", [])

    # Update source list — no duplicates
    sources = local.get("source", [])
    if isinstance(sources, str):
        sources = [sources]
    if "cm50" not in sources:
        sources.append("cm50")
    local["source"] = sources

    return local


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def write_updated_jsonl(records: list[dict], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[OK]   Wrote {len(records)} records to {out_path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_merge() -> None:
    id_map, img_map = load_cm50_map(CM50_JSONL)

    total_matched_id  = 0
    total_matched_img = 0
    total_unmatched   = 0

    for category, jsonl_path in METADATA_FILES.items():
        records = load_local_template_metadata(jsonl_path)
        if not records:
            print(f"[WARN] No records found for category '{category}' — skipping")
            continue

        print(f"\n[INFO] Processing '{category}' — {len(records)} records")

        cat_id   = 0
        cat_img  = 0
        cat_none = 0

        for rec in records:
            cm50_rec, method = find_cm50_record(rec, id_map, img_map)

            if cm50_rec:
                merge_cm50_into_record(rec, cm50_rec)
                if method == "template_id":
                    cat_id += 1
                else:
                    cat_img += 1
                    print(f"    [FALLBACK] image_filename match — "
                          f"template_id={rec.get('template_id')} "
                          f"({rec.get('title', 'unknown')})")
            else:
                rec["isCM50"] = False
                cat_none += 1
                print(f"    [WARN] No CM50 match — "
                      f"template_id={rec.get('template_id')} "
                      f"({rec.get('title', 'unknown')})")

        stem     = jsonl_path.stem
        out_path = jsonl_path.parent / f"{stem}_cm50.jsonl"
        write_updated_jsonl(records, out_path)

        print(
            f"[INFO] '{category}': "
            f"{cat_id} matched by id, "
            f"{cat_img} matched by image, "
            f"{cat_none} unmatched"
        )
        total_matched_id  += cat_id
        total_matched_img += cat_img
        total_unmatched   += cat_none

    print(
        f"\n[OK]   Merge complete — "
        f"{total_matched_id} by template_id, "
        f"{total_matched_img} by image filename, "
        f"{total_unmatched} unmatched"
    )


if __name__ == "__main__":
    run_merge()
