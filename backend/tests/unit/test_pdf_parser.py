"""Unit tests for the PDF parser utilities."""
from pathlib import Path
from backend.lib.pdf_parser import _strip_repeated_lines

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_lease.txt"


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
