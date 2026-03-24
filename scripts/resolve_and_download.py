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
