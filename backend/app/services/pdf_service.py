import fitz
import logging
from typing import List, Dict, Any

_reader = None


def get_ocr_reader():
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def extract_pages(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract PDF page by page.
    Uses PyMuPDF text extraction, falling back to EasyOCR if text is empty and images exist.
    """
    pages = []
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logging.error(f"Failed to open PDF at {pdf_path}: {e}")
        raise ValueError(f"Could not open PDF file: {str(e)}")

    try:
        for page_num, page in enumerate(doc):
            text = page.get_text("text").strip()
            has_images = len(page.get_images()) > 0

            if len(text) > 30:
                logging.debug(f"Page {page_num + 1}: Direct text extracted ({len(text)} chars)")
            elif has_images:
                try:
                    logging.info(f"Page {page_num + 1}: Running OCR fallback")
                    reader = get_ocr_reader()
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                    img_bytes = pix.tobytes("png")
                    result = reader.readtext(img_bytes)
                    ocr_lines = [item[1] for item in result if item[1].strip()]
                    if ocr_lines:
                        text = "\n".join(ocr_lines)
                except Exception as ocr_err:
                    logging.warning(f"OCR failed for page {page_num + 1}: {ocr_err}")

            pages.append({
                "page_number": page_num + 1,
                "text": text,
                "has_images": has_images
            })
    finally:
        doc.close()

    return pages