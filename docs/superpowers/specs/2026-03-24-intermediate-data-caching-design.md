# Intermediate Data Caching Design

Save intermediate data across the daily-briefing and paper-reading skill workflows so that users can debug pipeline stages, reuse cached data for similar queries, and avoid redundant API fetches.

## Settings

`settings.json` at the project root:

```json
{
  "cache_ttl_days": 7
}
```

User-editable. The only setting for now; additional settings can be added without breaking anything.

## Cache Directory Structure

`cache/` at the project root, gitignored.

```
cache/
  daily-briefing/
    2026-03-24/
      raw/
        huggingface_papers.json    # exact output from source script
        smol_news.json
      filter-decisions.json        # per-item filtering record
      aggregated.json              # post-dedup merged items
  paper-reading/
    <url-hash>/                    # first 16 hex chars of SHA-256 of normalized URL
      paper.pdf
      summary.md
      metadata.json                # url, title, fetched_at
```

## Cache Validity

A cached file is valid if `now - file_mtime < cache_ttl_days`. No separate timestamp tracking — filesystem mtime is the source of truth.

If `settings.json` is missing or contains invalid JSON, `cache.py` falls back to the hardcoded default of 7 days and logs a warning to stderr.

For `filter-decisions.json` and `aggregated.json`, cache validity has a second condition: the `topics_hash` stored in the file must match the current hash of `topic-of-interest.md`. The `check` command only validates path existence and mtime. The SKILL.md instructions handle topic-hash comparison: after `check` succeeds, read the file, compare `topics_hash`, and discard if mismatched.

## URL Normalization

For paper-reading cache keys, normalization is: lowercase hostname, strip trailing slashes. Different URLs pointing to the same paper (e.g., arxiv.org vs huggingface.co/papers) cache separately — this is acceptable given the small data volume and TTL-based expiration. On `check`, `cache.py` verifies that the URL stored in `metadata.json` matches the requested URL, guarding against hash collisions.

## Cache Management Script

**New file: `scripts/cache.py`** — CLI tool handling cache operations so Claude doesn't manually compute hashes, check mtimes, or construct paths.

### Commands

```bash
# Check if a cache entry exists and is valid
python scripts/cache.py check daily-briefing 2026-03-24 raw/huggingface_papers.json
# Exit code 0 = valid cache hit (prints file path), 1 = miss

# Write data to cache (reads stdin, writes to correct path)
python scripts/cache.py write daily-briefing 2026-03-24 raw/huggingface_papers.json
# Reads stdin, writes to cache/daily-briefing/2026-03-24/raw/huggingface_papers.json

# Write a file to cache by copying from an existing path (for binary files like PDFs)
python scripts/cache.py write paper-reading "https://arxiv.org/abs/2603.12345" paper.pdf --from-file /tmp/abc.pdf

# Check for paper-reading (handles URL hashing internally)
python scripts/cache.py check paper-reading "https://arxiv.org/abs/2603.12345" paper.pdf

# Get the cache path without checking validity (for constructing paths)
python scripts/cache.py path paper-reading "https://arxiv.org/abs/2603.12345" paper.pdf
# Prints cache/paper-reading/a1b2c3d4e5f67890/paper.pdf

# Read settings
python scripts/cache.py settings
# Prints {"cache_ttl_days": 7}

# Show what's cached (for debugging)
python scripts/cache.py list
# Example output:
#   daily-briefing/2026-03-24/raw/huggingface_papers.json  2h ago   valid
#   daily-briefing/2026-03-24/raw/smol_news.json           2h ago   valid
#   daily-briefing/2026-03-24/filter-decisions.json         2h ago   valid
#   paper-reading/a1b2c3d4e5f67890/paper.pdf                3d ago   valid
#   paper-reading/a1b2c3d4e5f67890/summary.md               3d ago   valid
```

All commands create intermediate directories automatically via `os.makedirs(..., exist_ok=True)`.

### Responsibilities

- **Hash computation** — computes SHA-256 of normalized URLs for paper-reading cache keys
- **TTL checking** — exact mtime comparison in Python rather than Claude estimating freshness
- **Path construction** — knows the `cache/` layout, reducing path errors
- **`list` command** — gives users a quick debugging view of all cached data

## Daily Briefing Cache Workflow

### Cache Keys

