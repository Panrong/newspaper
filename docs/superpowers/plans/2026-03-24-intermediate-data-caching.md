# Intermediate Data Caching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add file-based caching of intermediate pipeline data to daily-briefing and paper-reading skills, enabling debugging, reuse, and avoiding redundant API fetches.

**Architecture:** A `scripts/cache.py` CLI manages all cache operations (check, write, path, list, settings). SKILL.md files are updated to use this CLI at each pipeline stage. A `settings.json` at the project root holds user-configurable TTL.

**Tech Stack:** Python 3.10+, pytest, no new dependencies (stdlib only for cache.py)

**Spec:** `docs/superpowers/specs/2026-03-24-intermediate-data-caching-design.md`

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `scripts/cache.py` | Cache CLI: check, write, path, list, settings commands |
| `settings.json` | User-editable config (`cache_ttl_days`) |
| `.gitignore` | Ignore `cache/`, `__pycache__/`, `*.egg-info/` |
| `tests/test_cache.py` | Tests for all cache.py commands |

### Modified files

| File | Changes |
|------|---------|
| `skills/daily-briefing/SKILL.md` | Add cache-check logic at fetch, filter, aggregate stages |
| `skills/paper-reading/SKILL.md` | Add cache-check for PDF and summary, remove cleanup step |

---

## Task 1: Project config files

**Files:**
- Create: `settings.json`
- Create: `.gitignore`

- [ ] **Step 1: Create `settings.json`**

```json
{
  "cache_ttl_days": 7
}
```

- [ ] **Step 2: Create `.gitignore`**

```
cache/
__pycache__/
*.egg-info/
.venv/
.pytest_cache/
```

- [ ] **Step 3: Commit**

```bash
git add settings.json .gitignore
git commit -m "chore: add settings.json and .gitignore for cache support"
```

---

## Task 2: cache.py — core helpers (settings, URL normalization, path construction)

**Files:**
- Create: `scripts/cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Write failing tests for settings loading**

In `tests/test_cache.py`:

```python
import json
import os
import pytest


def test_load_settings_default(tmp_path, monkeypatch):
    """Missing settings.json returns default TTL of 7."""
    monkeypatch.chdir(tmp_path)
    from scripts.cache import load_settings
    settings = load_settings(project_root=str(tmp_path))
    assert settings["cache_ttl_days"] == 7


def test_load_settings_custom(tmp_path, monkeypatch):
    """Custom settings.json overrides default."""
    (tmp_path / "settings.json").write_text(json.dumps({"cache_ttl_days": 14}))
    from scripts.cache import load_settings
    settings = load_settings(project_root=str(tmp_path))
    assert settings["cache_ttl_days"] == 14


def test_load_settings_invalid_json(tmp_path, monkeypatch, capsys):
    """Invalid JSON falls back to default and warns on stderr."""
    (tmp_path / "settings.json").write_text("not json")
    from scripts.cache import load_settings
    settings = load_settings(project_root=str(tmp_path))
    assert settings["cache_ttl_days"] == 7
    assert "warning" in capsys.readouterr().err.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cache.py::test_load_settings_default tests/test_cache.py::test_load_settings_custom tests/test_cache.py::test_load_settings_invalid_json -v`
Expected: FAIL — `scripts.cache` module not found

- [ ] **Step 3: Write failing tests for URL normalization and path construction**

Append to `tests/test_cache.py`:

```python
def test_normalize_url_strips_trailing_slash():
    from scripts.cache import normalize_url
    assert normalize_url("https://ArXiv.org/abs/123/") == "https://arxiv.org/abs/123"


def test_normalize_url_lowercases_hostname():
    from scripts.cache import normalize_url
    assert normalize_url("https://ARXIV.ORG/abs/123") == "https://arxiv.org/abs/123"


def test_url_hash_is_16_hex_chars():
    from scripts.cache import url_hash
    h = url_hash("https://arxiv.org/abs/123")
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


def test_url_hash_deterministic():
    from scripts.cache import url_hash
    assert url_hash("https://arxiv.org/abs/123") == url_hash("https://arxiv.org/abs/123")


