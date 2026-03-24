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
