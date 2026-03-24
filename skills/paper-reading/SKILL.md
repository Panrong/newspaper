---
name: paper-reading
description: Use when the user wants to read, summarize, or ask questions about an academic paper from a URL (arXiv, OpenReview, HuggingFace, Semantic Scholar)
---

# Paper Reading

Download and read an academic paper, then summarize it or answer questions about it.

## Workflow

### 1. Get the Paper URL

The user provides a paper URL. Supported sources:
- arXiv (`arxiv.org/abs/...`)
- OpenReview (`openreview.net/forum?id=...`)
- HuggingFace Papers (`huggingface.co/papers/...`)
- Semantic Scholar (`semanticscholar.org/paper/...`)
- Direct PDF links (`*.pdf`)

### 2. Download the PDF

Run the resolver script via Bash:

```bash
python <plugin_root>/scripts/resolve_and_download.py "<url>"
```

The script prints the local file path to stdout. If it fails, report the error to the user.

### 3. Read the PDF

Use the Read tool on the downloaded PDF file path. For large PDFs (more than 10 pages), read in chunks using the `pages` parameter (e.g., pages 1-10, then 11-20).

### 4. Respond Based on Intent

**If no question was provided**, summarize the paper:

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

**If a question was provided**, answer it grounded in the paper's content. Cite specific sections, figures, or tables where relevant. If the paper does not contain information to answer the question, say so.

### 5. Cleanup

Delete the downloaded temp PDF file after reading:

```bash
rm <temp_file_path>
```
