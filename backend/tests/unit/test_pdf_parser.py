"""Unit tests for the PDF parser utilities."""
import pytest
from pathlib import Path
from backend.lib.pdf_parser import extract_sections, _strip_repeated_lines

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_lease.txt"


@pytest.fixture
def sample_text() -> str:
    return FIXTURE.read_text()


def test_detects_numbered_headings(sample_text):
    titles = [s["title"] for s in extract_sections(sample_text)]
    assert any("PROPERTY" in t or "RENT" in t or "TERM" in t for t in titles), titles


def test_all_sections_have_nonempty_content(sample_text):
    for section in extract_sections(sample_text):
        assert section["title"]
        assert len(section["content"]) > 0


def test_unstructured_text_returns_single_chunk():
    # No headings detected → content lands in the "Preamble" bucket.
    # The "Full Document" fallback only fires when sections is truly empty.
    sections = extract_sections("Just a blob of text with no headings whatsoever.")
    assert len(sections) == 1
    assert sections[0]["title"] == "Preamble"
    assert "blob of text" in sections[0]["content"]


def test_preamble_captured_before_first_heading(sample_text):
    sections = extract_sections(sample_text)
    assert len(sections) >= 1
    assert len(sections[0]["content"]) > 10


def test_strip_repeated_lines_removes_header_footer():
    pages = [
        "Header\nPage one content\nFooter",
        "Header\nPage two content\nFooter",
        "Header\nPage three content\nFooter",
    ]
    result = _strip_repeated_lines("\n".join(pages), pages)
    assert "Header" not in result
    assert "Footer" not in result
    assert "Page one content" in result


def test_strip_repeated_lines_keeps_unique_lines():
    pages = [
        "Header\nUnique line A\nFooter",
        "Header\nUnique line B\nFooter",
        "Header\nUnique line C\nFooter",
    ]
    result = _strip_repeated_lines("\n".join(pages), pages)
    assert "Unique line A" in result
    assert "Unique line B" in result


def test_strip_repeated_lines_skips_short_documents():
    """Fewer than 3 pages — nothing stripped."""
    pages = ["Header\nContent\nFooter", "Header\nOther\nFooter"]
    full = "\n".join(pages)
    result = _strip_repeated_lines(full, pages)
    assert result == full
