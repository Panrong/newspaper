import os
from unittest.mock import patch, MagicMock

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return f.read()


def test_parse_rss_returns_list():
    """Parsing RSS XML should return a list of dicts."""
    from scripts.sources.smol_news import parse_rss

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    assert isinstance(result, list)
    assert len(result) > 0


def test_parse_rss_schema():
    """Each item must have the required fields with correct types."""
    from scripts.sources.smol_news import parse_rss

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    for item in result:
        assert isinstance(item["title"], str)
        assert isinstance(item["body"], str)
        assert isinstance(item["url"], str)
        assert item["source_name"] == "smol.ai AI News"
        assert isinstance(item["date"], str)
        assert item["item_type"] == "news"


def test_parse_rss_body_uses_content_encoded():
    """Body should use content:encoded (full HTML content) when available."""
    from scripts.sources.smol_news import parse_rss

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    for item in result:
        # content:encoded is typically much longer than description
        assert len(item["body"]) > 20


def test_parse_rss_date_format():
    """Date should be in YYYY-MM-DD format."""
    from scripts.sources.smol_news import parse_rss
    import re

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    for item in result:
        assert re.match(r"\d{4}-\d{2}-\d{2}", item["date"])


def test_parse_rss_empty_input():
    """Empty RSS feed should return empty list."""
    from scripts.sources.smol_news import parse_rss

    xml = '<?xml version="1.0"?><rss><channel></channel></rss>'
    result = parse_rss(xml)
    assert result == []


@patch("scripts.sources.smol_news.requests.get")
def test_fetch_news_calls_rss(mock_get):
    """fetch_news should fetch the RSS feed URL."""
    from scripts.sources.smol_news import fetch_news

    mock_response = MagicMock()
    mock_response.text = load_fixture("smol_news_rss.xml")
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = fetch_news()
    mock_get.assert_called_once_with(
        "https://news.smol.ai/rss.xml", timeout=30
    )
    assert isinstance(result, list)
    assert len(result) > 0
