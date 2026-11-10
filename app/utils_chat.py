"""Funciones de apoyo para los chatbots (las usan streamlit_chatbot.py y full_chatbot.py)."""
import os

import streamlit as st
from langchain_core.messages import HumanMessage, SystemMessage


def extraer_texto(contenido):
    """Devuelve siempre un str con el texto de la respuesta del modelo.

    OpenAI y Gemini 2.x devuelven el contenido como texto (str).
    Gemini 3.x lo devuelve como lista de bloques: [{'type': 'text', 'text': '...'}].
    """
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        partes = []
        for bloque in contenido:
            if isinstance(bloque, str):
                partes.append(bloque)
            elif isinstance(bloque, dict) and bloque.get("type") == "text":
                partes.append(bloque.get("text", ""))
        return "".join(partes)
    return str(contenido)


def leer_clave(nombre):
    """Busca la clave en las variables de entorno y, si no está, en st.secrets."""
    valor = os.getenv(nombre)
    if valor:
        return valor
    try:
        return st.secrets.get(nombre)
    except Exception:
        # no existe .streamlit/secrets.toml
        return None


def formatear_historial(mensajes):
    """Pasa la lista de mensajes a texto, para meterlo en el prompt."""
    lineas = []
    for m in mensajes:
        if isinstance(m, SystemMessage):
            continue
        autor = "Usuario" if isinstance(m, HumanMessage) else "Asistente"
        lineas.append(f"{autor}: {extraer_texto(m.content)}")
    return "\n".join(lineas)