def test_resolve_cache_path_daily_briefing(tmp_path):
    from scripts.cache import resolve_cache_path
    path = resolve_cache_path(
        "daily-briefing", "2026-03-24", "raw/huggingface_papers.json",
        cache_root=str(tmp_path / "cache")
    )
    assert path == str(tmp_path / "cache" / "daily-briefing" / "2026-03-24" / "raw" / "huggingface_papers.json")


def test_resolve_cache_path_paper_reading(tmp_path):
    from scripts.cache import resolve_cache_path, url_hash
    url = "https://arxiv.org/abs/2401.12345"
    h = url_hash(url)
    path = resolve_cache_path(
        "paper-reading", url, "paper.pdf",
        cache_root=str(tmp_path / "cache")
    )
    assert path == str(tmp_path / "cache" / "paper-reading" / h / "paper.pdf")
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python -m pytest tests/test_cache.py -v -k "normalize or hash or resolve_cache"`
Expected: FAIL

- [ ] **Step 5: Implement core helpers**

In `scripts/cache.py`:

```python
#!/usr/bin/env python3
"""Cache management CLI for newspaper plugin.

Commands: check, write, path, list, settings
"""
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

DEFAULT_SETTINGS = {"cache_ttl_days": 7}


def load_settings(project_root: str = ".") -> dict:
    """Load settings from settings.json, falling back to defaults."""
    settings_path = os.path.join(project_root, "settings.json")
    try:
        with open(settings_path) as f:
            return {**DEFAULT_SETTINGS, **json.load(f)}
    except FileNotFoundError:
        return dict(DEFAULT_SETTINGS)
    except (json.JSONDecodeError, ValueError):
        print("Warning: settings.json contains invalid JSON, using defaults", file=sys.stderr)
        return dict(DEFAULT_SETTINGS)


def normalize_url(url: str) -> str:
    """Normalize URL: lowercase hostname, strip trailing slashes."""
    parsed = urlparse(url)
    normalized = parsed._replace(
        netloc=parsed.netloc.lower(),
        path=parsed.path.rstrip("/"),
    )
    return normalized.geturl()


def url_hash(url: str) -> str:
    """SHA-256 hash of normalized URL, truncated to 16 hex chars."""
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def resolve_cache_path(skill: str, key: str, filename: str, cache_root: str = "cache") -> str:
    """Resolve the full cache file path for a given skill, key, and filename.

    For daily-briefing: key is the date string (YYYY-MM-DD).
    For paper-reading: key is the URL (hashed internally).
    """
    if skill == "paper-reading":
        subdir = url_hash(key)
    else:
        subdir = key
    return os.path.join(cache_root, skill, subdir, filename)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_cache.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add scripts/cache.py tests/test_cache.py
git commit -m "feat: add cache.py core helpers — settings, URL normalization, path resolution"
```

---

## Task 3: cache.py — check command

**Files:**
- Modify: `scripts/cache.py`
- Modify: `tests/test_cache.py`

- [ ] **Step 1: Write failing tests for check command**

Append to `tests/test_cache.py`:

```python
import time


def test_check_cache_miss_no_file(tmp_path):
    """check returns None when file doesn't exist."""
    from scripts.cache import check_cache
    result = check_cache(
        "daily-briefing", "2026-03-24", "raw/huggingface_papers.json",
        cache_root=str(tmp_path / "cache"), ttl_days=7
    )
    assert result is None


