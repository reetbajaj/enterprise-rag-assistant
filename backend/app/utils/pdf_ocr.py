import fitz  # PyMuPDF
import io
from PIL import Image
import numpy as np

_ocr_reader = None


def get_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        _ocr_reader = easyocr.Reader(["en"], gpu=False)
    return _ocr_reader


def extract_text_with_ocr(pdf_path):
    """
    Extracts text from a PDF using:
    1. PyMuPDF for selectable text
    2. EasyOCR for pages with little/no selectable text
    """
    doc = fitz.open(pdf_path)
    full_text = ""
    try:
        reader = None
        for page_num, page in enumerate(doc):
            text = page.get_text("text").strip()

            if len(text) > 100:
                full_text += f"\n\n--- Page {page_num + 1} ---\n"
                full_text += text
                continue

            if reader is None:
                reader = get_reader()

            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))
            image_array = np.array(image)

            result = reader.readtext(image_array)
            ocr_text = "\n".join([item[1] for item in result if item[1].strip()])

            full_text += f"\n\n--- Page {page_num + 1} (OCR) ---\n"
            full_text += ocr_text
    finally:
        doc.close()

    return full_text