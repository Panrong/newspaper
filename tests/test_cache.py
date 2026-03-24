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
