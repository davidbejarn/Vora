import requests

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

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            f"{GEMINI_API_URL}?key={API_KEY}",
            json=payload,
            headers=headers,
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"(Error con Gemini: {e})"
