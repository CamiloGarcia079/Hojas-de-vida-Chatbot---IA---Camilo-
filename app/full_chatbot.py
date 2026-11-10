import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:
    ChatGoogleGenerativeAI = None

from utils_chat import extraer_texto, formatear_historial, leer_clave

load_dotenv()

# Configuración inicial
st.set_page_config(page_title="Chatbot Básico", page_icon="🤖")
st.title("🤖 Chatbot Básico con LangChain")
st.markdown("Este es un *chatbot de ejemplo* construido con LangChain + Streamlit. ¡Escribe tu mensaje abajo para comenzar!")

with st.sidebar:
    st.header("Configuración")
    temperature = st.slider("Temperatura", 0.0, 1.0, 0.5, 0.1)
    model_name = st.selectbox(
        "Modelo",
        ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gpt-3.5-turbo", "gpt-4", "gpt-4o-mini"],
    )

    # Cargar API key según el proveedor del modelo seleccionado
    is_gemini_model = model_name.startswith("gemini")
    key_name = "GOOGLE_API_KEY" if is_gemini_model else "OPENAI_API_KEY"
    provider_name = "Google" if is_gemini_model else "OpenAI"
    api_key = leer_clave(key_name)
    if not api_key:
        api_key = st.text_input(f"{provider_name} API Key", type="password")
        st.caption(f"También puedes configurarla en {key_name} o en .streamlit/secrets.toml")

    st.caption(f"Proveedor activo: {provider_name} · modelo: {model_name}")

# Inicializar el historial de mensajes en session_state
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# Crear el template de prompt con comportamiento específico
prompt_template = PromptTemplate(
    input_variables=["mensaje", "historial"],
    template="""Eres un asistente útil y amigable llamado ChatBot Pro. 

Historial de conversación:
{historial}

Responde de manera clara y concisa a la siguiente pregunta: {mensaje}""",
)

# Crear cadena usando LCEL (LangChain Expression Language)
cadena = None
if api_key:
    if is_gemini_model:
        if ChatGoogleGenerativeAI is None:
            st.error("Falta la dependencia para Gemini: instala `langchain-google-genai`.")
        else:
            chat_model = ChatGoogleGenerativeAI(model=model_name, temperature=temperature, google_api_key=api_key)
            cadena = prompt_template | chat_model
    else:
        chat_model = ChatOpenAI(model=model_name, temperature=temperature, api_key=api_key)
        cadena = prompt_template | chat_model

# Renderizar historial existente
for msg in st.session_state.mensajes:
    if isinstance(msg, SystemMessage):
        continue  # no mostrar mensajes del sistema al usuario

    role = "assistant" if isinstance(msg, AIMessage) else "user"
    with st.chat_message(role):
        st.markdown(msg.content)

if st.button("🗑️ Nueva conversación"):
    st.session_state.mensajes = []
    st.rerun()

# Input de usuario
pregunta = st.chat_input("Escribe tu mensaje:")

if pregunta:
    if not cadena:
        st.error(f"Falta la API Key de {provider_name}. Configura {key_name} para continuar.")
        st.stop()

    # Mostrar y almacenar mensaje del usuario
    with st.chat_message("user"):
        st.markdown(pregunta)

    # Generar y mostrar respuesta del asistente
    try:
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            # Streaming de la respuesta
            historial = formatear_historial(st.session_state.mensajes)
            for chunk in cadena.stream({"mensaje": pregunta, "historial": historial}):
                full_response += extraer_texto(chunk.content)
                response_placeholder.markdown(full_response + "▌")

            response_placeholder.markdown(full_response)

        st.session_state.mensajes.append(HumanMessage(content=pregunta))
        st.session_state.mensajes.append(AIMessage(content=full_response))

    except Exception as e:
        st.error(f"Error al generar respuesta: {str(e)}")
        st.info(f"Verifica que tu API Key de {provider_name} ({key_name}) esté configurada correctamente.")


# =============================================================================
# ANÁLISIS: ¿la respuesta sale por OpenAI o por Gemini? ¿Qué se arregló?
# =============================================================================
# 1) Quién responde depende solo del modelo elegido en la barra lateral:
#      - si el nombre empieza por "gemini"  -> ChatGoogleGenerativeAI, usa GOOGLE_API_KEY
#      - cualquier otro (gpt-...)           -> ChatOpenAI, usa OPENAI_API_KEY
#    Abajo del selector hay una línea con el proveedor activo para verlo en pantalla.
#    Si no tienes saldo en OpenAI, escoge un modelo gemini y no se llama a OpenAI nunca.
#
# 2) Problema encontrado (se ve en la captura del profe): los modelos Gemini 3.x no
#    devuelven el contenido como texto sino como una lista de bloques:
#        [{'type': 'text', 'text': 'La respuesta...'}]
#    Por eso en hello_world_gemini.py el profe escribió respuesta.content[0]['text'].
#    En el chatbot, la línea  full_response += chunk.content  intenta sumar un str con
#    una lista y falla (TypeError), y el usuario ve "Error al generar respuesta".
#    OpenAI y los Gemini 2.x normalmente devuelven un str, por eso ahí sí funciona.
#    Solución: extraer_texto() (en utils_chat.py) acepta las dos formas y siempre
#    devuelve un str.
#
# 3) El aviso "Model 'gemini-3.5-flash-lite' uses fixed sampling defaults ... temperature
#    will be ignored" no es un error: esos modelos ignoran el slider de temperatura.
#    Con gemini-3.8-flash y con OpenAI el slider sí cambia el resultado.
#
# 4) Otros ajustes pequeños:
#      - El historial se pasaba como lista de objetos; ahora se convierte a texto
#        "Usuario: ... / Asistente: ..." antes de meterlo en el prompt.
#      - st.secrets.get() falla si no existe .streamlit/secrets.toml; leer_clave()
#        lo controla y cae al cuadro de texto de la clave.
#      - Los modelos de Gemini van primero en la lista, para que por defecto no pida
#        la clave de OpenAI.
