# Newspaper Plugin — Design Spec

## Overview

`newspaper` is a Claude Code / OpenClaw plugin providing two skills for staying current with AI research and news. It follows the hybrid architecture: SKILL.md files orchestrate the host agent, Python helper scripts handle I/O (scraping, downloading, parsing).

## Skills

### `daily-briefing`

Produces a daily brief of AI papers and news filtered by the user's interests.

**Frontmatter:**
```yaml
---
name: daily-briefing
description: Use when the user wants a daily news brief, AI paper summary, or asks about today's papers/news from HuggingFace or smol.ai
---
```

**Workflow:**

1. Locate `topic-of-interest.md` in the project root. If not found, ask the user to create one. The file accepts two formats:
   - Simple list: one topic/keyword per line, all treated as equal weight.
   - Categorized: topics grouped under headings with descriptions for finer-grained filtering context.
2. Discover source scripts by scanning `scripts/sources/` for `.py` files.
3. Fetch all sources in parallel via Bash. Each source script outputs a JSON array to stdout with the schema: `{title, body, url, source_name, date, item_type}` where `item_type` is `"paper"` or `"news"`.
4. The host agent filters each item against the topics for relevance (yes/no judgment).
5. The host agent groups related items across sources (e.g., same paper on HuggingFace and smol.ai, same product launch from multiple sources) into unified entries with all source links cited.
6. Generate a structured markdown brief:

```markdown
# Daily Brief — YYYY-MM-DD

## Papers
- **Paper Title** — one-paragraph synthesis.
  Sources: [HuggingFace](…), [smol.ai](…)

## News
- **News Headline** — one-paragraph synthesis.
  Sources: [smol.ai](…)

## Filtered out
<list of titles that did not match topics>
```

7. Save to `briefs/YYYY-MM-DD-brief.md` and display a summary in the terminal.

### `paper-reading`

Reads and summarizes a paper from a URL, or answers a specific question about it.

**Frontmatter:**
```yaml
---
name: paper-reading
description: Use when the user wants to read, summarize, or ask questions about an academic paper from a URL (arXiv, OpenReview, HuggingFace, Semantic Scholar)
---
```

**Workflow:**

1. Receive a paper URL from the user.
2. Run `python scripts/resolve_and_download.py <url>` to resolve the URL to a PDF and download it. The script outputs the local file path to stdout.
3. The host agent reads the PDF using its built-in PDF Read tool.
4. Branch on user intent:
   - **No question provided** — summarize:
     ```markdown
     # Paper Summary: <Title>

     **Authors:** ...
     **Published:** ...
     **URL:** ...

     ## Key Idea
     One paragraph — the core contribution in plain language.

     ## Method
     How they did it, key technical choices.

     ## Results
     Main findings, benchmarks, comparisons.

     ## Limitations & Future Work
     What the authors acknowledge or what's missing.
     ```
   - **Question provided** — answer the question grounded in the paper's content, citing specific sections/figures.

## Architecture

### Plugin Structure

```
newspaper/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest for Claude Code
├── .opencode/
│   └── plugins/
│       └── newspaper.js         # OpenClaw integration
├── hooks/
│   ├── hooks.json               # SessionStart hook config
│   └── session-start            # Bootstrap script
├── skills/
│   ├── daily-briefing/
│   │   └── SKILL.md
│   └── paper-reading/
│       └── SKILL.md
├── scripts/
│   ├── sources/
│   │   ├── huggingface_papers.py
│   │   ├── smol_news.py
│   │   └── README.md            # Documents source interface
│   └── resolve_and_download.py
├── tests/
│   ├── fixtures/
│   │   ├── hf_papers_sample.html
│   │   ├── smol_news_sample.html
│   │   ├── arxiv_abs_page.html
│   │   └── topic_of_interest.md
│   ├── test_fetch_hf_papers.py
│   ├── test_fetch_smol_news.py
│   └── test_resolve_and_download.py
├── package.json
├── pyproject.toml
└── README.md
```

### Source Script Interface

Each source script in `scripts/sources/` must:

- Be a standalone Python script executable via `python scripts/sources/<name>.py`.
- Accept optional flags (e.g., `--method web|rss|email --email-path /path/to/mbox` for smol_news).
- Output a JSON array to stdout with the schema:
  ```json
  [
    {
      "title": "string",
      "body": "string (full rich text, may include markdown)",
      "url": "string",
      "source_name": "string (e.g. 'HuggingFace Daily Papers')",
      "date": "string (YYYY-MM-DD)",
      "item_type": "paper | news"
    }
  ]
  ```
- Exit 0 on success, non-zero with an error message on stderr on failure.

Users add new sources by creating a new `.py` file in `scripts/sources/` following this contract.

### URL Resolution Rules (`resolve_and_download.py`)

| Input URL pattern | Resolution |
|---|---|
| `arxiv.org/abs/XXXX` | `arxiv.org/pdf/XXXX.pdf` |
| `openreview.net/forum?id=XXX` | `openreview.net/pdf?id=XXX` |
| `huggingface.co/papers/XXXX` | Resolve to arXiv PDF via page metadata |
| `semanticscholar.org/paper/...` | Extract direct PDF link from page |
| Already a `.pdf` URL | Use directly |

Downloads to a temp file. Prints the local file path to stdout. Exits non-zero with error on failure.

### Python Dependencies

```toml
[project]
name = "newspaper"
version = "0.1.0"
dependencies = [
    "requests",
    "beautifulsoup4",
]
```

No PDF parsing library needed — the host agent reads PDFs natively.

### Plugin Packaging

**`package.json`:**
```json
{
  "name": "newspaper",
  "version": "0.1.0",
  "type": "module",
  "description": "Daily AI news briefing and paper reading skills for Claude Code and OpenClaw"
}
```

**`.claude-plugin/plugin.json`:**
```json
{
  "name": "newspaper",
  "description": "Daily briefing from AI news sources and paper reading/summarization",
  "version": "0.1.0",
  "author": "panrong",
  "license": "MIT",
  "keywords": ["news", "papers", "briefing", "arxiv", "huggingface"]
}
```

**Hooks:** `hooks/session-start` injects skill descriptions into session context at startup, following the superpowers pattern.

**OpenClaw:** `.opencode/plugins/newspaper.js` registers skill paths for auto-discovery.

## Testing Strategy

All tests use pytest with saved HTML fixtures and mocked HTTP responses.

### `test_fetch_hf_papers.py`
- Parse saved HuggingFace HTML fixture.
- Verify output schema (all required fields present, correct types).
- Verify `item_type` is `"paper"`.
- Edge cases: empty page, malformed HTML.

### `test_fetch_smol_news.py`
- Parse saved smol.ai HTML fixture.
- Verify output schema.
- Verify `item_type` is `"news"`.
- Test both web and RSS parsing paths.
- Edge cases: empty feed, malformed HTML.

### `test_resolve_and_download.py`
- Test URL resolution for each supported source (arXiv, OpenReview, HuggingFace, Semantic Scholar, direct PDF).
- Mock HTTP responses to avoid network dependency.
- Test error handling for unsupported URLs, download failures.

### What is NOT tested

LLM filtering, aggregation, and summarization are handled by the host agent at runtime and are inherently non-deterministic. Tests focus on the mechanical/deterministic parts only.

### Smoke test

Each source script can be run standalone and must produce valid JSON to stdout. A simple smoke test validates this against a live network (not run in CI).
