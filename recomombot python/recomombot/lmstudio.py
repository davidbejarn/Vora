import requests

# Endpoint
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


API_KEY = "AIzaSyCzgnAQbQ91Ekk6K-SALROh0Fas-T8MJzg"


SYSTEM_PROMPT = (
    "Eres un experto en literatura. Tu tarea es recomendar principalmente LIBROS, "
    "aunque también puedes sugerir películas o series si el usuario lo pide. "
    "Las recomendaciones deben ser claras, concisas y máximo 3 títulos."
)

def ask_gemini(user_prompt):
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT},  
                    {"text": user_prompt}     
                ]
            }
        ]
    }

    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            f"{GEMINI_API_URL}?key={API_KEY}",
            json=payload,
            headers=headers,
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
        # Extraer la respuesta
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except requests.exceptions.RequestException as e:
        return f"(No se pudo conectar a Gemini: {e})"
    except KeyError:
        return f"(La respuesta no tiene el formato esperado: {response.text})"


# Ejemplo de uso
if __name__ == "__main__":
    pregunta = "Recomiéndame libros de ciencia ficción modernos"
    print(ask_gemini(pregunta))

##Muerte si se comparte jajjajaja API Key: AIzaSyCzgnAQbQ91Ekk6K-SALROh0Fas-T8MJzg