# tests/test_resolve_and_download.py
import os
from unittest.mock import patch, MagicMock


def test_resolve_arxiv_abs():
    """arXiv abstract URL should resolve to PDF URL."""
    from scripts.resolve_and_download import resolve_pdf_url

    url = "https://arxiv.org/abs/2401.12345"
    assert resolve_pdf_url(url) == "https://arxiv.org/pdf/2401.12345.pdf"


def test_resolve_arxiv_abs_versioned():
    """arXiv versioned abstract URL should resolve to versioned PDF URL."""
    from scripts.resolve_and_download import resolve_pdf_url

    url = "https://arxiv.org/abs/2401.12345v2"
    assert resolve_pdf_url(url) == "https://arxiv.org/pdf/2401.12345v2.pdf"


def test_resolve_openreview():
    """OpenReview forum URL should resolve to PDF URL."""
    from scripts.resolve_and_download import resolve_pdf_url

    url = "https://openreview.net/forum?id=abc123"
    assert resolve_pdf_url(url) == "https://openreview.net/pdf?id=abc123"


def test_resolve_direct_pdf():
    """Direct PDF URL should be returned as-is."""
    from scripts.resolve_and_download import resolve_pdf_url

    url = "https://example.com/paper.pdf"
    assert resolve_pdf_url(url) == "https://example.com/paper.pdf"


def test_resolve_huggingface_paper():
    """HuggingFace paper URL should resolve to arXiv PDF."""
    from scripts.resolve_and_download import resolve_pdf_url

    url = "https://huggingface.co/papers/2401.12345"
    assert resolve_pdf_url(url) == "https://arxiv.org/pdf/2401.12345.pdf"


@patch("scripts.resolve_and_download.requests.get")
def test_resolve_semantic_scholar(mock_get):
    """Semantic Scholar URL should resolve by extracting PDF link from page."""
    from scripts.resolve_and_download import resolve_pdf_url

    mock_response = MagicMock()
    mock_response.text = '<a href="https://arxiv.org/pdf/2401.12345.pdf" class="pdf-link">PDF</a>'
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    url = "https://www.semanticscholar.org/paper/Some-Title/abc123"
    assert resolve_pdf_url(url) == "https://arxiv.org/pdf/2401.12345.pdf"


def test_resolve_unsupported_url_raises():
    """Unsupported URL should raise ValueError."""
    from scripts.resolve_and_download import resolve_pdf_url
    import pytest

    with pytest.raises(ValueError, match="Unsupported"):
        resolve_pdf_url("https://example.com/not-a-paper")


@patch("scripts.resolve_and_download.requests.get")
def test_download_pdf(mock_get):
    """download_pdf should save content to a temp file and return the path."""
    from scripts.resolve_and_download import download_pdf

    mock_response = MagicMock()
    mock_response.content = b"%PDF-1.4 fake pdf content"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    path = download_pdf("https://arxiv.org/pdf/2401.12345.pdf")
    try:
        assert os.path.exists(path)
        assert path.endswith(".pdf")
        with open(path, "rb") as f:
            assert f.read() == b"%PDF-1.4 fake pdf content"
    finally:
        os.unlink(path)


@patch("scripts.resolve_and_download.requests.get")
def test_resolve_and_download_integration(mock_get):
    """resolve_and_download should resolve URL then download."""
    from scripts.resolve_and_download import resolve_and_download

    mock_response = MagicMock()
    mock_response.content = b"%PDF-1.4 fake pdf content"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    path = resolve_and_download("https://arxiv.org/abs/2401.12345")
    try:
        assert os.path.exists(path)
        mock_get.assert_called_once_with(
            "https://arxiv.org/pdf/2401.12345.pdf", timeout=60
        )
    finally:
        os.unlink(path)
