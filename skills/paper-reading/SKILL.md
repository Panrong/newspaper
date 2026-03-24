---
name: paper-reading
description: Use when the user wants to read, summarize, or ask questions about an academic paper from a URL (arXiv, OpenReview, HuggingFace, Semantic Scholar)
---

# Paper Reading

Download and read an academic paper, then summarize it or answer questions about it.

> **Cache:** This skill uses `scripts/cache.py` to cache downloaded PDFs and generated summaries. If the user asks for fresh data (e.g., "re-download", "ignore cache"), skip cache checks and proceed directly to downloading. New data is always written to cache.

## Workflow

### 1. Get the Paper URL

The user provides a paper URL. Supported sources:
- arXiv (`arxiv.org/abs/...`)
- OpenReview (`openreview.net/forum?id=...`)
- HuggingFace Papers (`huggingface.co/papers/...`)
- Semantic Scholar (`semanticscholar.org/paper/...`)
- Direct PDF links (`*.pdf`)

### 2. Download the PDF (cache-aware)

Check the cache for an existing download:

```bash
python <plugin_root>/scripts/cache.py check paper-reading "<url>" paper.pdf
```

- **Exit code 0 (cache hit):** the printed path is the cached PDF. Use it directly.
- **Exit code 1 (cache miss):** download the PDF, then cache it:

```bash
python <plugin_root>/scripts/resolve_and_download.py "<url>"
```

The script prints a temp file path. Cache the downloaded file:

```bash
python <plugin_root>/scripts/cache.py write paper-reading "<url>" paper.pdf --from-file <temp_file_path>
```

The write command prints the cache path. Use this path for reading.

### 3. Read the PDF

Use the Read tool on the PDF file path (either cached or newly downloaded). For large PDFs (more than 10 pages), read in chunks using the `pages` parameter (e.g., pages 1-10, then 11-20).

### 4. Respond Based on Intent (cache-aware)

**If no question was provided**, check for a cached summary:

```bash
python <plugin_root>/scripts/cache.py check paper-reading "<url>" summary.md
```

- **Cache hit:** read and return the cached summary.
- **Cache miss:** generate a summary using this format:

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

Write the summary to cache using the Write tool at the path returned by:

```bash
python <plugin_root>/scripts/cache.py path paper-reading "<url>" summary.md
```

**If a question was provided**, answer it grounded in the paper's content. Cite specific sections, figures, or tables where relevant. If the paper does not contain information to answer the question, say so. Do NOT write Q&A responses to `summary.md` — only default summaries are cached.
