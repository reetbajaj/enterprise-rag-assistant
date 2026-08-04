def chunk_pages(pages, chunk_size=800, overlap=100):

    chunks = []

    for page in pages:

        words = page["text"].split()

        start = 0

        while start < len(words):

            end = start + chunk_size

            chunk = " ".join(
                words[start:end]
            )

            chunks.append(
                {
                    "text": chunk,
                    "page_number": page["page_number"]
                }
            )

            start = end - overlap

    return chunks