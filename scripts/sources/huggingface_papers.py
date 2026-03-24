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
                "url": f"https://huggingface.co/papers/{paper.get('id', '')}",
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
