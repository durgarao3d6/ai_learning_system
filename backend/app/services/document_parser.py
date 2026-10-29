"""Document parsing and chunking utility functions."""

import io
import re
from dataclasses import dataclass


@dataclass
class ParsedSection:
    heading: str | None
    text: str
    page_number: int | None


def validate_file_magic(content: bytes, filename: str) -> str:
    """Validate magic bytes and determine file format ('pdf', 'docx', 'txt')."""
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if content.startswith(b"%PDF-"):
        return "pdf"
    elif content.startswith(b"PK\x03\x04") and ext in ("docx", "zip"):
        return "docx"
    elif ext in ("txt", "md"):
        return "txt"
    raise ValueError("Unsupported or invalid file format. Only PDF, DOCX, and TXT are allowed.")


def extract_text_from_pdf(content: bytes) -> tuple[list[ParsedSection], int]:
    """Extract sections from PDF using PyMuPDF if available, or lightweight stream parser."""
    sections: list[ParsedSection] = []
    total_pages = 1
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=content, filetype="pdf")
        total_pages = len(doc)
        for page_idx in range(total_pages):
            page = doc[page_idx]
            text = page.get_text("text").strip()
            if text:
                sections.append(ParsedSection(heading=f"Page {page_idx + 1}", text=text, page_number=page_idx + 1))
    except Exception:
        # Fallback raw text decoding for test environments or simple PDFs
        raw = content.decode("utf-8", errors="ignore")
        clean = re.sub(r"[^\x20-\x7E\n]", " ", raw)
        sections.append(ParsedSection(heading="Document Content", text=clean[:50000], page_number=1))

    return sections, total_pages


def extract_text_from_docx(content: bytes) -> list[ParsedSection]:
    """Extract sections and paragraphs from DOCX."""
    sections: list[ParsedSection] = []
    try:
        import docx
        doc = docx.Document(io.BytesIO(content))
        current_heading = "Introduction"
        current_paras: list[str] = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            if para.style and para.style.name.startswith("Heading"):
                if current_paras:
                    sections.append(ParsedSection(heading=current_heading, text="\n".join(current_paras), page_number=1))
                    current_paras = []
                current_heading = text
            else:
                current_paras.append(text)

        if current_paras:
            sections.append(ParsedSection(heading=current_heading, text="\n".join(current_paras), page_number=1))
    except Exception:
        raw = content.decode("utf-8", errors="ignore")
        sections.append(ParsedSection(heading="Document Content", text=raw[:50000], page_number=1))

    return sections


def chunk_sections(sections: list[ParsedSection], target_tokens: int = 500, overlap_tokens: int = 50) -> list[dict]:
    """Chunk sections respecting headings and token windows."""
    chunks = []
    chunk_index = 0

    for sec in sections:
        words = sec.text.split()
        if not words:
            continue

        step = max(1, target_tokens - overlap_tokens)
        for i in range(0, len(words), step):
            window = words[i : i + target_tokens]
            chunk_text = " ".join(window)
            chunks.append({
                "chunk_index": chunk_index,
                "text": chunk_text,
                "token_count": len(window),
                "page_number": sec.page_number,
                "heading": sec.heading,
            })
            chunk_index += 1
            if i + target_tokens >= len(words):
                break

    return chunks
