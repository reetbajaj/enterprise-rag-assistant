import logging
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"


def generate_answer(question: str, context: str) -> str:
    prompt = f"""You are an enterprise document assistant.

Follow these rules strictly:
1. Answer ONLY using the facts stated in the provided context.
2. Do not extrapolate, assume, or use any outside knowledge.
3. Do not mention chunks, embeddings, vectors, or retrieval systems.
4. Do not invent page numbers or citations not in the text.
5. If the provided context does not contain enough information to answer the question, reply ONLY with:
"I don't know based on the provided documents."

Context:
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
                    "top_k": 10
                }
            },
            timeout=45
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