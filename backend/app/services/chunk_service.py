import re
from typing import List, Dict, Any


def chunk_pages(
    pages: List[Dict[str, Any]],
    max_words: int = 500
) -> List[Dict[str, Any]]:
    """
    Chunks multimodal page elements into semantic chunks for vector indexing.
    - Tables: preserved intact with markdown structure.
    - Diagrams / Figures / Charts: preserved with visual headers and component labels.
    - Text & OCR: split into logical paragraph/heading-bounded blocks.
    """
    all_chunks = []

    for page in pages:
        page_number = page.get("page_number", 1)
        has_images = page.get("has_images", False)
        elements = page.get("elements", [])

        # If page had raw text without structured elements fallback
        if not elements and page.get("text", "").strip():
            elements = [{
                "content_type": "text",
                "source_type": "pdf_text",
                "page_number": page_number,
                "heading": "",
                "text": page["text"].strip()
            }]

        for elem in elements:
            content_type = elem.get("content_type", "text")
            source_type = elem.get("source_type", "pdf_text")
            heading = elem.get("heading", "")
            raw_text = elem.get("text", "").strip()

            if not raw_text:
                continue

            # Tables and Diagrams/Figures should be indexed as complete, standalone structured chunks
            if content_type in ["table", "diagram", "figure", "chart"] or elem.get("chunk_type") == "table_row":
                all_chunks.append({
                    "text": raw_text,
                    "page_number": page_number,
                    "chunk_type": content_type,
                    "content_type": content_type,
                    "source_type": source_type,
                    "heading": heading,
                    "has_images": has_images
                })
            else:
                # Standard text or OCR paragraphs: split logically
                blocks = split_into_blocks(raw_text)
                text_chunks = build_chunks(blocks, max_words)

                for c in text_chunks:
                    all_chunks.append({
                        "text": c["text"],
                        "page_number": page_number,
                        "chunk_type": c.get("chunk_type", "paragraph"),
                        "content_type": content_type,
                        "source_type": source_type,
                        "heading": heading or c.get("heading", ""),
                        "has_images": has_images
                    })

    return all_chunks


# --------------------------------
# Split text into logical blocks
# --------------------------------

def split_into_blocks(text: str) -> List[Dict[str, Any]]:
    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip()
    ]

    blocks = []
    current_block = []

    for line in lines:
        if is_new_structure(line):
            if current_block:
                blocks.append({
                    "text": " ".join(current_block),
                    "type": detect_block_type(current_block)
                })
                current_block = []

            blocks.append({
                "text": line,
                "type": detect_line_type(line)
            })
        else:
            current_block.append(line)

    if current_block:
        blocks.append({
            "text": " ".join(current_block),
            "type": "paragraph"
        })

    return blocks


# --------------------------------
# Detect boundaries & structures
# --------------------------------

def is_new_structure(line: str) -> bool:
    return (
        is_heading(line)
        or is_question(line)
        or is_bullet(line)
        or is_numbered_section(line)
    )


def is_heading(line: str) -> bool:
    words = line.split()
    if len(words) > 12:
        return False
    if len(line) > 90:
        return False
    if line.endswith("."):
        return False
    if re.match(r"^\d+(\.\d+)*\s+", line):
        return True
    capital_words = sum(1 for word in words if word[0].isupper())
    return capital_words >= max(2, len(words) // 2)


def is_question(line: str) -> bool:
    return bool(re.match(r"^(Q\d+|Question\s+\d+)", line, re.IGNORECASE))


def is_bullet(line: str) -> bool:
    return bool(re.match(r"^[•\-\*]", line))


def is_numbered_section(line: str) -> bool:
    return bool(re.match(r"^\d+[\.\)]", line))


def detect_line_type(line: str) -> str:
    if is_question(line):
        return "question"
    if is_bullet(line):
        return "list"
    if is_numbered_section(line):
        return "section"
    if is_heading(line):
        return "heading"
    return "paragraph"


def detect_block_type(lines: List[str]) -> str:
    return detect_line_type(lines[0])


# --------------------------------
# Create final chunks
# --------------------------------

def build_chunks(
    blocks: List[Dict[str, Any]],
    max_words: int
) -> List[Dict[str, Any]]:
    chunks = []
    current_text = []
    current_type = None
    word_count = 0

    for block in blocks:
        block_words = len(block["text"].split())

        if word_count + block_words > max_words and current_text:
            chunks.append({
                "text": " ".join(current_text),
                "chunk_type": current_type
            })
            current_text = []
            word_count = 0

        current_text.append(block["text"])
        current_type = block["type"]
        word_count += block_words

    if current_text:
        chunks.append({
            "text": " ".join(current_text),
            "chunk_type": current_type
        })

    return chunks