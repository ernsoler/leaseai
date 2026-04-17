"""
PDF parsing utilities for LeaseAI.

Uses PyMuPDF (fitz) for text extraction.
Detects scanned PDFs and strips repeated headers/footers.
"""
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# Heuristic: fewer than 100 chars/page suggests a scanned PDF
MIN_CHARS_PER_PAGE = 100
MAX_PAGES = 50


def extract_text(pdf_bytes: bytes) -> str:
    """
    Extract all selectable text from a PDF.

    Raises:
        ValueError: if the PDF appears to be scanned or exceeds MAX_PAGES
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError("PyMuPDF (fitz) is not installed") from exc

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)

    if page_count > MAX_PAGES:
        raise ValueError(
            f"Lease is {page_count} pages — maximum supported is {MAX_PAGES}. "
            "Please upload a shorter document."
        )

    pages_text: list[str] = []
    for page in doc:
        pages_text.append(page.get_text())

    doc.close()

    # Scanned PDF detection
    total_chars = sum(len(t) for t in pages_text)
    if page_count > 0 and (total_chars / page_count) < MIN_CHARS_PER_PAGE:
        raise ValueError(
            "This PDF appears to be a scanned image and does not contain selectable text. "
            "Please upload a text-selectable PDF. "
            "If you only have a scanned copy, try running it through an OCR tool first."
        )

    full_text = "\n".join(pages_text)
    full_text = _strip_repeated_lines(full_text, pages_text)
    return full_text.strip()


def _strip_repeated_lines(full_text: str, pages_text: list[str]) -> str:
    """Remove lines that appear on nearly every page (headers/footers)."""
    if len(pages_text) < 3:
        return full_text

    line_counts: Counter = Counter()
    for page_text in pages_text:
        seen = set()
        for line in page_text.splitlines():
            stripped = line.strip()
            if stripped and stripped not in seen:
                line_counts[stripped] += 1
                seen.add(stripped)

    threshold = max(2, len(pages_text) * 0.6)
    repeated = {line for line, count in line_counts.items() if count >= threshold}

    if not repeated:
        return full_text

    cleaned_lines = [
        line for line in full_text.splitlines()
        if line.strip() not in repeated
    ]
    return "\n".join(cleaned_lines)

