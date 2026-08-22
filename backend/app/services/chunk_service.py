import re



def chunk_pages(
    pages,
    max_words=500
):

    all_chunks = []


    for page in pages:

        text = page["text"].strip()


        if not text:
            continue


        blocks = split_into_blocks(
            text
        )


        chunks = build_chunks(
            blocks,
            max_words
        )


        for chunk in chunks:

            all_chunks.append(
                {
                    "text": chunk["text"],

                    "page_number":
                    page["page_number"],

                    "chunk_type":
                    chunk["chunk_type"],

                    "heading":
                    chunk.get("heading"),

                    "has_images":
                    page.get(
                        "has_images",
                        False
                    )
                }
            )


    return all_chunks




# --------------------------------
# Split document into logical blocks
# --------------------------------


def split_into_blocks(text):

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

                blocks.append(
                    {
                        "text":
                        " ".join(current_block),

                        "type":
                        detect_block_type(
                            current_block
                        )
                    }
                )


                current_block = []



            blocks.append(
                {
                    "text": line,

                    "type":
                    detect_line_type(
                        line
                    )
                }
            )


        else:

            current_block.append(
                line
            )



    if current_block:

        blocks.append(
            {
                "text":
                " ".join(current_block),

                "type":
                "paragraph"
            }
        )


    return blocks





# --------------------------------
# Detect boundaries
# --------------------------------


def is_new_structure(line):


    return (

        is_heading(line)

        or

        is_question(line)

        or

        is_bullet(line)

        or

        is_numbered_section(line)

    )





# --------------------------------
# Structure detection
# --------------------------------


def is_heading(line):

    words = line.split()


    if len(words) > 10:
        return False


    if len(line) > 80:
        return False


    # Avoid normal sentences

    if line.endswith("."):
        return False


    # Numbered headings

    if re.match(
        r"^\d+(\.\d+)*\s+",
        line
    ):
        return True


    # Title case headings

    capital_words = sum(
        1
        for word in words
        if word[0].isupper()
    )


    return (
        capital_words >= max(
            2,
            len(words)//2
        )
    )




def is_question(line):

    return bool(
        re.match(
            r"^(Q\d+|Question\s+\d+)",
            line,
            re.IGNORECASE
        )
    )




def is_bullet(line):

    return bool(
        re.match(
            r"^[•\-\*]",
            line
        )
    )




def is_numbered_section(line):

    return bool(
        re.match(
            r"^\d+[\.\)]",
            line
        )
    )





# --------------------------------
# Block classification
# --------------------------------


def detect_line_type(line):


    if is_question(line):
        return "question"


    if is_bullet(line):
        return "list"


    if is_numbered_section(line):
        return "section"


    if is_heading(line):
        return "heading"


    return "paragraph"





def detect_block_type(lines):

    return detect_line_type(
        lines[0]
    )





# --------------------------------
# Create final chunks
# --------------------------------


def build_chunks(
    blocks,
    max_words
):

    chunks = []


    current_text = []

    current_type = None


    word_count = 0



    for block in blocks:


        block_words = len(
            block["text"].split()
        )



        if (
            word_count + block_words
            > max_words
            and current_text
        ):


            chunks.append(
                {
                    "text":
                    " ".join(current_text),

                    "chunk_type":
                    current_type
                }
            )


            current_text = []

            word_count = 0



        current_text.append(
            block["text"]
        )


        current_type = block["type"]


        word_count += block_words



    if current_text:

        chunks.append(
            {
                "text":
                " ".join(current_text),

                "chunk_type":
                current_type
            }
        )


    return chunks