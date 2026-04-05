# Imgflip Template Scraper Specification

## Overview

This module scrapes blank meme templates from Imgflip and stores them locally for use in a template → archetype → RAG pipeline.

The scraper builds three separate sub-datasets:
- Top 30 Days
- Top All Time
- Top New

Each dataset consists of:
- Downloaded template images
- JSONL metadata file

The scraper is designed to:
- Run periodically (e.g., monthly)
- Avoid re-downloading previously processed templates
- Maintain reproducibility via snapshot-based acquisition

---

## Target Directory Structure

Base path:

/Users/vmac/prog/PY/semiotic_harm/RawCollection/candidate_templates/

Structure:

candidate_templates/
  top30/
    images/
    metadata_top30.jsonl

  allTime/
    images/
    metadata_allTime.jsonl

  new/
    images/
    metadata_new.jsonl

---

## Data Source

Source website:
https://imgflip.com/memetemplates

Sort modes:

- Top 30 days:
  https://imgflip.com/memetemplates

- Top All Time:
  https://imgflip.com/memetemplates?sort=top-all-time

- Top New:
  https://imgflip.com/memetemplates?sort=top-new

---

## Scraping Strategy

For each category:
- Iterate over first N pages
- N = 5 (fixed)

Each page contains ~30 templates

Total expected templates:
~450 (before deduplication)

---

## HTML Structure

Each template is contained in:

<div class="mt-box">
    <h3 class="mt-title">
        <a href="/meme/{id}/{slug}">TITLE</a>
    </h3>
    <div class="mt-img-wrap">
        <img src="//i.imgflip.com/...jpg">
    </div>
</div>

---

## Fields to Extract

From each template:

- template_id (from URL)
- title
- slug (from URL)
- template_page_url
- image_url

---

## Image Handling

- Convert image URLs starting with `//` to `https://`
- Download image to:
  {category}/images/{template_id}_{slug}.jpg

- Slug must be sanitized (no spaces or special chars)

---

## Deduplication Logic

Two levels:

### 1. Per-dataset deduplication
- Load existing JSONL
- Extract all template_ids
- Skip if already present

### 2. Cross-dataset deduplication (optional but recommended)
- Maintain global set of template_ids
- Prevent duplicates across top30 / allTime / new

---

## Metadata Output (JSONL)

One JSONL file per dataset.

Example entry:

{
  "template_id": "216523697",
  "title": "All My Homies Hate",
  "slug": "All-My-Homies-Hate",
  "template_page_url": "https://imgflip.com/meme/216523697/All-My-Homies-Hate",
  "image_url": "https://i.imgflip.com/4/3kwur5.jpg",
  "local_image_path": "top30/images/216523697_All-My-Homies-Hate.jpg",
  "source": "imgflip",
  "category": "top30",
  "page_number": 1,
  "downloaded_at": "ISO_TIMESTAMP"
}

---

## Rate Limiting

- Sleep 1 second between requests
- Use browser-like User-Agent header

---

## Error Handling

- Skip templates with missing fields
- Retry image download once
- Log failures but continue execution

---

## Script Interface

File name:

scraper_imgflip_templates.py

Main function:

run_scraper()

Optional CLI:

python scraper_imgflip_templates.py --pages 5

---

## Configuration

Hardcoded (initially):

N_PAGES = 5

BASE_PATH = "/Users/vmac/prog/PY/semiotic_harm/RawCollection/candidate_templates"

CATEGORIES = {
    "top30": "...",
    "allTime": "...",
    "new": "..."
}

---

## Output Guarantees

After execution:

- Images saved locally
- JSONL metadata updated incrementally
- No duplicate template_ids processed
- Script can be safely re-run

---

## Integration with Downstream Pipeline

This scraper only handles **template acquisition**.

Next stages:

1. Archetype enrichment (LLM)
2. RAG indexing
3. Runtime template matching

---

## Important Design Decisions

- No text removal required (Imgflip provides blank templates)
- Templates are treated as **surface forms**
- Archetypes will be added later via LLM processing
- Snapshot approach ensures reproducibility

---

## Future Extensions

- Add SHA256 hashing for stronger deduplication
- Add concurrency for faster downloads
- Add logging file
- Add progress tracking
- Add live update mode (optional)

---

## Non-Goals

- No archetype inference in this script
- No RAG integration
- No image processing beyond download

---

## Success Criteria

- ~300–450 templates downloaded
- Clean folder structure
- Valid JSONL files
- Script re-runnable without duplication