- **Raw fetch:** date (YYYY-MM-DD) + source name
- **Filter decisions:** date + topics hash (SHA-256 of `topic-of-interest.md` content)
- **Aggregated result:** date + topics hash

### Step 2 (Fetch Sources) — cache-aware

Before running a source script, use `cache.py check` to see if `raw/{source_name}.json` exists and is within TTL.

- **Cache hit:** read from cached file, skip the script
- **Cache miss:** run the script, pipe output through `cache.py write`, then use it
- Each source is checked independently — one can be cached while the other re-fetches

### Step 3 (Filter) — cache-aware with topic sensitivity

Check if `filter-decisions.json` exists. That file records which topics were used via a `topics_hash` field.

- **Cache hit (same topics):** reuse decisions
- **Cache miss (topics changed or no cache):** re-filter from raw cache, write new decisions file

Changing `topic-of-interest.md` automatically invalidates filter decisions but NOT raw fetches.

### Step 4 (Aggregate) — cache-aware

Check if `aggregated.json` exists and its `topics_hash` matches current topics.

- Same invalidation logic as filter decisions — if topics change, re-aggregate

### filter-decisions.json Schema

```json
{
  "topics_hash": "a1b2c3...",
  "topics_file": "GUI Agent\nReinforcement Learning",
  "generated_at": "2026-03-24T16:30:00Z",
  "decisions": [
    {
      "title": "Some Paper Title",
      "source": "huggingface_papers",
      "url": "https://...",
      "kept": true,
      "matched_topics": ["GUI Agent"],
      "reason": "Paper presents a GUI-based agent framework"
    },
    {
      "title": "Unrelated Paper",
      "source": "huggingface_papers",
      "url": "https://...",
      "kept": false,
      "matched_topics": [],
      "reason": "No relevance to GUI Agent or Reinforcement Learning"
    }
  ]
}
```

### aggregated.json Schema

```json
{
  "topics_hash": "a1b2c3...",
  "generated_at": "2026-03-24T16:32:00Z",
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
  ],
  }
}
```

The filtered-out list is derived from `filter-decisions.json` (items where `kept: false`). It is not duplicated in `aggregated.json`.

## Paper Reading Cache Workflow

### Cache Key

SHA-256 of normalized URL (lowercase hostname, strip trailing slashes), truncated to first 16 hex characters.

### Step 2 (Download) — cache-aware

- Use `cache.py check` to see if the PDF is cached and valid (also verifies URL match in metadata)
- **Cache hit:** use cached PDF path
- **Cache miss:** download via `resolve_and_download.py`, then `cache.py write --from-file <tmp_path>` to copy into cache
- The cache IS the storage — no more `/tmp` files

### Step 4 (Summary) — cache-aware

- **Cache hit (no question asked):** return cached `summary.md` directly
- **Question asked:** always answer fresh from the cached PDF — do NOT overwrite `summary.md` with Q&A responses
- **Cache miss (no question):** generate summary, write to `summary.md`

### Step 5 (Cleanup) — removed

No longer delete the PDF. Cache TTL handles expiration.

### metadata.json Schema

```json
{
  "url": "https://arxiv.org/abs/2603.12345",
  "url_hash": "a1b2c3d4e5f67890",
  "title": "Paper Title",
  "fetched_at": "2026-03-24T16:30:00Z"
}
```

## Implementation Touchpoints

### New files

- `settings.json` — project root, user-editable cache config
- `scripts/cache.py` — cache management CLI
- `.gitignore` entry — add `cache/`

### Modified files

- `skills/daily-briefing/SKILL.md` — add cache-check logic at each stage
- `skills/paper-reading/SKILL.md` — add cache-check for PDF and summary, remove cleanup step

### Unchanged files

- `scripts/sources/huggingface_papers.py` — still outputs JSON to stdout
- `scripts/sources/smol_news.py` — still outputs JSON to stdout
- `scripts/resolve_and_download.py` — still downloads PDFs

### Cache expiration

No background cleanup process. Stale files are ignored and overwritten on next run. Users can `rm -rf cache/` to clear manually.

### Skipping cache

If a user asks for fresh data (e.g., "ignore cache", "re-fetch"), the SKILL.md instructions skip the `cache.py check` step and proceed directly to fetching. The newly fetched data still gets written to cache, overwriting stale entries.
