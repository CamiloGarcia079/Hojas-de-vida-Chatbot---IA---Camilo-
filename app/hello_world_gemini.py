import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from utils_chat import extraer_texto

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
modelo = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
llm = ChatGoogleGenerativeAI(model=modelo, temperature=0.7, google_api_key=api_key)

pregunta = "¿En qué año llegó el ser humano a la Luna por primera vez?"
print("Pregunta: ", pregunta)

respuesta = llm.invoke(pregunta)

# Gemini 3.x devuelve el contenido como lista de bloques: respuesta.content[0]['text'].
# extraer_texto() funciona con las dos formas (texto o lista).
print("Respuesta del modelo: ", extraer_texto(respuesta.content))
