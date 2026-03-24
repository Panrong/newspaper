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
