---
name: daily-briefing
description: Use when the user wants a daily news brief, AI paper summary, or asks about today's papers/news from HuggingFace or smol.ai
---

# Daily Briefing

Produce a daily brief of AI papers and news, filtered by the user's interests and aggregated across sources.

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

Read the file and hold its contents for filtering.

### 2. Fetch Sources

Discover all `.py` files in `scripts/sources/` relative to this plugin's root directory. Run each source script in parallel via Bash:

```bash
python <plugin_root>/scripts/sources/huggingface_papers.py
python <plugin_root>/scripts/sources/smol_news.py
```

Each script outputs a JSON array to stdout. Parse the JSON from each.

### 3. Filter for Relevance

For each fetched item, judge whether it is relevant to the user's topics. Consider both the title and body. Make a yes/no decision. Process items in batches (all titles and summaries at once) rather than one at a time.

### 4. Aggregate Across Sources

Group items that discuss the same underlying topic, event, or paper across different sources into a single entry. Cite all source URLs. If the same paper appears in both HuggingFace and smol.ai, merge into one entry under Papers.

### 5. Generate Brief

Write a structured markdown brief. Items are categorized as either Papers or News based on their `item_type` field:

```markdown
# Daily Brief — YYYY-MM-DD

## Papers
- **Paper Title** — one-paragraph synthesis of the paper's contribution.
  Sources: [HuggingFace](url), [smol.ai](url)

## News
- **News Headline** — one-paragraph synthesis of the news item.
  Sources: [smol.ai](url)

## Filtered out
- Title 1
- Title 2
```

### 6. Save and Display

1. Create the `briefs/` directory if it does not exist.
2. Write the brief to `briefs/YYYY-MM-DD-brief.md`.
3. Display a concise summary in the terminal.
