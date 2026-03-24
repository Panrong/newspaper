# Newspaper Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code / OpenClaw plugin with two skills (`daily-briefing`, `paper-reading`) and Python helper scripts for fetching AI papers and news.

**Architecture:** Hybrid — SKILL.md files orchestrate the host agent's reasoning (filtering, summarizing), Python scripts handle I/O (API calls, RSS parsing, PDF downloading). Extensible source system via `scripts/sources/` directory.

**Tech Stack:** Python 3.10+, requests, beautifulsoup4, pytest. HuggingFace JSON API, smol.ai RSS feed. No LLM SDK — the host agent does all reasoning.

**Spec:** `docs/superpowers/specs/2026-03-24-newspaper-design.md`

---

### Task 1: Project Scaffolding

**Files:**
- Create: `package.json`
- Create: `pyproject.toml`
- Create: `.claude-plugin/plugin.json`
- Create: `scripts/sources/` (directory)
- Create: `tests/fixtures/` (directory)

- [ ] **Step 1: Create package.json**

```json
{
  "name": "newspaper",
  "version": "0.1.0",
  "type": "module",
  "description": "Daily AI news briefing and paper reading skills for Claude Code and OpenClaw"
}
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "newspaper"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "requests",
    "beautifulsoup4",
]

[project.optional-dependencies]
dev = [
    "pytest",
]
```

- [ ] **Step 3: Create .claude-plugin/plugin.json**

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

- [ ] **Step 4: Create directory structure**

```bash
mkdir -p scripts/sources tests/fixtures skills/daily-briefing skills/paper-reading
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -e ".[dev]"
```

- [ ] **Step 6: Commit**

```bash
git add package.json pyproject.toml .claude-plugin/plugin.json
git commit -m "feat: add project scaffolding and plugin manifest"
```

---

### Task 2: HuggingFace Papers Source Script — Tests

**Files:**
- Create: `tests/fixtures/hf_daily_papers_response.json`
- Create: `tests/test_fetch_hf_papers.py`

- [ ] **Step 1: Save a fixture of the HuggingFace API response**

Fetch `https://huggingface.co/api/daily_papers` and save 3-5 entries as `tests/fixtures/hf_daily_papers_response.json`. The API returns:

```json
[
  {
    "paper": {
      "id": "2603.21489",
      "title": "Effective Strategies for Asynchronous Software Engineering Agents",
      "summary": "AI agents have become increasingly capable...",
      "authors": [{"name": "Jiayi Geng", "hidden": false}, {"name": "Graham Neubig", "hidden": false}],
      "publishedAt": "2026-03-23T02:26:35.000Z",
      "ai_summary": "Multi-agent collaboration...",
      "ai_keywords": ["multi-agent", "software engineering"]
    }
  }
]
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_fetch_hf_papers.py
import json
import os
from unittest.mock import patch, MagicMock

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return f.read()


def test_parse_hf_papers_returns_list():
    """Parsing the API response should return a list of dicts."""
    from scripts.sources.huggingface_papers import parse_papers

    raw = json.loads(load_fixture("hf_daily_papers_response.json"))
    result = parse_papers(raw)
    assert isinstance(result, list)
    assert len(result) > 0


def test_parse_hf_papers_schema():
    """Each item must have the required fields with correct types."""
    from scripts.sources.huggingface_papers import parse_papers

    raw = json.loads(load_fixture("hf_daily_papers_response.json"))
    result = parse_papers(raw)
    for item in result:
        assert isinstance(item["title"], str)
        assert isinstance(item["body"], str)
        assert isinstance(item["url"], str)
        assert item["source_name"] == "HuggingFace Daily Papers"
        assert isinstance(item["date"], str)
        assert item["item_type"] == "paper"


def test_parse_hf_papers_url_format():
    """URL should point to the HuggingFace paper page."""
    from scripts.sources.huggingface_papers import parse_papers

    raw = json.loads(load_fixture("hf_daily_papers_response.json"))
    result = parse_papers(raw)
    for item in result:
        assert item["url"].startswith("https://huggingface.co/papers/")


def test_parse_hf_papers_body_contains_abstract():
    """Body should include the paper abstract/summary."""
    from scripts.sources.huggingface_papers import parse_papers

    raw = json.loads(load_fixture("hf_daily_papers_response.json"))
    result = parse_papers(raw)
    for item in result:
        assert len(item["body"]) > 20


def test_parse_hf_papers_empty_input():
    """Empty API response should return empty list."""
    from scripts.sources.huggingface_papers import parse_papers

    result = parse_papers([])
    assert result == []


@patch("scripts.sources.huggingface_papers.requests.get")
def test_fetch_papers_calls_api(mock_get):
    """fetch_papers should call the HuggingFace API."""
    from scripts.sources.huggingface_papers import fetch_papers

    mock_response = MagicMock()
    mock_response.json.return_value = json.loads(
        load_fixture("hf_daily_papers_response.json")
    )
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = fetch_papers()
    mock_get.assert_called_once_with(
        "https://huggingface.co/api/daily_papers", timeout=30
    )
    assert isinstance(result, list)
    assert len(result) > 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_fetch_hf_papers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.sources.huggingface_papers'`

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/hf_daily_papers_response.json tests/test_fetch_hf_papers.py
git commit -m "test: add failing tests for HuggingFace papers source script"
```

---

### Task 3: HuggingFace Papers Source Script — Implementation

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/sources/__init__.py`
- Create: `scripts/sources/huggingface_papers.py`

