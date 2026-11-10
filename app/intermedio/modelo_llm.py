"""Ayuda común de los ejercicios de esta carpeta: crea el modelo (Gemini u OpenAI).

Lee las claves del .env (el de la raíz del proyecto sirve):
  - si hay OPENAI_API_KEY real  -> ChatOpenAI(gpt-4o-mini)   (como en clase)
  - si no, y hay GOOGLE_API_KEY -> ChatGoogleGenerativeAI(gemini-3.8-flash)
Puedes forzar el modelo con MODELO=... (ej.: MODELO=gemini-3.8-flash).
"""
import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))


def _real(nombre):
    valor = (os.getenv(nombre) or "").strip()
    return valor if valor and "clave" not in valor.lower() and "aqui" not in valor.lower() else None


def crear_llm(temperature=0):
    nombre = os.getenv("MODELO", "").strip()
    if not nombre:
        nombre = "gpt-4o-mini" if _real("OPENAI_API_KEY") else "gemini-3.8-flash"
    if nombre.startswith("gemini"):
        from langchain_google_genai import ChatGoogleGenerativeAI

        extra = {} if nombre.startswith("gemini-3") else {"temperature": temperature}
        return ChatGoogleGenerativeAI(
            model=nombre, google_api_key=_real("GOOGLE_API_KEY"), timeout=30, max_retries=1, **extra
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=nombre, temperature=temperature, api_key=_real("OPENAI_API_KEY"), timeout=30, max_retries=1
    )


def texto(respuesta):
    """Devuelve el texto de la respuesta (Gemini 3.x entrega una lista de bloques)."""
    contenido = getattr(respuesta, "content", respuesta)
    if isinstance(contenido, list):
        return "".join(
            b.get("text", "") if isinstance(b, dict) else str(b) for b in contenido
        )
    return str(contenido)
