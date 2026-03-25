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

    project_root = os.getcwd()
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
