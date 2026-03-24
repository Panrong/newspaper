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


import time as time_mod


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
    old_time = time_mod.time() - (8 * 86400)
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
    result = check_cache("paper-reading", url, "paper.pdf", cache_root=str(tmp_path / "cache"), ttl_days=7)
    assert result is None


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
