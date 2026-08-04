import requests


OLLAMA_URL = "http://localhost:11434/api/generate"


def generate_answer(question, context):

    prompt = f"""
You are an enterprise document assistant.

Rules:
1. Answer only using the provided context.
2. Do not mention chunk numbers.
3. Do not create citations.
4. If the answer is not in the context, say:
"I don't know based on the provided documents."

Context:

{context}


Question:

{question}


Answer:
"""


    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "llama3.2",
            "prompt": prompt,
            "stream": False
        }
    )


    result = response.json()

    return result["response"]