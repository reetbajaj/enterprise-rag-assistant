import logging
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"


def generate_answer(question: str, context: str) -> str:
    prompt = f"""You are an enterprise document assistant.

Answer the user's question using ONLY the supplied evidence.

Grounding rules:
1. Use only facts explicitly present in the evidence.
2. Never use outside knowledge or fill missing facts by guessing.
3. If the evidence contains a structured table, use its column headers and row labels
   to map values correctly. Do not reinterpret a numeric value as a different field.
4. If the evidence says a document contains a field such as Close, Trend, S1, Pivot,
   etc., preserve that field meaning exactly.
5. A value from one document or table must never be attributed to another document.
6. For comparisons, answer each requested side only from evidence supporting that side.
7. For summaries, summarize the scoped evidence rather than unrelated retrieved material.
8. If some requested aspect is absent but other requested aspects are supported, answer
   the supported aspects and explicitly state which aspect is not stated.
9. If NONE of the requested information is supported by the evidence, reply exactly:
"I don't know based on the provided documents."
10. Do not mention chunks, embeddings, vectors, retrieval, ranking, or internal systems.
11. Do not invent citations, page numbers, document names, or numerical values.

Important:
- "Close" in a table means the document's Close field. Do not silently call it a
  live/current price unless the evidence explicitly does so.
- When a question asks for a previous closing price and the evidence only provides
  a Close value, say that the previous closing price is not stated rather than
  converting the Close value into a previous close.

Evidence:
{context}

Question:
{question}

Answer:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "top_p": 0.1,
                    "top_k": 10,
                },
            },
            timeout=45,
        )
        response.raise_for_status()
        result = response.json()
        answer = result.get("response", "").strip()
        return answer if answer else "I don't know based on the provided documents."
    except requests.exceptions.ConnectionError:
        logging.error("Could not connect to Ollama server at http://localhost:11434")
        return "Error: LLM service (Ollama) is currently unavailable. Please ensure Ollama is running."
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        return f"Error generating answer from LLM: {str(e)}"
