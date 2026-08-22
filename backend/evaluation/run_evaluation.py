import json

from app.services.rag_service import answer_question
from evaluation.metrics import (
    precision_at_k,
    recall_at_k
)
from evaluation.answer_metrics import (
    faithfulness_score
)


def load_questions():

    with open(
        "evaluation/questions.json",
        "r"
    ) as file:

        return json.load(file)



def evaluate():

    questions = load_questions()

    total = len(questions)

    passed = 0

    precision_scores = []
    recall_scores = []

    failed_questions = []


    for item in questions:

        question = item["question"]

        print("\nQuestion:")
        print(question)


        user_id = item.get("user_id", 1)
        result = answer_question(question, user_id=user_id)


        print("\nAnswer:")
        print(result["answer"])

        sources = result["sources"]


        contexts = [
            source["text"]
            for source in result["retrieved_chunks"]
        ]


        precision = precision_at_k(
            sources,
            item["expected_chunks"]
        )


        recall = recall_at_k(
            sources,
            item["expected_chunks"]
        )


        precision_scores.append(precision)
        recall_scores.append(recall)


        print(
            "Precision@K:",
            precision
        )

        print(
            "Recall@K:",
            recall
        )
        contexts = [
            chunk["text"]
            for chunk in result["retrieved_chunks"]
        ]


        faithfulness = faithfulness_score(
            result["answer"],
            contexts
        )


        print(
            "Faithfulness:",
            faithfulness
        )


        if precision >= 0.5:

            passed += 1
            print("✅ PASS")

        else:

            print("❌ FAIL")

            failed_questions.append(
                {
                    "question": question,
                    "precision": precision,
                    "recall": recall
                }
            )


    average_precision = (
        sum(precision_scores)
        /
        len(precision_scores)
    )


    average_recall = (
        sum(recall_scores)
        /
        len(recall_scores)
    )


    report = {

        "total_questions": total,

        "passed": passed,

        "failed": total - passed,

        "average_precision": round(
            average_precision,
            3
        ),

        "average_recall": round(
            average_recall,
            3
        ),

        "failed_questions": failed_questions
    }


    with open(
        "evaluation/report.json",
        "w"
    ) as file:

        json.dump(
            report,
            file,
            indent=4
        )


    print("\n===================")

    print(report)

    print(
        "\nReport saved: evaluation/report.json"
    )


if __name__ == "__main__":
    evaluate()