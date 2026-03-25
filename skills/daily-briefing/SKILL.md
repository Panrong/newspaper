---
name: daily-briefing
description: Use when the user wants a daily news brief, AI paper summary, or asks about today's papers/news from HuggingFace or smol.ai
---

# Daily Briefing

Produce a daily brief of AI papers and news for a **single date**, filtered by the user's interests and aggregated across sources.

> **Date:** If the user specifies a date, use that. Otherwise default to today's date (YYYY-MM-DD). Let `<date>` refer to this value throughout. Only items published on `<date>` are included.

> **Cache:** This skill uses `scripts/cache.py` to cache intermediate data. If the user asks for fresh data (e.g., "ignore cache", "re-fetch"), skip cache checks and proceed directly to fetching. New data is always written to cache.

## Workflow

### 1. Locate Topics

Find `topic-of-interest.md` in the current project root. If it does not exist, ask the user to create one. The file may be:

- A simple list (one topic per line, equal weight):
  ```
  LLM agents
  retrieval augmented generation
  code generation
  ```
- Categorized with descriptions:
  ```markdown
  ## Core interests
  - LLM agents: autonomous tool-using agents, planning, reflection

  ## Peripheral interests
  - Code generation: benchmarks, evaluation methods
  ```

Read the file and hold its contents for filtering. Compute a SHA-256 hash of the file's content (the "topics hash") for cache invalidation.

### 2. Fetch Sources (cache-aware)

Let `<date>` be today's date in YYYY-MM-DD format.

For each source script in `scripts/sources/`, check the cache before running:

```bash
python <plugin_root>/scripts/cache.py check daily-briefing <date> raw/<source_name>.json
```

- **Exit code 0 (cache hit):** read the file path printed to stdout. Use its contents.
- **Exit code 1 (cache miss):** run the source script with `--date` and pipe output to cache:

```bash
python <plugin_root>/scripts/sources/<source_name>.py --date <date> | python <plugin_root>/scripts/cache.py write daily-briefing <date> raw/<source_name>.json
```

The write command prints the cache file path. Read the cached file to get the data.

Each source is checked independently — one can be cached while the other re-fetches.

### 3. Filter for Relevance (cache-aware)

Check the cache for existing filter decisions:

```bash
python <plugin_root>/scripts/cache.py check daily-briefing <date> filter-decisions.json
```

**If cache hit:** read the file and check the `topics_hash` field. If it matches the current topics hash, reuse the decisions. If it does not match, treat as a cache miss.

**If cache miss:** for each fetched item, judge whether it is relevant to the user's topics. Consider both the title and body. Make a yes/no decision. Process items in batches (all titles and summaries at once) rather than one at a time.

Write the result as JSON via the Write tool to the path returned by:

```bash
python <plugin_root>/scripts/cache.py path daily-briefing <date> filter-decisions.json
```

Use this schema:

```json
{
  "topics_hash": "<sha256 of topic-of-interest.md content>",
  "topics_file": "<raw content of topic-of-interest.md>",
  "generated_at": "<ISO 8601 timestamp>",
  "decisions": [
    {
      "title": "Paper or News Title",
      "source": "huggingface_papers",
      "url": "https://...",
      "kept": true,
      "matched_topics": ["GUI Agent"],
      "reason": "Brief explanation of why this item was kept or filtered"
    }
  ]
}
```

### 4. Aggregate Across Sources (cache-aware)

Check the cache:

```bash
python <plugin_root>/scripts/cache.py check daily-briefing <date> aggregated.json
```

**If cache hit:** read the file and check `topics_hash`. If it matches, reuse. Otherwise treat as miss.

**If cache miss:** group items (where `kept: true` in filter decisions) that discuss the same underlying topic, event, or paper across different sources into a single entry. Cite all source URLs. If the same paper appears in both HuggingFace and smol.ai, merge into one entry under Papers. Preserve each item's `item_type` — `"news"` or `"paper"` — so the brief can render them in the correct section.

Write the result to the path returned by:

```bash
python <plugin_root>/scripts/cache.py path daily-briefing <date> aggregated.json
```

Use this schema:

```json
{
  "topics_hash": "<sha256 of topic-of-interest.md content>",
  "generated_at": "<ISO 8601 timestamp>",
  "items": [
    {
      "title": "Merged Paper Title",
      "item_type": "paper",
      "summary": "One-paragraph synthesis...",
      "sources": [
        {"name": "HuggingFace", "url": "https://..."},
        {"name": "smol.ai", "url": "https://..."}
      ]
    }
  ]
}
```

### 5. Generate Brief

Write a structured markdown brief. Items are categorized by their `item_type` field: `"news"` or `"paper"`. The filtered-out list comes from `filter-decisions.json` (items where `kept: false`).

**News items use their original text** — do not summarize or rewrite. Copy the body as-is. Show all URLs from the `urls` field as links. Papers may be synthesized into one-paragraph summaries.

News section comes **before** the Papers section:

```markdown
# Daily Brief — YYYY-MM-DD

## News
- **Title** — original body text, not summarized.
  Links: [label1](url1), [label2](url2)

## Papers
- **Paper Title** — one-paragraph synthesis of the paper's contribution.
  Sources: [HuggingFace](url), [smol.ai](url)

## Filtered out
- Title 1
- Title 2
```

### 6. Save and Display

1. Create the `briefs/` directory if it does not exist.
2. Write the brief to `briefs/YYYY-MM-DD-brief.md`.
3. Display a concise summary in the terminal.
