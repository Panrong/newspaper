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