- [ ] **Step 1: Create __init__.py files for package imports**

Create empty `scripts/__init__.py` and `scripts/sources/__init__.py`.

- [ ] **Step 2: Implement huggingface_papers.py**

```python
#!/usr/bin/env python3
"""Fetch today's papers from HuggingFace Daily Papers API.

Outputs a JSON array to stdout with the source script interface schema:
  [{title, body, url, source_name, date, item_type}]
"""
import json
import sys
from datetime import datetime

import requests


API_URL = "https://huggingface.co/api/daily_papers"


def parse_papers(api_response: list[dict]) -> list[dict]:
    """Parse the HuggingFace API response into the common source schema."""
    results = []
    for entry in api_response:
        paper = entry.get("paper", entry)
        published = paper.get("publishedAt", "")
        try:
            date_str = datetime.fromisoformat(
                published.replace("Z", "+00:00")
            ).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            date_str = datetime.now().strftime("%Y-%m-%d")

        authors = ", ".join(
            a["name"] for a in paper.get("authors", []) if not a.get("hidden")
        )
        abstract = paper.get("summary", "")
        ai_summary = paper.get("ai_summary", "")
        body_parts = []
        if authors:
            body_parts.append(f"**Authors:** {authors}")
        if abstract:
            body_parts.append(abstract)
        if ai_summary:
            body_parts.append(f"**AI Summary:** {ai_summary}")

        results.append(
            {
                "title": paper.get("title", "Untitled"),
                "body": "\n\n".join(body_parts),
                "url": f"https://huggingface.co/papers/{paper['id']}",
                "source_name": "HuggingFace Daily Papers",
                "date": date_str,
                "item_type": "paper",
            }
        )
    return results


def fetch_papers() -> list[dict]:
    """Fetch and parse today's papers from the HuggingFace API."""
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    return parse_papers(response.json())


if __name__ == "__main__":
    try:
        papers = fetch_papers()
        print(json.dumps(papers, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_fetch_hf_papers.py -v`
Expected: All 6 tests PASS

- [ ] **Step 4: Commit**

```bash
git add scripts/__init__.py scripts/sources/__init__.py scripts/sources/huggingface_papers.py
git commit -m "feat: implement HuggingFace daily papers source script"
```

---

### Task 4: Smol News Source Script — Tests

**Files:**
- Create: `tests/fixtures/smol_news_rss.xml`
- Create: `tests/test_fetch_smol_news.py`

- [ ] **Step 1: Save a fixture of the smol.ai RSS response**

Fetch `https://news.smol.ai/rss.xml` and save 3-5 entries as `tests/fixtures/smol_news_rss.xml`. The RSS contains `<item>` elements with `<title>`, `<link>`, `<description>`, `<pubDate>`, `<content:encoded>`, and `<category>` tags.

- [ ] **Step 2: Write failing tests**

