import fitz


def extract_pages(file_path):

    doc = fitz.open(file_path)

    pages = []

    for page_number, page in enumerate(doc):

        text = page.get_text()

        pages.append(
            {
                "page_number": page_number + 1,
                "text": text
            }
        )

    return pages