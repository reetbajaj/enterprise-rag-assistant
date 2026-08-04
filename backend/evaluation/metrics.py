def precision_at_k(retrieved_chunks, expected_chunks):

    retrieved = [
        (
            chunk["filename"],
            chunk["chunk_number"]
        )
        for chunk in retrieved_chunks
    ]


    expected = [
        (
            chunk["filename"],
            chunk["chunk_number"]
        )
        for chunk in expected_chunks
    ]


    relevant = 0

    for item in retrieved:
        if item in expected:
            relevant += 1


    if len(retrieved) == 0:
        return 0


    return relevant / len(retrieved)


def recall_at_k(retrieved_chunks, expected_chunks):

    retrieved = [
        (
            chunk["filename"],
            chunk["chunk_number"]
        )
        for chunk in retrieved_chunks
    ]


    expected = [
        (
            chunk["filename"],
            chunk["chunk_number"]
        )
        for chunk in expected_chunks
    ]


    relevant_found = 0

    for item in expected:
        if item in retrieved:
            relevant_found += 1


    if len(expected) == 0:
        return 0


    return relevant_found / len(expected)