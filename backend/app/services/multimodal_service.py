import re
import logging
from typing import List, Dict, Any, Optional
import fitz
from app.utils.pdf_ocr import get_reader as get_ocr_reader


def _clean_table_rows(table_data: List[List[Any]]) -> List[List[str]]:
    """
    Normalize PyMuPDF table output without destroying column alignment.

    PyMuPDF often represents bordered tables as:
        ["Name", None, None, "Close", None, ...]
    where the None values are spacer cells inside the same logical column.
    Removing those cells shifts values into the wrong columns. Instead we
    collapse consecutive/duplicate layout cells only when they are clearly
    empty trailing/spacer cells, while preserving the logical positions of
    populated cells.
    """
    rows: List[List[str]] = []
    max_cols = 0

    for row in table_data or []:
        cells = [
            "" if cell is None else str(cell).strip().replace("\n", " ")
            for cell in row
        ]
        # Keep positional empties; they are meaningful for column alignment.
        # Trim only empty cells at the far right.
        while cells and not cells[-1]:
            cells.pop()
        if cells:
            rows.append(cells)
            max_cols = max(max_cols, len(cells))

    for row in rows:
        row.extend([""] * (max_cols - len(row)))
    return rows


def _looks_like_header(row: List[str]) -> bool:
    """Identify a real table header without assuming a particular document."""
    if not row:
        return False

    cells = [str(c).strip() for c in row]
    nonempty = [c for c in cells if c]
    if not nonempty:
        return False

    numeric = sum(bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?", c.replace(",", "")))
                  for c in nonempty)
    textual = sum(bool(re.search(r"[A-Za-z]", c)) for c in nonempty)

    header_terms = {
        "name", "close", "price", "current", "change", "trend", "pivot",
        "support", "resistance", "volume", "date", "time", "value",
        "average", "sema", "open", "high", "low", "company"
    }
    normalized = {re.sub(r"[^a-z0-9]+", " ", c.lower()).strip() for c in nonempty}
    has_header_term = bool(normalized & header_terms)

    # A real header is predominantly textual and normally contains several
    # populated cells. A section label such as "FINANCE COMPANY" has one cell
    # and therefore is not treated as a schema header.
    return (
        len(nonempty) >= 2
        and textual >= max(2, len(nonempty) // 2)
        and numeric < max(1, len(nonempty) // 2)
        and (has_header_term or len(nonempty) >= 3)
    )


def format_table_as_markdown(table_data: List[List[Any]]) -> Optional[str]:
    rows = _clean_table_rows(table_data)
    if len(rows) < 2:
        return None

    headers = rows[0]
    if not any(headers):
        headers = [f"Column {i+1}" for i in range(len(headers))]

    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    data_lines = ["| " + " | ".join(row) + " |" for row in rows[1:]]
    return "\n".join([header_line, separator_line] + data_lines)


def _canonical_header(header: str) -> str:
    """Normalize common table labels without tying the code to a document."""
    h = re.sub(r"[^a-z0-9%]+", " ", str(header).lower()).strip()
    aliases = {
        "close": "Close",
        "closing": "Close",
        "closing price": "Close",
        "current price": "Close",
        "last price": "Close",
        "% change": "% Change",
        "change": "% Change",
        "20 sema": "20 SEMA",
        "trend": "Trend",
        "pivot": "Pivot",
        "s1": "S1",
        "s2": "S2",
        "r1": "R1",
        "r2": "R2",
    }
    return aliases.get(h, str(header).strip() or "Column")


def _table_semantic_rows(headers: List[str], rows: List[List[str]], heading: str) -> List[Dict[str, Any]]:
    """Create one self-contained, semantically searchable record per table row."""
    canonical_headers = [_canonical_header(h) for h in headers]
    records = []

    for row in rows:
        if not any(str(v).strip() for v in row):
            continue

        pairs = []
        for i, value in enumerate(row):
            label = canonical_headers[i] if i < len(canonical_headers) else f"Column {i+1}"
            value = str(value).strip()
            if value:
                pairs.append(f"{label}={value}")

        if not pairs:
            continue

        # Include natural-language aliases in addition to the structured form.
        # This helps embedding models map questions such as "closing price" to
        # a column named "Close" without special-casing any company/document.
        text = (
            f"### {heading}\n"
            f"Structured table row: " + "; ".join(pairs) + "\n"
            f"Row data: " + " | ".join(
                f"{label}: {str(value).strip()}"
                for label, value in zip(canonical_headers, row)
                if str(value).strip()
            )
        )
        records.append({
            "content_type": "table",
            "source_type": "pdf_table_row",
            "chunk_type": "table_row",
            "heading": heading,
            "text": text,
        })

    return records


def extract_tables_from_page(
    page: fitz.Page,
    page_number: int,
    inherited_headers: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Extract structured tables and row-level retrieval records.

    Important: PDF table pages frequently repeat a section/category label as the
    first extracted row (for example "FINANCE COMPANY") rather than repeating
    the actual schema. Such a row must not overwrite inherited headers.
    """
    tables_found: List[Dict[str, Any]] = []

    try:
        finder = page.find_tables()
        tables = list(finder.tables) if finder and finder.tables else []
    except Exception as exc:
        logging.warning("PyMuPDF table detection failed on page %s: %s", page_number, exc)
        return tables_found

    for idx, tab in enumerate(tables):
        try:
            rows = _clean_table_rows(tab.extract())
            if not rows:
                continue

            first_row = rows[0]
            local_header = first_row if _looks_like_header(first_row) else None

            # Prefer a valid local schema. Otherwise carry forward the most
            # recent valid schema from a previous page/table.
            if local_header:
                headers = list(local_header)
                data_rows = rows[1:]
            elif inherited_headers and len(inherited_headers) >= 2:
                headers = list(inherited_headers)
                data_rows = rows
            else:
                # No reliable schema exists. Create positional columns rather
                # than inventing semantic names.
                width = max(len(r) for r in rows)
                headers = [f"Column {i+1}" for i in range(width)]
                data_rows = rows

            width = max(len(headers), *(len(r) for r in data_rows)) if data_rows else len(headers)
            headers = headers + [f"Column {i+1}" for i in range(len(headers), width)]
            data_rows = [r + [""] * (width - len(r)) for r in data_rows]

            # Drop section/category labels such as "FINANCE COMPANY" when they
            # occupy only the first logical column. Real data rows have values in
            # multiple columns, so this remains document-agnostic.
            data_rows = [
                r for r in data_rows
                if not (
                    r
                    and str(r[0]).strip()
                    and not any(str(v).strip() for v in r[1:])
                )
            ]

            bbox = tab.bbox
            heading = f"Table on Page {page_number}"
            try:
                header_rect = fitz.Rect(
                    bbox[0], max(0, bbox[1] - 80), bbox[2], bbox[1]
                )
                above_text = page.get_text("text", clip=header_rect).strip()
                if above_text:
                    first_line = above_text.splitlines()[-1].strip()
                    if 1 < len(first_line) < 120 and first_line.lower() not in {
                        "retail research", "page"
                    }:
                        heading = first_line
            except Exception:
                pass

            canonical_headers = [_canonical_header(h) for h in headers]
            md_table = format_table_as_markdown([canonical_headers] + data_rows)
            if not md_table:
                continue

            table_text = (
                f"### {heading}\n"
                f"**Columns**: " + " | ".join(canonical_headers) + "\n\n" +
                md_table
            )

            tables_found.append({
                "content_type": "table",
                "source_type": "pdf_table",
                "chunk_type": "table",
                "page_number": page_number,
                "heading": heading,
                "text": table_text,
                "bbox": bbox,
                "table_headers": canonical_headers,
            })

            tables_found.extend(
                _table_semantic_rows(canonical_headers, data_rows, heading)
            )

        except Exception as exc:
            logging.warning(
                "Structured table extraction failed on page %s table %s: %s",
                page_number, idx, exc
            )

    return tables_found

def extract_diagrams_or_figures_from_page(
    page: fitz.Page,
    page_number: int,
    table_bboxes: Optional[List[Any]] = None
) -> List[Dict[str, Any]]:
    """
    Detects drawings, architecture diagrams, charts, and figures on a PDF page.
    Renders high-resolution image crops and runs layout OCR to extract component labels and flow relationships.
    """
    visual_elements = []
    table_bboxes = table_bboxes or []

    try:
        images = page.get_images()
        drawings = page.get_drawings()

        # If page has substantial vector drawings (diagrams/charts) or embedded images
        if len(images) > 0 or len(drawings) > 5:
            # Check for figure/diagram captions on page
            full_page_text = page.get_text("text")
            figure_captions = re.findall(r"(Figure\s+\d+[:\.\-][^\n]+|Diagram\s+\d+[:\.\-][^\n]+|Architecture[:\.\-][^\n]+)", full_page_text, re.IGNORECASE)

            # High-res crop of the page to parse visual text labels
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            img_bytes = pix.tobytes("png")

            reader = get_ocr_reader()
            ocr_results = reader.readtext(img_bytes)

            # Filter out text already captured in clean direct text if it is just a paragraph
            # But capture spatial layout labels (e.g. arrows, boxes, components)
            visual_labels = []
            for item in ocr_results:
                text_label = item[1].strip()
                confidence = item[2]
                if len(text_label) > 1 and confidence > 0.3:
                    visual_labels.append(text_label)

            if visual_labels:
                joined_labels = " | ".join(visual_labels)
                caption = figure_captions[0] if figure_captions else f"Visual Element / Diagram on Page {page_number}"
                
                # Classify visual type
                lower_cap = (caption + " " + joined_labels).lower()
                if any(w in lower_cap for w in ["architecture", "diagram", "workflow", "pipeline", "framework", "system", "component"]):
                    content_type = "diagram"
                elif any(w in lower_cap for w in ["chart", "graph", "plot", "distribution", "metric"]):
                    content_type = "chart"
                else:
                    content_type = "figure"

                structured_visual_text = (
                    f"### {caption}\n"
                    f"**Visual Type**: {content_type.capitalize()}\n"
                    f"**Labels & Extracted Components**: {joined_labels}"
                )

                visual_elements.append({
                    "content_type": content_type,
                    "source_type": "pdf_visual",
                    "page_number": page_number,
                    "heading": caption,
                    "text": structured_visual_text
                })
    except Exception as e:
        logging.warning(f"Visual extraction failed on page {page_number}: {e}")

    return visual_elements


def extract_scanned_ocr_page(page: fitz.Page, page_number: int) -> Optional[Dict[str, Any]]:
    """
    Performs full-page high-resolution OCR on scanned/image pages where machine-readable text is absent.
    """
    try:
        logging.info(f"Page {page_number}: Running scanned page OCR extraction")
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        img_bytes = pix.tobytes("png")

        reader = get_ocr_reader()
        ocr_results = reader.readtext(img_bytes)

        lines = [item[1].strip() for item in ocr_results if item[1].strip()]
        if not lines:
            return None

        # Reconstruct paragraphs based on text flow
        ocr_text = "\n".join(lines)
        return {
            "content_type": "ocr",
            "source_type": "pdf_ocr",
            "page_number": page_number,
            "heading": f"Scanned Document (Page {page_number})",
            "text": ocr_text
        }
    except Exception as e:
        logging.error(f"Scanned page OCR failed on page {page_number}: {e}")
        return None
