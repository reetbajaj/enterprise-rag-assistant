def faithfulness_score(answer, contexts):

    answer_words = set(
        answer.lower().split()
    )

    context_words = set(
        " ".join(contexts)
        .lower()
        .split()
    )


    if not answer_words:
        return 0


    supported_words = (
        answer_words.intersection(
            context_words
        )
    )


    return round(
        len(supported_words)
        /
        len(answer_words),
        2
    )

if __name__ == "__main__":

    answer = "The minimum GPA requirement is 7"

    contexts = [
        "The candidate must have a minimum cumulative 7 GPA"
    ]

    print(
        faithfulness_score(
            answer,
            contexts
        )
    )