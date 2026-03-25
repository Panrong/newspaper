#!/usr/bin/env python3
"""Fetch news from smol.ai AI News RSS feed.

Outputs a JSON array to stdout with the source script interface schema:
  [{title, body, urls, source_name, date, item_type}]

Each RSS entry is a daily roundup. Post-processing extracts individual items
from the "AI Twitter Recap" section (excluding "Top Tweets"), splitting each
<li> into its own item with a descriptive title (from bold lead text),
plain-text body (hyperlinks removed entirely), and all hyperlink URLs
collected into a urls list.

Usage:
  python smol_news.py                # items from today
  python smol_news.py --date 2026-03-24  # items from a specific date
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape

import requests


RSS_URL = "https://news.smol.ai/rss.xml"
CONTENT_NS = {"content": "http://purl.org/rss/1.0/modules/content/"}


def _html_to_text(html: str) -> str:
    """Convert HTML to plain text, removing hyperlinks entirely.

    Links are stripped completely (not even the link text is kept) because
    the URLs are captured separately in the urls field, and the link text
    (e.g. author names, source labels) adds noise to the body.
    """
    # Remove <a> tags and their content entirely
    text = re.sub(
        r'<a\s+[^>]*>.*?</a>',
        r"",
        html,
        flags=re.DOTALL,
    )
    # Convert <strong>text</strong> to **text**
    text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text)
    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Clean up leftover artifacts: dangling parens, commas, extra spaces
    text = re.sub(r"\(\s*[,\s]*\)", "", text)  # empty or comma-only parens
    text = re.sub(r"\s{2,}", " ", text)  # collapse multiple spaces
    return unescape(text).strip()


def _extract_urls(html: str) -> list[str]:
    """Extract all hyperlink URLs from an HTML fragment."""
    return re.findall(r'<a\s+[^>]*href="([^"]*)"', html)


def _extract_lead_title(html: str) -> str:
    """Extract the bold lead text from a <li> element as the item title.

    Expects patterns like: <strong>Title text</strong>: rest of body...
    Falls back to first 80 chars of plain text if no bold lead found.
    """
    m = re.match(r"\s*<strong>(.*?)</strong>", html, re.DOTALL)
    if m:
        return unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
    # Fallback: first 80 chars of plain text
    text = unescape(re.sub(r"<[^>]+>", "", html)).strip()
    return text[:80].rstrip() + ("..." if len(text) > 80 else "")


def _extract_recap_items(
    html_body: str,
) -> list[tuple[str, str, list[str]]]:
    """Extract individual items from the AI Twitter Recap section.

    Returns a list of (title, plain_text_body, urls) tuples.
    Each <li> becomes its own item. The "Top Tweets" section is excluded
    since it duplicates content already covered by the thematic sections.
    """
    recap_start = html_body.find("AI Twitter Recap")
    if recap_start == -1:
        return []

    recap_body = html_body[recap_start:]

    # Split on section headers: <p><strong>TITLE</strong></p>
    # Result alternates: [preamble, title1, content1, title2, content2, ...]
    parts = re.split(r"<p><strong>([^<]+)</strong></p>", recap_body)

    items = []
    for i in range(1, len(parts) - 1, 2):
        section_title = unescape(parts[i]).strip()
        if "Top Tweets" in section_title:
            continue
        section_html = parts[i + 1]

        # Extract <li> elements within this section
        lis = re.findall(r"<li>(.*?)</li>", section_html, re.DOTALL)
        for li_html in lis:
            title = _extract_lead_title(li_html)
            body = _html_to_text(li_html)
            urls = _extract_urls(li_html)
            items.append((title, body, urls))

    return items


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

        # Post-process: extract individual items from AI Twitter Recap
        recap_items = _extract_recap_items(body)
        if recap_items:
            for item_title, item_body, item_urls in recap_items:
                results.append(
                    {
                        "title": item_title,
                        "body": item_body,
                        "urls": item_urls or [url],
                        "source_name": "smol.ai AI News",
                        "date": date_str,
                        "item_type": "news",
                    }
                )
        else:
            # Fallback: no AI Twitter Recap found, emit as single item
            results.append(
                {
                    "title": title,
                    "body": _html_to_text(body),
                    "urls": [url],
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
    parser = argparse.ArgumentParser(description="Fetch smol.ai AI News")
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Target date in YYYY-MM-DD format (default: today)",
    )
    args = parser.parse_args()
    try:
        news = fetch_news()
        filtered = [item for item in news if item["date"] == args.date]
        print(json.dumps(filtered, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
