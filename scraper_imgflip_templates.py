"""
scraper_imgflip_templates.py

Scrapes blank meme templates from Imgflip and stores them locally.
Spec: Imgflip Template Scraper Specification
"""

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

N_PAGES = 5

BASE_PATH = Path("/Users/vmac/prog/PY/semiotic_harm/RawCollection/candidate_templates")

CATEGORIES = {
    "top30":   "https://imgflip.com/memetemplates",
    "allTime": "https://imgflip.com/memetemplates?sort=top-all-time",
    "new":     "https://imgflip.com/memetemplates?sort=top-new",
}

METADATA_FILES = {
    "top30":   "metadata_top30.jsonl",
    "allTime": "metadata_allTime.jsonl",
    "new":     "metadata_new.jsonl",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

REQUEST_DELAY = 1  # seconds between requests


# ---------------------------------------------------------------------------
# Directory setup
# ---------------------------------------------------------------------------

def setup_dirs() -> None:
    for cat in CATEGORIES:
        (BASE_PATH / cat / "images").mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# JSONL helpers
# ---------------------------------------------------------------------------

def load_existing_ids(jsonl_path: Path) -> set[str]:
    """Return the set of template_ids already present in a JSONL file."""
    ids: set[str] = set()
    if not jsonl_path.exists():
        return ids
    with jsonl_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                ids.add(record["template_id"])
            except (json.JSONDecodeError, KeyError):
                pass
    return ids


def append_record(jsonl_path: Path, record: dict) -> None:
    with jsonl_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Slug sanitisation
# ---------------------------------------------------------------------------

def sanitise_slug(slug: str) -> str:
    """Remove characters that are unsafe in file names."""
    return re.sub(r"[^\w\-]", "_", slug)


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------

def parse_page(html: str, category: str, page_number: int) -> list[dict]:
    """Extract raw template data from a single Imgflip listing page."""
    soup = BeautifulSoup(html, "html.parser")
    templates = []

    for box in soup.select("div.mt-box"):
        try:
            # Title & URL
            anchor = box.select_one("h3.mt-title a")
            if not anchor:
                continue
            href = anchor.get("href", "")          # /meme/{id}/{slug}
            title = anchor.get_text(strip=True)

            parts = href.strip("/").split("/")     # ['meme', id, slug]
            if len(parts) < 3:
                continue
            template_id = parts[1]
            slug = parts[2]

            # Image URL
            img = box.select_one("div.mt-img-wrap img")
            if not img:
                continue
            image_url = img.get("src", "")
            if image_url.startswith("//"):
                image_url = "https:" + image_url
            if not image_url:
                continue

            safe_slug = sanitise_slug(slug)
            local_image_path = f"{category}/images/{template_id}_{safe_slug}.jpg"

            templates.append({
                "template_id":       template_id,
                "title":             title,
                "slug":              slug,
                "template_page_url": f"https://imgflip.com/meme/{template_id}/{slug}",
                "image_url":         image_url,
                "local_image_path":  local_image_path,
                "source":            "imgflip",
                "category":          category,
                "page_number":       page_number,
                "downloaded_at":     None,          # filled after download
            })

        except Exception as exc:  # noqa: BLE001
            print(f"  [WARN] Skipping malformed template block: {exc}")

    return templates


# ---------------------------------------------------------------------------
# Image download
# ---------------------------------------------------------------------------

def download_image(url: str, dest: Path) -> bool:
    """Download an image with one retry. Returns True on success."""
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            return True
        except Exception as exc:  # noqa: BLE001
            if attempt == 0:
                print(f"    [RETRY] {url} — {exc}")
                time.sleep(REQUEST_DELAY)
            else:
                print(f"    [FAIL]  Could not download {url} — {exc}")
    return False


# ---------------------------------------------------------------------------
# Category scraper
# ---------------------------------------------------------------------------

def scrape_category(
    category: str,
    base_url: str,
    n_pages: int,
    global_seen: set[str],
) -> int:
    """Scrape one category. Returns the number of new templates saved."""

    jsonl_path = BASE_PATH / category / METADATA_FILES[category]
    existing_ids = load_existing_ids(jsonl_path)
    print(f"\n{'='*60}")
    print(f"Category : {category}")
    print(f"JSONL    : {jsonl_path}")
    print(f"Existing : {len(existing_ids)} template(s) already on disk")

    new_count = 0

    for page in range(1, n_pages + 1):
        page_url = base_url if page == 1 else f"{base_url}&page={page}"
        # Handle URLs that already carry a query param
        if "?" not in base_url:
            page_url = base_url if page == 1 else f"{base_url}?page={page}"

        print(f"\n  Page {page}: {page_url}")
        time.sleep(REQUEST_DELAY)

        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            print(f"  [ERROR] Could not fetch page {page}: {exc}")
            continue

        templates = parse_page(resp.text, category, page)
        print(f"  Found {len(templates)} template(s) on page {page}")

        for tmpl in templates:
            tid = tmpl["template_id"]

            # --- deduplication ---
            if tid in existing_ids or tid in global_seen:
                print(f"    [SKIP] {tid} already processed")
                continue

            # --- image download ---
            dest = BASE_PATH / tmpl["local_image_path"]
            success = download_image(tmpl["image_url"], dest)
            if not success:
                continue

            tmpl["downloaded_at"] = datetime.now(timezone.utc).isoformat()
            append_record(jsonl_path, tmpl)

            existing_ids.add(tid)
            global_seen.add(tid)
            new_count += 1
            print(f"    [OK]   {tmpl['title']} ({tid})")

            time.sleep(REQUEST_DELAY)

    print(f"\n  Done — {new_count} new template(s) saved for '{category}'")
    return new_count


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_scraper(n_pages: int = N_PAGES) -> None:
    print(f"Imgflip Template Scraper — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base path : {BASE_PATH}")
    print(f"Pages/cat : {n_pages}")

    setup_dirs()

    global_seen: set[str] = set()
    total_new = 0

    for category, base_url in CATEGORIES.items():
        total_new += scrape_category(category, base_url, n_pages, global_seen)

    print(f"\n{'='*60}")
    print(f"Scrape complete. Total new templates: {total_new}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Imgflip meme template scraper")
    parser.add_argument(
        "--pages",
        type=int,
        default=N_PAGES,
        help=f"Pages to scrape per category (default: {N_PAGES})",
    )
    args = parser.parse_args()
    run_scraper(n_pages=args.pages)
