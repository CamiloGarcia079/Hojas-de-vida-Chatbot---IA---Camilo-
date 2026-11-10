"""Chatbot 2: el chatbot básico migrado de PromptTemplate a ChatPromptTemplate.

Tarea de clase «Mejora tu Chatbot con ChatPromptTemplate»:
  - mensaje `system` (comportamiento) separado del mensaje `human` (historial + pregunta)
  - desafío: selector de personalidad en la barra lateral que cambia el mensaje `system`

Ejecutar:  streamlit run streamlit_chatbot2.py
"""
import os

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from utils_chat import extraer_texto, formatear_historial

load_dotenv()

st.set_page_config(page_title="Chatbot con ChatPromptTemplate", page_icon="🤖")
st.title("🤖 Chatbot con ChatPromptTemplate")

SISTEMA_POR_PERSONALIDAD = {
    "Útil y amigable": (
        "El asistente se llama ChatBot Pro y se caracteriza por ser "
        "útil y amigable. Sus respuestas deben ser claras y concisas."
    ),
    "Profesional y formal": (
        "El asistente mantiene un estilo profesional y formal. "
        "Sus respuestas deben ser precisas y estar bien estructuradas."
    ),
    "Casual y relajado": (
        "El asistente mantiene un estilo casual y relajado. "
        "Su lenguaje debe ser natural, cercano y amigable."
    ),
    "Experto técnico": (
        "El asistente actúa como un experto técnico. "
        "Sus respuestas deben ser detalladas y técnicamente precisas."
    ),
    "Creativo y divertido": (
        "El asistente mantiene un estilo creativo y divertido. "
        "Sus respuestas deben incluir analogías y ejemplos creativos, con un tono alegre."
    ),
}

with st.sidebar:
    st.header("Configuración")
    temperature = st.slider("Temperatura", 0.0, 1.0, 0.5, 0.1)
    model_name = st.selectbox("Modelo", ["gemini-3.8-flash", "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"])
    personalidad = st.selectbox("Personalidad del asistente", list(SISTEMA_POR_PERSONALIDAD))

    if model_name.startswith("gemini"):
        chat_model = ChatGoogleGenerativeAI(
            model=model_name, temperature=temperature, google_api_key=os.getenv("GOOGLE_API_KEY")
        )
    else:
        chat_model = ChatOpenAI(model=model_name, temperature=temperature, api_key=os.getenv("OPENAI_API_KEY"))

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# Plantilla de mensajes con roles: el system cambia según la personalidad elegida
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", SISTEMA_POR_PERSONALIDAD[personalidad]),
    ("human", "Historial de conversación:\n{historial}\n\nPregunta actual: {mensaje}"),
])

# Conexión de la plantilla con el modelo (LCEL)
cadena = chat_prompt | chat_model

for msg in st.session_state.mensajes:
    if isinstance(msg, SystemMessage):
        continue
    with st.chat_message("assistant" if isinstance(msg, AIMessage) else "user"):
        st.markdown(msg.content)

if st.button("🗑️ Nueva conversación"):
    st.session_state.mensajes = []
    st.rerun()

pregunta = st.chat_input("Escribe tu mensaje:")

if pregunta:
    with st.chat_message("user"):
        st.markdown(pregunta)
    try:
        with st.chat_message("assistant"):
            hueco = st.empty()
            respuesta = ""
            historial = formatear_historial(st.session_state.mensajes)
            for chunk in cadena.stream({"mensaje": pregunta, "historial": historial}):
                respuesta += extraer_texto(chunk.content)
                hueco.markdown(respuesta + "▌")
            hueco.markdown(respuesta)
        st.session_state.mensajes.append(HumanMessage(content=pregunta))
        st.session_state.mensajes.append(AIMessage(content=respuesta))
    except Exception as e:
        st.error(f"Error al generar respuesta: {e}")
        st.info("Verifica que tu API Key (GOOGLE_API_KEY u OPENAI_API_KEY) esté configurada en el .env.")
