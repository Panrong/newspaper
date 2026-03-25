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
        assert isinstance(item["urls"], list)
        assert all(isinstance(u, str) for u in item["urls"])
        assert item["source_name"] == "smol.ai AI News"
        assert isinstance(item["date"], str)
        assert item["item_type"] == "news"


def test_parse_rss_splits_li_into_individual_items():
    """Each <li> should become its own item, not grouped by section."""
    from scripts.sources.smol_news import parse_rss

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    # Fixture has 3 news <li> (Top Tweets excluded) + 1 fallback = 4
    assert len(result) == 4


def test_parse_rss_excludes_top_tweets():
    """Top Tweets section should be excluded entirely."""
    from scripts.sources.smol_news import parse_rss

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    titles = [i["title"] for i in result]
    assert "MiniMax M2.7 announcement" not in titles
    assert "Cartesia Mamba-3 SSM launch" not in titles


def test_parse_rss_title_from_bold_lead():
    """Title should be extracted from the bold lead text of each <li>."""
    from scripts.sources.smol_news import parse_rss

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    titles = [i["title"] for i in result]
    assert "MiniMax M2.7 launched as a self-evolving agent" in titles
    assert "Harness engineering is becoming the key differentiator" in titles


def test_parse_rss_urls_from_hyperlinks():
    """urls should contain all hyperlinks found in the <li>."""
    from scripts.sources.smol_news import parse_rss

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    item = next(i for i in result if "MiniMax M2.7 launched" in i["title"])
    assert "https://ollama.com/minimax" in item["urls"]
    assert "https://openrouter.ai/minimax" in item["urls"]
    assert len(item["urls"]) == 2


def test_parse_rss_body_has_no_hyperlink_text():
    """Body should not contain hyperlink text or URLs."""
    from scripts.sources.smol_news import parse_rss

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    for item in result:
        assert "](http" not in item["body"]
        # Link text like "Ollama" or "OpenRouter" should be stripped
        if "MiniMax M2.7 launched" in item["title"]:
            assert "Ollama" not in item["body"]
            assert "OpenRouter" not in item["body"]


def test_parse_rss_fallback_for_no_recap():
    """Items without AI Twitter Recap should fall back to single item."""
    from scripts.sources.smol_news import parse_rss

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    fallback = next(i for i in result if i["title"] == "A quiet day")
    assert fallback["item_type"] == "news"
    assert fallback["urls"] == ["https://news.smol.ai/issues/26-03-17-quiet/"]


def test_parse_rss_body_uses_content_encoded():
    """Body should use content:encoded (full HTML content) when available."""
    from scripts.sources.smol_news import parse_rss

    xml = load_fixture("smol_news_rss.xml")
    result = parse_rss(xml)
    for item in result:
        assert len(item["body"]) > 10


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