def test_check_cache_hit_fresh(tmp_path):
    """check returns path when file exists and is within TTL."""
    from scripts.cache import check_cache, resolve_cache_path
    path = resolve_cache_path(
        "daily-briefing", "2026-03-24", "raw/huggingface_papers.json",
        cache_root=str(tmp_path / "cache")
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("[]")
    result = check_cache(
        "daily-briefing", "2026-03-24", "raw/huggingface_papers.json",
        cache_root=str(tmp_path / "cache"), ttl_days=7
    )
    assert result == path


def test_check_cache_miss_expired(tmp_path):
    """check returns None when file exists but is expired."""
    from scripts.cache import check_cache, resolve_cache_path
    path = resolve_cache_path(
        "daily-briefing", "2026-03-24", "raw/huggingface_papers.json",
        cache_root=str(tmp_path / "cache")
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("[]")
    # Set mtime to 8 days ago
    old_time = time.time() - (8 * 86400)
    os.utime(path, (old_time, old_time))
    result = check_cache(
        "daily-briefing", "2026-03-24", "raw/huggingface_papers.json",
        cache_root=str(tmp_path / "cache"), ttl_days=7
    )
    assert result is None


def test_check_paper_reading_verifies_url(tmp_path):
    """check for paper-reading verifies URL in metadata.json matches."""
    from scripts.cache import check_cache, resolve_cache_path
    url = "https://arxiv.org/abs/2401.12345"
    # Write metadata with matching URL
    meta_path = resolve_cache_path("paper-reading", url, "metadata.json", cache_root=str(tmp_path / "cache"))
    pdf_path = resolve_cache_path("paper-reading", url, "paper.pdf", cache_root=str(tmp_path / "cache"))
    os.makedirs(os.path.dirname(meta_path), exist_ok=True)
    with open(meta_path, "w") as f:
        json.dump({"url": url, "url_hash": "x", "title": "Test", "fetched_at": "2026-01-01T00:00:00Z"}, f)
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF")
    result = check_cache("paper-reading", url, "paper.pdf", cache_root=str(tmp_path / "cache"), ttl_days=7)
    assert result == pdf_path


def test_check_paper_reading_url_mismatch(tmp_path):
    """check for paper-reading returns None on URL hash collision."""
    from scripts.cache import check_cache, resolve_cache_path
    url = "https://arxiv.org/abs/2401.12345"
    meta_path = resolve_cache_path("paper-reading", url, "metadata.json", cache_root=str(tmp_path / "cache"))
    pdf_path = resolve_cache_path("paper-reading", url, "paper.pdf", cache_root=str(tmp_path / "cache"))
    os.makedirs(os.path.dirname(meta_path), exist_ok=True)
    with open(meta_path, "w") as f:
        json.dump({"url": "https://different.com/paper", "url_hash": "x", "title": "Test", "fetched_at": "2026-01-01T00:00:00Z"}, f)
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF")
    result = check_cache("paper-reading", url, "paper.pdf", cache_root=str(tmp_path / "cache"), ttl_days=7)
    assert result is None


def test_check_paper_reading_missing_metadata(tmp_path):
    """check for paper-reading returns None when metadata.json is missing."""
    from scripts.cache import check_cache, resolve_cache_path
    url = "https://arxiv.org/abs/2401.12345"
    pdf_path = resolve_cache_path("paper-reading", url, "paper.pdf", cache_root=str(tmp_path / "cache"))
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF")
    # No metadata.json exists — check should return None
    result = check_cache("paper-reading", url, "paper.pdf", cache_root=str(tmp_path / "cache"), ttl_days=7)
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cache.py -v -k "check"`
Expected: FAIL

- [ ] **Step 3: Implement check_cache function**

Add to `scripts/cache.py`:

```python
def check_cache(skill: str, key: str, filename: str, cache_root: str = "cache", ttl_days: int = 7) -> str | None:
    """Check if a cache entry exists and is valid.

    Returns the file path if valid, None otherwise.
    For paper-reading, also verifies the URL in metadata.json matches.
    """
    path = resolve_cache_path(skill, key, filename, cache_root=cache_root)
    if not os.path.exists(path):
        return None

    # Check TTL
    mtime = os.path.getmtime(path)
    age_days = (time.time() - mtime) / 86400
    if age_days > ttl_days:
        return None

    # For paper-reading, verify URL matches metadata
    if skill == "paper-reading":
        meta_path = resolve_cache_path(skill, key, "metadata.json", cache_root=cache_root)
        if not os.path.exists(meta_path):
            return None  # Can't verify URL without metadata
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            if normalize_url(meta.get("url", "")) != normalize_url(key):
                return None
        except (json.JSONDecodeError, KeyError):
            return None

    return path
```

`import time` is already included in the initial `scripts/cache.py` imports from Task 2.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cache.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/cache.py tests/test_cache.py
git commit -m "feat: add cache check command with TTL and URL verification"
```

---

## Task 4: cache.py — write command

**Files:**
- Modify: `scripts/cache.py`
- Modify: `tests/test_cache.py`

- [ ] **Step 1: Write failing tests for write command**

Append to `tests/test_cache.py`:

```python
def test_write_cache_from_stdin(tmp_path):
    """write_cache stores stdin content at the correct path."""
    from scripts.cache import write_cache
    data = '[{"title": "test"}]'
    path = write_cache(
        "daily-briefing", "2026-03-24", "raw/huggingface_papers.json",
        content=data, cache_root=str(tmp_path / "cache")
    )
    assert os.path.exists(path)
    with open(path) as f:
        assert json.load(f) == [{"title": "test"}]


def test_write_cache_creates_dirs(tmp_path):
    """write_cache creates intermediate directories."""
    from scripts.cache import write_cache
    path = write_cache(
        "daily-briefing", "2026-03-24", "raw/deep/nested.json",
        content="{}", cache_root=str(tmp_path / "cache")
    )
    assert os.path.exists(path)


def test_write_cache_from_file(tmp_path):
    """write_cache with from_file copies a binary file into cache."""
    from scripts.cache import write_cache
    # Create a source file
    src = tmp_path / "source.pdf"
    src.write_bytes(b"%PDF-1.4 fake content")
    path = write_cache(
        "paper-reading", "https://arxiv.org/abs/2401.12345", "paper.pdf",
        from_file=str(src), cache_root=str(tmp_path / "cache")
    )
    assert os.path.exists(path)
    with open(path, "rb") as f:
        assert f.read() == b"%PDF-1.4 fake content"


def test_write_cache_paper_creates_metadata(tmp_path):
    """write_cache for paper-reading auto-creates metadata.json."""
    from scripts.cache import write_cache, resolve_cache_path
    src = tmp_path / "source.pdf"
    src.write_bytes(b"%PDF")
    url = "https://arxiv.org/abs/2401.12345"
    write_cache(
        "paper-reading", url, "paper.pdf",
        from_file=str(src), cache_root=str(tmp_path / "cache")
    )
    meta_path = resolve_cache_path("paper-reading", url, "metadata.json", cache_root=str(tmp_path / "cache"))
    assert os.path.exists(meta_path)
    with open(meta_path) as f:
        meta = json.load(f)
    assert meta["url"] == url
    assert "fetched_at" in meta
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cache.py -v -k "write"`
Expected: FAIL

- [ ] **Step 3: Implement write_cache function**

Add to `scripts/cache.py` (`shutil` is already imported from Task 2):

```python
def write_cache(
    skill: str, key: str, filename: str,
    content: str | None = None, from_file: str | None = None,
    cache_root: str = "cache"
) -> str:
    """Write data to cache. Either content (str) or from_file (path) must be provided.

    For paper-reading with from_file, also creates metadata.json automatically.
    Returns the cache file path.
    """
    path = resolve_cache_path(skill, key, filename, cache_root=cache_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if from_file is not None:
        shutil.copy2(from_file, path)
    elif content is not None:
        with open(path, "w") as f:
            f.write(content)
    else:
        raise ValueError("Either content or from_file must be provided")

    # Auto-create metadata.json for paper-reading when writing paper.pdf
    if skill == "paper-reading" and filename == "paper.pdf":
        meta_path = resolve_cache_path(skill, key, "metadata.json", cache_root=cache_root)
        meta = {
            "url": key,
            "url_hash": url_hash(key),
            "title": "",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cache.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/cache.py tests/test_cache.py
git commit -m "feat: add cache write command with --from-file support"
```

---

## Task 5: cache.py — path, list, settings CLI commands

**Files:**
- Modify: `scripts/cache.py`
- Modify: `tests/test_cache.py`

- [ ] **Step 1: Write failing tests for CLI interface**

Append to `tests/test_cache.py`:

```python
def test_cli_settings(tmp_path):
    """settings command loads from correct path."""
    (tmp_path / "settings.json").write_text('{"cache_ttl_days": 14}')
    from scripts.cache import load_settings
    settings = load_settings(project_root=str(tmp_path))
    assert settings["cache_ttl_days"] == 14


def test_cli_path_daily_briefing():
    """CLI 'path' prints the resolved cache path."""
    from scripts.cache import resolve_cache_path
    path = resolve_cache_path("daily-briefing", "2026-03-24", "raw/huggingface_papers.json")
    assert "daily-briefing" in path
    assert "2026-03-24" in path


def test_cli_list_empty(tmp_path):
    """CLI 'list' on empty cache returns no entries."""
    from scripts.cache import list_cache
    entries = list_cache(cache_root=str(tmp_path / "cache"), ttl_days=7)
    assert entries == []


def test_cli_list_with_entries(tmp_path):
    """CLI 'list' returns entries with age and validity."""
    from scripts.cache import write_cache, list_cache
    write_cache(
        "daily-briefing", "2026-03-24", "raw/huggingface_papers.json",
        content="[]", cache_root=str(tmp_path / "cache")
    )
    entries = list_cache(cache_root=str(tmp_path / "cache"), ttl_days=7)
    assert len(entries) == 1
    assert entries[0]["path"].endswith("huggingface_papers.json")
    assert entries[0]["valid"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cache.py -v -k "cli"`
Expected: FAIL

- [ ] **Step 3: Implement list_cache and CLI main**

Add to `scripts/cache.py`:

```python
def list_cache(cache_root: str = "cache", ttl_days: int = 7) -> list[dict]:
    """List all cache entries with age and validity status."""
    entries = []
    if not os.path.exists(cache_root):
        return entries

    for root, dirs, files in os.walk(cache_root):
        for fname in files:
            fpath = os.path.join(root, fname)
            mtime = os.path.getmtime(fpath)
            age_seconds = time.time() - mtime
            age_days = age_seconds / 86400
            rel_path = os.path.relpath(fpath, cache_root)
            entries.append({
                "path": rel_path,
                "age_seconds": age_seconds,
                "valid": age_days <= ttl_days,
            })
    entries.sort(key=lambda e: e["path"])
    return entries


def format_age(seconds: float) -> str:
    """Format age in human-readable form."""
    if seconds < 3600:
        return f"{int(seconds / 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds / 3600)}h ago"
    return f"{int(seconds / 86400)}d ago"


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: cache.py <command> [args]", file=sys.stderr)
        print("Commands: check, write, path, list, settings", file=sys.stderr)
        sys.exit(1)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_root = os.path.join(project_root, "cache")
    settings = load_settings(project_root)
    ttl_days = settings["cache_ttl_days"]
    command = sys.argv[1]

    if command == "settings":
        print(json.dumps(settings, indent=2))

    elif command == "check":
        if len(sys.argv) != 5:
            print("Usage: cache.py check <skill> <key> <filename>", file=sys.stderr)
            sys.exit(1)
        skill, key, filename = sys.argv[2], sys.argv[3], sys.argv[4]
        result = check_cache(skill, key, filename, cache_root=cache_root, ttl_days=ttl_days)
        if result:
            print(result)
            sys.exit(0)
        else:
            sys.exit(1)

    elif command == "write":
        if len(sys.argv) < 5:
            print("Usage: cache.py write <skill> <key> <filename> [--from-file <path>]", file=sys.stderr)
            sys.exit(1)
        skill, key, filename = sys.argv[2], sys.argv[3], sys.argv[4]
        from_file = None
        if "--from-file" in sys.argv:
            idx = sys.argv.index("--from-file")
            if idx + 1 < len(sys.argv):
                from_file = sys.argv[idx + 1]
        if from_file:
            path = write_cache(skill, key, filename, from_file=from_file, cache_root=cache_root)
        else:
            content = sys.stdin.read()
            path = write_cache(skill, key, filename, content=content, cache_root=cache_root)
        print(path)

    elif command == "path":
        if len(sys.argv) != 5:
            print("Usage: cache.py path <skill> <key> <filename>", file=sys.stderr)
            sys.exit(1)
        skill, key, filename = sys.argv[2], sys.argv[3], sys.argv[4]
        print(resolve_cache_path(skill, key, filename, cache_root=cache_root))

    elif command == "list":
        entries = list_cache(cache_root=cache_root, ttl_days=ttl_days)
        if not entries:
            print("(no cache entries)")
        else:
            for e in entries:
                status = "valid" if e["valid"] else "expired"
                age = format_age(e["age_seconds"])
                print(f"  {e['path']:<60s} {age:<10s} {status}")

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all cache tests**

Run: `python -m pytest tests/test_cache.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run CLI smoke test**

```bash
python scripts/cache.py settings
python scripts/cache.py list
echo '[]' | python scripts/cache.py write daily-briefing 2026-03-24 raw/test.json
python scripts/cache.py check daily-briefing 2026-03-24 raw/test.json
python scripts/cache.py path paper-reading "https://arxiv.org/abs/123" paper.pdf
rm -rf cache/daily-briefing/2026-03-24/raw/test.json
```

Expected: settings prints JSON, list shows the written entry, check exits 0 and prints path, path prints a path.

- [ ] **Step 6: Commit**

```bash
git add scripts/cache.py tests/test_cache.py
git commit -m "feat: add cache path, list, settings commands and CLI entry point"
```

---

## Task 6: Update daily-briefing SKILL.md

**Files:**
- Modify: `skills/daily-briefing/SKILL.md`

- [ ] **Step 1: Rewrite SKILL.md with cache-aware workflow**

Replace the full content of `skills/daily-briefing/SKILL.md` with:

````markdown
---
name: daily-briefing
description: Use when the user wants a daily news brief, AI paper summary, or asks about today's papers/news from HuggingFace or smol.ai
---

# Daily Briefing

Produce a daily brief of AI papers and news, filtered by the user's interests and aggregated across sources.

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
- **Exit code 1 (cache miss):** run the source script and pipe output to cache:

```bash
python <plugin_root>/scripts/sources/<source_name>.py | python <plugin_root>/scripts/cache.py write daily-briefing <date> raw/<source_name>.json
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

**If cache miss:** group items (where `kept: true` in filter decisions) that discuss the same underlying topic, event, or paper across different sources into a single entry. Cite all source URLs. If the same paper appears in both HuggingFace and smol.ai, merge into one entry under Papers.

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

Write a structured markdown brief. Items are categorized as either Papers or News based on their `item_type` field. The filtered-out list comes from `filter-decisions.json` (items where `kept: false`):

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
````

- [ ] **Step 2: Review the updated SKILL.md for correctness**

Read through the file and verify all cache.py command invocations match the CLI interface from Task 5.

- [ ] **Step 3: Commit**

```bash
git add skills/daily-briefing/SKILL.md
git commit -m "feat: update daily-briefing skill with cache-aware workflow"
```

---

## Task 7: Update paper-reading SKILL.md

**Files:**
- Modify: `skills/paper-reading/SKILL.md`

- [ ] **Step 1: Rewrite SKILL.md with cache-aware workflow**

Replace the full content of `skills/paper-reading/SKILL.md` with:

````markdown
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
````

- [ ] **Step 2: Review the updated SKILL.md for correctness**

Read through the file and verify all cache.py command invocations match the CLI interface from Task 5.

- [ ] **Step 3: Commit**

```bash
git add skills/paper-reading/SKILL.md
git commit -m "feat: update paper-reading skill with cache-aware workflow"
```

---

## Task 8: Run full test suite and final verification

**Files:**
- None (verification only)

- [ ] **Step 1: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: ALL PASS (existing tests + new cache tests)

- [ ] **Step 2: Verify cache directory is gitignored**

```bash
mkdir -p cache/test && touch cache/test/file.txt
git status
```

Expected: `cache/` does not appear in untracked files

- [ ] **Step 3: Clean up test cache files**

```bash
rm -rf cache/test
```

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git status
# Only commit if there are changes
```
