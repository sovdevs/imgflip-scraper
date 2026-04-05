# SPEC3.md — Archetype Enrichment (Spiral 1)

## Overview

This module performs archetype inference for each template in the local dataset using:

- CM50 curated template explanations
- Prompt-based reasoning via LangChain
- Multishot prompting grounded in CM50 examples

The goal is to generate:

- archetype
- pragmatic_function
- caption_dependence
- template_reasoning
- needs_human_review

This stage does NOT involve:
- fine-tuning
- RAG retrieval
- embeddings

It is purely prompt-based reasoning.

---

## Input Data

### Local template dataset
From previous stage:

candidate_templates/.../metadata_*_cm50.jsonl

Each record contains:
- template_id
- title
- image path
- optional cm50_about
- optional example_meme_url
- isCM50 flag

---

### CM50 normalized dataset

From previous stage:

cm50/50_template_info.jsonl

Contains:
- template_name
- cm50_about
- alternative_names
- example_meme_url

---

## Output

Updated JSONL files:

metadata_*_cm50_enriched.jsonl

Each record must include:

{
  "template_name": "...",
  "archetype": "...",
  "pragmatic_function": "...",
  "caption_dependence": "...",
  "template_reasoning": "...",
  "needs_human_review": false
}

---

## Core Idea

For each template:

- Use CM50 entries as **few-shot reasoning examples**
- Inject them into prompt
- Ask LLM to infer archetype-level meaning

---

## Prompt Design

### System Prompt

You are analyzing meme templates at the archetype level.

Your task is not to explain a specific meme instance, but to explain the reusable communicative function of a template.

---

### Few-shot Examples (from CM50)

Each example should include:

Template Name  
About (CM50)  
Structured Output



## Few-Shot Selection Strategy (Spiral 0)

In this initial implementation (Spiral 0), few-shot examples are selected from the CM50 dataset using a **fixed random sampling strategy**.

### Rationale

Few-shot examples guide the model in mapping:
- template → archetype
- template → pragmatic function

However, fully random selection introduces variability and reduces reproducibility. To ensure consistent and stable outputs during development and evaluation, a fixed random seed is used.

---

## Implementation Details

- Number of few-shot examples: **K = 3**
- Selection method: `random.sample`
- Random seed: **42 (fixed)**

Example:

```python
import random

random.seed(42)
few_shot_examples = random.sample(cm50_examples, 3)

---

### Example format

Template: The Most Interesting Man In The World

About:
The Most Interesting Man In The World is an advice animal character inspired by...

Output:
{
  "archetype": "suave authority dispensing knowing advice",
  "pragmatic_function": "frames statements as culturally confident, superior, worldly observations",
  "caption_dependence": "medium",
  "template_reasoning": "The template inherits the persona of..."
}

---

### Input Template

Template: {title}

CM50 About (if available): {cm50_about}

Alternative Names: {alternative_names}

Image Path: {image_path}

---

### Required Output Format

Strict JSON:

{
  "template_name": "...",
  "archetype": "...",
  "pragmatic_function": "...",
  "caption_dependence": "low|medium|high",
  "template_reasoning": "...",
  "needs_human_review": false
}

---

## Model Selection

Use a strong multimodal or reasoning-capable LLM.

Recommended:

- GPT-4o / GPT-5 (best)
- Claude Sonnet (fallback)
- Gemini Pro (optional)

Temperature: 0.2–0.4

---

## LangChain Implementation

Use:

- PromptTemplate
- RunnableSequence or LCEL
- Optional batching

---

## Processing Flow

For each template record:

1. Load template metadata
2. Select K CM50 examples (K = 2–3)
3. Build prompt:
   - system instruction
   - CM50 few-shot examples
   - current template
4. Invoke LLM
5. Parse JSON output
6. Append fields to record
7. Write to new JSONL

---

## CM50 Usage Strategy

### Do NOT:
- run retrieval over CM50
- embed CM50
- filter dynamically (yet)

### DO:
- randomly sample or preselect 2–3 CM50 examples
- keep prompt stable

---

## Handling Missing CM50

If template has no CM50 entry:

- still run inference
- leave CM50 section empty
- rely on:
  - title
  - image (if model supports it)

---

## Deduplication

Skip templates already enriched:
- check if "archetype" exists

---

## Error Handling

If JSON parsing fails:
- retry once
- fallback:
  needs_human_review = true

---

## Logging

Print:

[INFO] Processing template: X  
[OK] Archetype generated  
[WARN] Missing CM50  
[ERROR] JSON parse failed  

---

## Output Example

{
  "template_name": "Matrix Morpheus",
  "archetype": "revealing hidden truth / corrective contrarianism",
  "pragmatic_function": "frames statements as revelations that challenge common beliefs",
  "caption_dependence": "medium",
  "template_reasoning": "The template uses Morpheus as a figure of epistemic authority revealing hidden truths.",
  "needs_human_review": false
}

---

## Future Extensions (NOT NOW)

- RAG-based template lookup
- embedding similarity
- human review UI
- confidence scoring

---

## Success Criteria

- All templates enriched
- Valid JSON output
- No crashes
- Meaningful archetypes generated