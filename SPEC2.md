# SPEC2.md — CM50 Normalization and Merge into Local Template Dataset

## Purpose

This module prepares the local CM50 resource for integration into the template → archetype → RAG pipeline.

It performs two main tasks:

1. Convert the existing CM50 collective JSON into:
   - a collective JSONL file
   - individual JSON files per template

2. Merge CM50 information into the local template dataset by matching on the Imgflip template ID extracted from the template URL.

This stage does **not** generate archetypes yet.  
It only prepares and enriches the dataset so that a later LLM stage can use CM50 as a multishot source.

---

## Source Paths

### CM50 input directory
`/Users/vmac/prog/PY/semiotic_harm/RawCollection/cm50`

This directory contains:
- `50_template_info.json`
- individual template JSON files
- template images for the 50 templates

### Local template dataset
Assume this already exists and was built from Imgflip scraping.

If not hardcoded elsewhere, support a configurable base path such as:
`/Users/vmac/prog/PY/semiotic_harm/RawCollection/candidate_templates`

Subfolders may include:
- `top30/`
- `allTime/`
- `new/`

Each subfolder contains:
- `images/`
- metadata JSONL

---

## CM50 Input Schemas

### Per-template CM50 JSON
Example:

```json
{
  "title": "10 Guy Meme Template",
  "template_url": "https://imgflip.com/s/meme/10-Guy.jpg",
  "alternative_names": "Really High Guy, Stoner Stanley, Brainwashed Bob, stoned guy, ten guy, stoned buzzed high dude bro",
  "template_id": "101440",
  "format": "jpg",
  "dimensions": "500x454 px",
  "file_size": "24 KB"
}

Collective JSON structure

Example:

{
  "10-Guy": {
    "about": "[10] Guy ...",
    "example meme": "https://i.imgflip.com/3g89a4.jpg"
  }
}


⸻

Goals

Stage 1 — Normalize CM50

Create alongside the collective CM50 JSON:
	1.	A collective JSONL file containing one record per template
	2.	Individual normalized JSON files for each template, in the same style used in the local dataset

Stage 2 — Merge into local template dataset

For each template entry in the local dataset:
	•	match by Imgflip template ID
	•	if matching CM50 entry exists:
	•	update local JSON with CM50 fields
	•	set isCM50: true
	•	if no match:
	•	ensure isCM50: false

⸻

Matching Rule

Primary key

Match using the template ID.

Source of ID

Use the ID from:
	•	template_id field in CM50 individual JSON if available
	•	otherwise extract ID from CM50 template_url only if needed
	•	for local dataset, use existing template_id

Notes

Do not match by title alone unless explicitly used as fallback.
Title matching is too noisy.

⸻

Required Outputs

⸻

Output A — CM50 collective JSONL

Create:

/Users/vmac/prog/PY/semiotic_harm/RawCollection/cm50/50_template_info.jsonl

One line per template.

Suggested schema

{
  "template_key": "10-Guy",
  "template_id": "101440",
  "title": "10 Guy Meme Template",
  "template_url": "https://imgflip.com/s/meme/10-Guy.jpg",
  "alternative_names": [
    "Really High Guy",
    "Stoner Stanley",
    "Brainwashed Bob",
    "stoned guy",
    "ten guy",
    "stoned buzzed high dude bro"
  ],
  "format": "jpg",
  "dimensions": "500x454 px",
  "file_size": "24 KB",
  "cm50_about": "[10] Guy ...",
  "example_meme_url": "https://i.imgflip.com/3g89a4.jpg",
  "isCM50": true
}


⸻

Output B — normalized individual JSONs for CM50

Create a directory such as:

/Users/vmac/prog/PY/semiotic_harm/RawCollection/cm50/normalized_jsons/

Each template should have its own JSON file, for example:

101440_10-Guy.json

Suggested normalized schema

{
  "template_key": "10-Guy",
  "template_id": "101440",
  "title": "10 Guy Meme Template",
  "template_url": "https://imgflip.com/s/meme/10-Guy.jpg",
  "alternative_names": [
    "Really High Guy",
    "Stoner Stanley",
    "Brainwashed Bob",
    "stoned guy",
    "ten guy",
    "stoned buzzed high dude bro"
  ],
  "format": "jpg",
  "dimensions": "500x454 px",
  "file_size": "24 KB",
  "cm50_about": "[10] Guy ...",
  "example_meme_url": "https://i.imgflip.com/3g89a4.jpg",
  "isCM50": true,
  "source": ["cm50"]
}


⸻

Output C — updated local template dataset entries

Update local template JSON / JSONL records with CM50 enrichment.

Minimum fields to add or update

{
  "isCM50": true,
  "cm50_about": "...",
  "example_meme_url": "...",
  "cm50_template_key": "10-Guy",
  "cm50_title": "10 Guy Meme Template",
  "cm50_template_url": "https://imgflip.com/s/meme/10-Guy.jpg",
  "cm50_alternative_names": [
    "Really High Guy",
    "Stoner Stanley"
  ]
}

If no match:

{
  "isCM50": false
}

Important

This stage should not overwrite existing fields such as:
	•	archetype
	•	pragmatic_function
	•	template_reasoning
	•	caption_dependence

Those belong to the later LLM enrichment stage.

It may create them as empty/null only if required by downstream schema, but should not invent values.

⸻

Desired Future Unified Schema

The long-term target record for the local dataset is:

{
  "template_name": "The-Most-Interesting-Man-In-The-World",
  "source": ["imgflip", "cm50"],
  "imgflip_title": "The-Most-Interesting-Man-In-The-World",
  "cm50_about": "The Most Interesting Man In The World is an advice animal character inspired by ...",
  "example_meme_url": "https://i.imgflip.com/3j9guq.jpg",
  "archetype": "suave authority dispensing knowing advice",
  "pragmatic_function": "frames statements as culturally confident, superior, worldly observations",
  "caption_dependence": "medium",
  "template_reasoning": "The template inherits the persona of an unusually charismatic, worldly man whose statements are framed as refined and authoritative.",
  "needs_human_review": false
}

For this stage only

Only populate:
	•	source
	•	cm50_about
	•	example_meme_url
	•	CM50 metadata fields
	•	isCM50

Do not generate:
	•	archetype
	•	pragmatic_function
	•	caption_dependence
	•	template_reasoning

⸻

Merge Logic

Step 1

Load collective CM50 JSON.

Step 2

Load all CM50 individual JSON files.

Step 3

Join collective + per-template CM50 data into one normalized internal representation.

Step 4

Write:
	•	one collective JSONL
	•	one normalized individual JSON per template

Step 5

Load local dataset records from all template metadata JSONL files.

Expected local dataset sources may include:
	•	top30 metadata
	•	allTime metadata
	•	new metadata

Step 6

For each local record:
	•	read template_id
	•	if template_id exists in normalized CM50 map:
	•	enrich record
	•	append "cm50" to source if not already present
	•	set isCM50 = true
	•	else:
	•	set isCM50 = false

Step 7

Write updated local records back safely.

⸻

File Handling Strategy

Safe update requirement

Do not modify files in-place without backup.

Use one of these strategies:
	•	write new _updated.jsonl files
	•	or create .bak backups first

Preferred approach:
	•	create updated output files first
	•	preserve originals

Example:
	•	metadata_top30.jsonl → metadata_top30_cm50.jsonl
	•	metadata_allTime.jsonl → metadata_allTime_cm50.jsonl
	•	metadata_new.jsonl → metadata_new_cm50.jsonl

⸻

Alternative Names Handling

CM50 stores alternative_names as a comma-separated string.

Normalize to:
	•	list of strings
	•	trimmed whitespace
	•	remove empty values

Example:

[
  "Really High Guy",
  "Stoner Stanley",
  "Brainwashed Bob",
  "stoned guy",
  "ten guy",
  "stoned buzzed high dude bro"
]


⸻

Source Field Rules

If local record already has:

"source": ["imgflip"]

and a CM50 match is found, update to:

"source": ["imgflip", "cm50"]

Do not duplicate values.

If source is missing:
	•	initialize as list

⸻

Non-Goals

This script must not:
	•	run any LLM
	•	generate archetypes
	•	classify caption dependence
	•	infer pragmatic function
	•	create embeddings
	•	run RAG

This is strictly a normalization and merge stage.

⸻

Suggested Script Names

Script 1

normalize_cm50.py

Responsibilities:
	•	read collective JSON + per-template JSONs
	•	create collective JSONL
	•	create normalized individual JSONs

Script 2

merge_cm50_into_templates.py

Responsibilities:
	•	read normalized CM50 outputs
	•	read local dataset metadata
	•	enrich local records
	•	write updated metadata files

Optional:
These may be combined into one script if cleanly organized.

⸻

Recommended Python Structure

Functions for normalization
	•	load_cm50_collective_json(path)
	•	load_cm50_individual_jsons(cm50_dir)
	•	normalize_alternative_names(raw_str)
	•	build_cm50_record(template_key, individual_obj, collective_obj)
	•	write_cm50_jsonl(records, out_path)
	•	write_cm50_individual_jsons(records, out_dir)

Functions for merging
	•	load_local_template_metadata(jsonl_paths)
	•	merge_cm50_into_record(local_record, cm50_record)
	•	write_updated_jsonl(records, out_path)

⸻

Error Handling

Missing collective entry

If an individual CM50 template exists but no collective about entry exists:
	•	still create normalized record
	•	set cm50_about to empty string
	•	set example_meme_url to empty string if absent

Missing individual JSON

If a collective entry exists but no individual JSON exists:
	•	log warning
	•	skip unless enough info exists to create partial record

Missing template_id

If template_id missing in individual JSON:
	•	attempt extraction from template_url
	•	if still unavailable, log and skip

Malformed JSON
	•	log error
	•	continue processing remaining files

⸻

Logging

Use clear console logging, for example:
	•	[INFO] Loaded 50 collective CM50 entries
	•	[INFO] Loaded 50 individual template JSONs
	•	[OK] Wrote 50 records to 50_template_info.jsonl
	•	[OK] Updated 87 local template records with CM50 metadata
	•	[WARN] Missing individual JSON for ...
	•	[WARN] No CM50 match for local template_id=...

⸻

Success Criteria

The implementation is successful if:
	1.	A CM50 collective JSONL is created
	2.	Normalized individual JSON files are created
	3.	Local template dataset metadata is enriched using template ID matching
	4.	Matching records receive:
	•	isCM50: true
	•	cm50_about
	•	example_meme_url
	•	normalized CM50 metadata
	5.	Non-matching records receive:
	•	isCM50: false
	6.	Original local metadata files are preserved or backed up
	7.	No archetype inference is attempted yet

⸻

Final Note for Next Stage

After this normalization + merge stage, a later LLM-based script will use CM50 entries as multishot examples to generate:
	•	archetype
	•	pragmatic_function
	•	caption_dependence
	•	template_reasoning
	•	needs_human_review