```python
# tests/test_fetch_smol_news.py
import os
from unittest.mock import patch, MagicMock

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return f.read()


def test_parse_rss_returns_list():
    """Parsing RSS XML should return a list of dicts."""
    from scripts.sources.smol_news import parse_rss

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    assert isinstance(result, list)
    assert len(result) > 0


def test_parse_rss_schema():
    """Each item must have the required fields with correct types."""
    from scripts.sources.smol_news import parse_rss

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    for item in result:
        assert isinstance(item["title"], str)
        assert isinstance(item["body"], str)
        assert isinstance(item["url"], str)
        assert item["source_name"] == "smol.ai AI News"
        assert isinstance(item["date"], str)
        assert item["item_type"] == "news"


def test_parse_rss_body_uses_content_encoded():
    """Body should use content:encoded (full HTML content) when available."""
    from scripts.sources.smol_news import parse_rss

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    for item in result:
        # content:encoded is typically much longer than description
        assert len(item["body"]) > 20


def test_parse_rss_date_format():
    """Date should be in YYYY-MM-DD format."""
    from scripts.sources.smol_news import parse_rss
    import re

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    for item in result:
        assert re.match(r"\d{4}-\d{2}-\d{2}", item["date"])


def test_parse_rss_empty_input():
    """Empty RSS feed should return empty list."""
    from scripts.sources.smol_news import parse_rss

    xml = '<?xml version="1.0"?><rss><channel></channel></rss>'
    result = parse_rss(xml)
    assert result == []


@patch("scripts.sources.smol_news.requests.get")
def test_fetch_news_calls_rss(mock_get):
    """fetch_news should fetch the RSS feed URL."""
    from scripts.sources.smol_news import fetch_news

    mock_response = MagicMock()
    mock_response.text = load_fixture("smol_news_rss.xml")
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = fetch_news()
    mock_get.assert_called_once_with(
        "https://news.smol.ai/rss.xml", timeout=30
    )
    assert isinstance(result, list)
    assert len(result) > 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_fetch_smol_news.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.sources.smol_news'`

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/smol_news_rss.xml tests/test_fetch_smol_news.py
git commit -m "test: add failing tests for smol.ai news source script"
```

---

### Task 5: Smol News Source Script — Implementation

**Files:**
- Create: `scripts/sources/smol_news.py`

- [ ] **Step 1: Implement smol_news.py**

```python
#!/usr/bin/env python3
"""Fetch news from smol.ai AI News RSS feed.

Outputs a JSON array to stdout with the source script interface schema:
  [{title, body, url, source_name, date, item_type}]
"""
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests


RSS_URL = "https://news.smol.ai/rss.xml"
CONTENT_NS = {"content": "http://purl.org/rss/1.0/modules/content/"}


def parse_rss(xml_text: str) -> list[dict]:
    """Parse smol.ai RSS XML into the common source schema."""
    root = ET.fromstring(xml_text)
    results = []

    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_date_el = item.find("pubDate")
        description_el = item.find("description")
        content_el = item.find("content:encoded", CONTENT_NS)

        title = title_el.text if title_el is not None and title_el.text else ""
        url = link_el.text if link_el is not None and link_el.text else ""

        # Prefer content:encoded (full article) over description (summary)
        if content_el is not None and content_el.text:
            body = content_el.text
        elif description_el is not None and description_el.text:
            body = description_el.text
        else:
            body = ""

        # Parse RFC 2822 date to YYYY-MM-DD
        date_str = datetime.now().strftime("%Y-%m-%d")
        if pub_date_el is not None and pub_date_el.text:
            try:
                dt = parsedate_to_datetime(pub_date_el.text)
                date_str = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        results.append(
            {
                "title": title,
                "body": body,
                "url": url,
                "source_name": "smol.ai AI News",
                "date": date_str,
                "item_type": "news",
            }
        )
    return results


def fetch_news() -> list[dict]:
    """Fetch and parse news from the smol.ai RSS feed."""
    response = requests.get(RSS_URL, timeout=30)
    response.raise_for_status()
    return parse_rss(response.text)


