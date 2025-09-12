import requests

AINIZE_API_URL = "https://ainize.ai/api/v1/llama/3.2/90B"

def ask_ainize(prompt):
    payload = {
        "model": "meta-llama/llama-3-2-90b",
        "messages": [
            {"role": "system", "content": "Eres un experto que recomienda películas y libros máximo 3 recomendaciones."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    try:
        headers = {"Authorization": "Bearer tu_api_key_aqui"}
        response = requests.post(AINIZE_API_URL, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"(No se pudo conectar al modelo: {e})"




