"""Chatbot 2 (variante): el historial entra como MENSAJES con rol (MessagesPlaceholder).

Diferencia con app/streamlit_chatbot2.py:
  - allí el historial se pega como TEXTO dentro de un único mensaje `human`;
  - aquí cada mensaje anterior conserva su rol (human / ai) gracias a MessagesPlaceholder.

Ejecutar desde esta carpeta:  streamlit run streamlit_chatbot2.py
"""
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from modelo_llm import crear_llm, texto

st.set_page_config(page_title="Chatbot con MessagesPlaceholder", page_icon="💬")
st.title("💬 Chatbot con MessagesPlaceholder")

with st.sidebar:
    temperature = st.slider("Temperatura", 0.0, 1.0, 0.5, 0.1)

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "El asistente se llama ChatBot Pro y es útil y amigable. Responde de forma clara y concisa."),
    MessagesPlaceholder(variable_name="historial"),
    ("human", "{mensaje}"),
])
cadena = chat_prompt | crear_llm(temperature=temperature)

for msg in st.session_state.mensajes:
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
            respuesta = texto(cadena.invoke({"historial": st.session_state.mensajes, "mensaje": pregunta}))
            st.markdown(respuesta)
        st.session_state.mensajes += [HumanMessage(content=pregunta), AIMessage(content=respuesta)]
    except Exception as e:
        st.error(f"Error al generar respuesta: {e}")
