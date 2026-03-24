# newspaper

A Claude Code / OpenClaw plugin for daily AI news briefing and paper reading.

## Skills

**`daily-briefing`** — Fetches papers from HuggingFace and news from smol.ai, filters by your `topic-of-interest.md`, aggregates cross-source duplicates, and outputs a dated markdown brief.

**`paper-reading`** — Downloads a paper from a URL (arXiv, OpenReview, HuggingFace, Semantic Scholar), then summarizes it or answers your questions about it.

## Install

```bash
pip install -e .
claude plugins add /path/to/newspaper
```

## Usage

Create `topic-of-interest.md` in your project root, then ask Claude for a daily brief or to read a paper.

## Adding Sources

Drop a `.py` script in `scripts/sources/` that outputs JSON to stdout. See `scripts/sources/README.md` for the interface.
