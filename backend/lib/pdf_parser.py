"""
PDF parsing utilities for LeaseAI.

Uses PyMuPDF (fitz) for text extraction.
Detects scanned PDFs, strips repeated headers/footers,
and splits text into logical lease sections.
"""
import re
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


# Patterns that indicate a new section heading
_SECTION_PATTERNS = [
    re.compile(r"^(\d+[\.\)]\s+[A-Z][A-Za-z\s]{3,})"),           # 1. Rent Payment
    re.compile(r"^([A-Z][A-Z\s]{4,}:?\s*$)"),                      # SECURITY DEPOSIT
    re.compile(r"^(ARTICLE\s+\d+[:\.\s])", re.IGNORECASE),         # Article 1.
    re.compile(r"^(SECTION\s+\d+[:\.\s])", re.IGNORECASE),         # Section 3.
    re.compile(r"^(\([a-z]\)\s+[A-Z])"),                            # (a) Tenant agrees
]


def extract_sections(text: str) -> list[dict]:
    """
    Split lease text into logical sections by detecting headings.

    Returns a list of dicts: [{"title": str, "content": str}, ...]
    """
    lines = text.splitlines()
    sections: list[dict] = []
    current_title = "Preamble"
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        is_heading = any(pat.match(stripped) for pat in _SECTION_PATTERNS)

        if is_heading and len(stripped) > 4:
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append({"title": current_title, "content": content})
            current_title = stripped
            current_lines = []
        else:
            current_lines.append(line)

    # Flush the last section
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append({"title": current_title, "content": content})

    if not sections:
        # No sections detected — return the full text as one chunk
        sections = [{"title": "Full Document", "content": text}]

    return sections