if __name__ == "__main__":
    try:
        news = fetch_news()
        print(json.dumps(news, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/test_fetch_smol_news.py -v`
Expected: All 6 tests PASS

- [ ] **Step 3: Commit**

```bash
git add scripts/sources/smol_news.py
git commit -m "feat: implement smol.ai news RSS source script"
```

---

### Task 6: URL Resolver & PDF Downloader — Tests

**Files:**
- Create: `tests/test_resolve_and_download.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_resolve_and_download.py
import os
import tempfile
from unittest.mock import patch, MagicMock

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def test_resolve_arxiv_abs():
    """arXiv abstract URL should resolve to PDF URL."""
    from scripts.resolve_and_download import resolve_pdf_url

    url = "https://arxiv.org/abs/2401.12345"
    assert resolve_pdf_url(url) == "https://arxiv.org/pdf/2401.12345.pdf"


def test_resolve_arxiv_abs_versioned():
    """arXiv versioned abstract URL should resolve to versioned PDF URL."""
    from scripts.resolve_and_download import resolve_pdf_url

    url = "https://arxiv.org/abs/2401.12345v2"
    assert resolve_pdf_url(url) == "https://arxiv.org/pdf/2401.12345v2.pdf"


def test_resolve_openreview():
    """OpenReview forum URL should resolve to PDF URL."""
    from scripts.resolve_and_download import resolve_pdf_url

    url = "https://openreview.net/forum?id=abc123"
    assert resolve_pdf_url(url) == "https://openreview.net/pdf?id=abc123"


def test_resolve_direct_pdf():
    """Direct PDF URL should be returned as-is."""
    from scripts.resolve_and_download import resolve_pdf_url

    url = "https://example.com/paper.pdf"
    assert resolve_pdf_url(url) == "https://example.com/paper.pdf"


def test_resolve_huggingface_paper():
    """HuggingFace paper URL should resolve to arXiv PDF."""
    from scripts.resolve_and_download import resolve_pdf_url

    url = "https://huggingface.co/papers/2401.12345"
    assert resolve_pdf_url(url) == "https://arxiv.org/pdf/2401.12345.pdf"


@patch("scripts.resolve_and_download.requests.get")
def test_resolve_semantic_scholar(mock_get):
    """Semantic Scholar URL should resolve by extracting PDF link from page."""
    from scripts.resolve_and_download import resolve_pdf_url

    mock_response = MagicMock()
    mock_response.text = '<a href="https://arxiv.org/pdf/2401.12345.pdf" class="pdf-link">PDF</a>'
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    url = "https://www.semanticscholar.org/paper/Some-Title/abc123"
    assert resolve_pdf_url(url) == "https://arxiv.org/pdf/2401.12345.pdf"


def test_resolve_unsupported_url_raises():
    """Unsupported URL should raise ValueError."""
    from scripts.resolve_and_download import resolve_pdf_url
    import pytest

    with pytest.raises(ValueError, match="Unsupported"):
        resolve_pdf_url("https://example.com/not-a-paper")


@patch("scripts.resolve_and_download.requests.get")
def test_download_pdf(mock_get):
    """download_pdf should save content to a temp file and return the path."""
    from scripts.resolve_and_download import download_pdf

    mock_response = MagicMock()
    mock_response.content = b"%PDF-1.4 fake pdf content"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    path = download_pdf("https://arxiv.org/pdf/2401.12345.pdf")
    try:
        assert os.path.exists(path)
        assert path.endswith(".pdf")
        with open(path, "rb") as f:
            assert f.read() == b"%PDF-1.4 fake pdf content"
    finally:
        os.unlink(path)


@patch("scripts.resolve_and_download.requests.get")
def test_resolve_and_download_integration(mock_get):
    """resolve_and_download should resolve URL then download."""
    from scripts.resolve_and_download import resolve_and_download

    mock_response = MagicMock()
    mock_response.content = b"%PDF-1.4 fake pdf content"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    path = resolve_and_download("https://arxiv.org/abs/2401.12345")
    try:
        assert os.path.exists(path)
        mock_get.assert_called_once_with(
            "https://arxiv.org/pdf/2401.12345.pdf", timeout=60
        )
    finally:
        os.unlink(path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_resolve_and_download.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.resolve_and_download'`

Note: 9 tests total in this file (6 resolve + 1 Semantic Scholar mocked + 1 download + 1 integration).

- [ ] **Step 3: Commit**

```bash
git add tests/test_resolve_and_download.py
git commit -m "test: add failing tests for URL resolver and PDF downloader"
```

---

### Task 7: URL Resolver & PDF Downloader — Implementation

**Files:**
- Create: `scripts/resolve_and_download.py`

- [ ] **Step 1: Implement resolve_and_download.py**

```python
#!/usr/bin/env python3
"""Resolve a paper URL to its PDF and download it.

Supports: arXiv, OpenReview, HuggingFace Papers, Semantic Scholar, direct PDF.
Prints the local file path to stdout on success.
"""
import re
import sys
import tempfile
from urllib.parse import urlparse, parse_qs

import requests


def resolve_pdf_url(url: str) -> str:
    """Resolve a paper URL to a direct PDF URL."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path

    # Direct PDF link
    if path.endswith(".pdf"):
        return url

    # arXiv: /abs/XXXX → /pdf/XXXX.pdf
    if "arxiv.org" in host:
        match = re.match(r"/abs/(.+)", path)
        if match:
            paper_id = match.group(1)
            return f"https://arxiv.org/pdf/{paper_id}.pdf"

    # OpenReview: /forum?id=XXX → /pdf?id=XXX
    if "openreview.net" in host and path == "/forum":
        query = parse_qs(parsed.query)
        paper_id = query.get("id", [None])[0]
        if paper_id:
            return f"https://openreview.net/pdf?id={paper_id}"

    # HuggingFace Papers: /papers/XXXX → arXiv PDF
    if "huggingface.co" in host:
        match = re.match(r"/papers/(.+)", path)
        if match:
            paper_id = match.group(1)
            return f"https://arxiv.org/pdf/{paper_id}.pdf"

    # Semantic Scholar: fetch page and extract PDF link
    if "semanticscholar.org" in host:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        # Look for direct PDF link in the page
        pdf_match = re.search(r'href="(https://[^"]+\.pdf)"', resp.text)
        if pdf_match:
            return pdf_match.group(1)

    raise ValueError(f"Unsupported URL or could not resolve PDF: {url}")


def download_pdf(pdf_url: str) -> str:
    """Download a PDF from a URL to a temp file. Returns the file path."""
    response = requests.get(pdf_url, timeout=60)
    response.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(response.content)
    tmp.close()
    return tmp.name


def resolve_and_download(url: str) -> str:
    """Resolve a paper URL to PDF and download it. Returns local file path."""
    pdf_url = resolve_pdf_url(url)
    return download_pdf(pdf_url)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: resolve_and_download.py <url>", file=sys.stderr)
        sys.exit(1)
    try:
        path = resolve_and_download(sys.argv[1])
        print(path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/test_resolve_and_download.py -v`
Expected: All 9 tests PASS

- [ ] **Step 3: Commit**

```bash
git add scripts/resolve_and_download.py
git commit -m "feat: implement URL resolver and PDF downloader"
```

---

### Task 8: Source Interface Documentation

**Files:**
- Create: `scripts/sources/README.md`

- [ ] **Step 1: Write the source interface README**

```markdown
# Source Scripts

Each Python script in this directory is a news/paper source for the `daily-briefing` skill.

## Interface

Each source script must:

1. Be executable via `python scripts/sources/<name>.py`
2. Output a JSON array to **stdout** with this schema:

```json
[
  {
    "title": "Item title",
    "body": "Full text content (may include markdown/HTML)",
    "url": "https://link-to-original",
    "source_name": "Human-readable source name",
    "date": "YYYY-MM-DD",
    "item_type": "paper | news"
  }
]
```

3. Exit `0` on success
4. Exit non-zero with an error message on **stderr** on failure

## Adding a New Source

Create a new `.py` file in this directory following the interface above. The
`daily-briefing` skill auto-discovers all `.py` files in this directory.

## Optional Flags

Source scripts may accept flags for configuration. For example:

```bash
python scripts/sources/smol_news.py --method rss   # default
python scripts/sources/smol_news.py --method web    # scrape website
```
```

- [ ] **Step 2: Commit**

```bash
git add scripts/sources/README.md
git commit -m "docs: add source script interface documentation"
```

---

### Task 9: `daily-briefing` SKILL.md

**Files:**
- Create: `skills/daily-briefing/SKILL.md`

- [ ] **Step 1: Write the skill file**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/daily-briefing/SKILL.md
git commit -m "feat: add daily-briefing skill"
```

---

### Task 10: `paper-reading` SKILL.md

**Files:**
- Create: `skills/paper-reading/SKILL.md`

- [ ] **Step 1: Write the skill file**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/paper-reading/SKILL.md
git commit -m "feat: add paper-reading skill"
```

---

### Task 11: Plugin Hooks & Integration

**Files:**
- Create: `hooks/hooks.json`
- Create: `hooks/session-start`
- Create: `.opencode/plugins/newspaper.js`

- [ ] **Step 1: Create hooks/hooks.json**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/session-start\"",
            "async": false
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Create hooks/session-start**

```bash
#!/usr/bin/env bash
# Inject newspaper skill descriptions into the session context.
set -e

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Read skill descriptions from SKILL.md frontmatter
NEWS_DESC=""
PAPER_DESC=""

if [ -f "$PLUGIN_ROOT/skills/daily-briefing/SKILL.md" ]; then
  NEWS_DESC=$(sed -n 's/^description: //p' "$PLUGIN_ROOT/skills/daily-briefing/SKILL.md" | head -1)
fi

if [ -f "$PLUGIN_ROOT/skills/paper-reading/SKILL.md" ]; then
  PAPER_DESC=$(sed -n 's/^description: //p' "$PLUGIN_ROOT/skills/paper-reading/SKILL.md" | head -1)
fi

CONTEXT="The following newspaper skills are available:
- daily-briefing: ${NEWS_DESC}
- paper-reading: ${PAPER_DESC}"

# Escape for JSON
ESCAPED=$(echo "$CONTEXT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")

cat <<EOF
{
  "hookResponse": {
    "additionalContext": ${ESCAPED}
  }
}
EOF
```

- [ ] **Step 3: Make session-start executable**

```bash
chmod +x hooks/session-start
```

- [ ] **Step 4: Create .opencode/plugins/newspaper.js**

```javascript
// OpenClaw plugin integration for newspaper
export default {
  name: "newspaper",
  skills: {
    "daily-briefing": {
      path: "skills/daily-briefing/SKILL.md",
    },
    "paper-reading": {
      path: "skills/paper-reading/SKILL.md",
    },
  },
};
```

- [ ] **Step 5: Commit**

```bash
git add hooks/hooks.json hooks/session-start .opencode/plugins/newspaper.js
git commit -m "feat: add plugin hooks and OpenClaw integration"
```

---

### Task 12: Smoke Test Script

**Files:**
- Create: `tests/smoke_test.sh`

- [ ] **Step 1: Write the smoke test**

```bash
#!/usr/bin/env bash
# Smoke test: run each source script and validate JSON output.
# Requires network access. Not for CI — for manual validation.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)/scripts/sources"
FAILURES=0

for script in "$SCRIPT_DIR"/*.py; do
  name=$(basename "$script")
  echo "Testing $name..."
  output=$(python3 "$script" 2>&1) || {
    echo "  FAIL: $name exited with error"
    echo "  $output"
    FAILURES=$((FAILURES + 1))
    continue
  }
  # Validate JSON array
  echo "$output" | python3 -c "import sys,json; d=json.load(sys.stdin); assert isinstance(d,list), 'Not a list'" 2>&1 || {
    echo "  FAIL: $name did not output a valid JSON array"
    FAILURES=$((FAILURES + 1))
    continue
  }
  count=$(echo "$output" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
  echo "  OK: $count items"
done

if [ $FAILURES -gt 0 ]; then
  echo "FAILED: $FAILURES script(s) failed"
  exit 1
fi
echo "All smoke tests passed"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x tests/smoke_test.sh
```

- [ ] **Step 3: Commit**

```bash
git add tests/smoke_test.sh
git commit -m "test: add smoke test for source scripts"
```

---

### Task 13: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass (21 total across 3 test files).

- [ ] **Step 2: Run smoke test (requires network)**

```bash
bash tests/smoke_test.sh
```

Expected: Both source scripts produce valid JSON with >0 items.

- [ ] **Step 3: Verify plugin structure**

```bash
ls -la .claude-plugin/plugin.json hooks/hooks.json hooks/session-start .opencode/plugins/newspaper.js skills/daily-briefing/SKILL.md skills/paper-reading/SKILL.md scripts/sources/huggingface_papers.py scripts/sources/smol_news.py scripts/resolve_and_download.py
```

Expected: All files exist.

- [ ] **Step 4: Final commit if any fixups needed**
