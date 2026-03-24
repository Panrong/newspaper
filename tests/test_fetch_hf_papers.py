import json
import os
from unittest.mock import patch, MagicMock

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return f.read()


def test_parse_hf_papers_returns_list():
    """Parsing the API response should return a list of dicts."""
    from scripts.sources.huggingface_papers import parse_papers

    raw = json.loads(load_fixture("hf_daily_papers_response.json"))
    result = parse_papers(raw)
    assert isinstance(result, list)
    assert len(result) > 0


def test_parse_hf_papers_schema():
    """Each item must have the required fields with correct types."""
    from scripts.sources.huggingface_papers import parse_papers

    raw = json.loads(load_fixture("hf_daily_papers_response.json"))
    result = parse_papers(raw)
    for item in result:
        assert isinstance(item["title"], str)
        assert isinstance(item["body"], str)
        assert isinstance(item["url"], str)
        assert item["source_name"] == "HuggingFace Daily Papers"
        assert isinstance(item["date"], str)
        assert item["item_type"] == "paper"


def test_parse_hf_papers_url_format():
    """URL should point to the HuggingFace paper page."""
    from scripts.sources.huggingface_papers import parse_papers

    raw = json.loads(load_fixture("hf_daily_papers_response.json"))
    result = parse_papers(raw)
    for item in result:
        assert item["url"].startswith("https://huggingface.co/papers/")


def test_parse_hf_papers_body_contains_abstract():
    """Body should include the paper abstract/summary."""
    from scripts.sources.huggingface_papers import parse_papers

    raw = json.loads(load_fixture("hf_daily_papers_response.json"))
    result = parse_papers(raw)
    for item in result:
        assert len(item["body"]) > 20


def test_parse_hf_papers_empty_input():
    """Empty API response should return empty list."""
    from scripts.sources.huggingface_papers import parse_papers

    result = parse_papers([])
    assert result == []


@patch("scripts.sources.huggingface_papers.requests.get")
def test_fetch_papers_calls_api(mock_get):
    """fetch_papers should call the HuggingFace API."""
    from scripts.sources.huggingface_papers import fetch_papers

    mock_response = MagicMock()
    mock_response.json.return_value = json.loads(
        load_fixture("hf_daily_papers_response.json")
    )
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    result = fetch_papers()
    mock_get.assert_called_once_with(
        "https://huggingface.co/api/daily_papers", timeout=30
    )
    assert isinstance(result, list)
    assert len(result) > 0
