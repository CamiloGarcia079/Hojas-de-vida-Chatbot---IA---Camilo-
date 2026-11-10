"""Interfaz de Streamlit: entradas, validaciones y presentación del análisis.

Esta capa no habla directamente con el modelo ni con el PDF: llama a los servicios.

Estado en st.session_state:
    resultado -> último análisis (se conserva aunque la página se vuelva a ejecutar).
    ronda     -> número que forma parte de la key de los campos; al pulsar «Limpiar»
                 aumenta, y Streamlit crea campos nuevos y vacíos.
"""
import json
from datetime import datetime

import streamlit as st

from models.criterios import CRITERIOS, evaluacion_principal, recomendacion_final
from models.errores import ErrorAnalizador
from services import modelo_llm
from services.cv_evaluator import evaluar_con_respaldo, validar_entradas
from services.pdf_processor import extraer_texto_pdf

OTRO = "Otro (escribir el nombre)…"

EJEMPLO_PUESTO = """Ejemplo detallado:

Puesto: Desarrollador Backend Junior

Requisitos obligatorios:
- 1+ año de experiencia desarrollando APIs REST
- Java con Spring Boot o Python
- Bases de datos relacionales (PostgreSQL o MySQL)
- Manejo de Git

Requisitos deseables:
- Docker
- Pruebas automatizadas
- Experiencia con LangChain o modelos de IA

Responsabilidades:
- Desarrollar y mantener servicios backend
- Integrar APIs de terceros
- Escribir y mantener pruebas"""

INSTRUCCIONES = """**Instrucciones:**
1. Sube un CV en formato PDF en la columna izquierda
2. Describe detalladamente el puesto de trabajo
3. Haz clic en "Analizar Candidato"
4. Aquí aparecerá el análisis completo del candidato

**Consejos para mejores resultados:**
- Usa CVs con texto seleccionable (no imágenes escaneadas)
- Sé específico en la descripción del puesto
- Incluye tanto requisitos obligatorios como deseables"""


# --------------------------------------------------------------------- estado
def iniciar_estado() -> None:
    st.session_state.setdefault("resultado", None)
    st.session_state.setdefault("ronda", 0)


def limpiar_todo() -> None:
    """Botón «Limpiar»: borra el resultado y deja el archivo y la descripción vacíos."""
    st.session_state.resultado = None
    st.session_state.ronda += 1


def _md(texto) -> str:
    """Evita que un '$' del CV se interprete como fórmula matemática en Streamlit."""
    return str(texto).replace("$", "\\$")


# ------------------------------------------------------------- barra lateral
@st.cache_data(ttl=3600, show_spinner=False)
def modelos_disponibles(proveedor: str, clave: str | None) -> list[str]:
    """Se pregunta a Google una vez por hora, no en cada clic."""
    return modelo_llm.listar_modelos(proveedor, clave)


def configurar_modelo() -> tuple[list[str], str | None]:
    """Proveedor, clave, modelo y respaldo. Devuelve (modelos a probar en orden, clave)."""
    st.header("⚙️ Configuración")
    solo_openai = modelo_llm.obtener_clave("openai") and not modelo_llm.obtener_clave("google")
    proveedor = st.radio(
        "Proveedor", ["google", "openai"], index=1 if solo_openai else 0, horizontal=True,
        format_func=lambda p: "Google (Gemini)" if p == "google" else "OpenAI",
    )
    clave = modelo_llm.obtener_clave(proveedor)
    if clave is None:
        clave = st.text_input(
            f"{modelo_llm.VARIABLE_CLAVE[proveedor]} (solo esta sesión)", type="password"
        ).strip() or None

    disponibles = modelos_disponibles(proveedor, clave)
    preferido = modelo_llm.valor_real("GEMINI_MODEL" if proveedor == "google" else "OPENAI_MODEL")
    opciones = list(dict.fromkeys([*([preferido] if preferido else []), *disponibles])) + [OTRO]
    elegido = st.selectbox("Modelo", opciones, index=0)
    if elegido == OTRO:
        elegido = st.text_input("Nombre del modelo", placeholder="ej.: gemini-3.5-flash-lite").strip()
        if not elegido:
            st.caption("Escribe el nombre del modelo para poder analizar.")
            elegido = opciones[0]

    respaldo = st.checkbox("Si el modelo está saturado, probar otro", value=True)
    modelos = modelo_llm.cadena_de_respaldo(elegido, disponibles) if respaldo else [elegido]
    st.caption("Orden de prueba: " + " → ".join(modelos))
    st.caption(f"Máximo {modelo_llm.TIEMPO_MAXIMO} s por modelo. Salida estructurada con Pydantic.")
    return modelos, clave


# ------------------------------------------------------------------- entradas
def encabezado() -> None:
    st.title("📄 Sistema de Evaluación de CVs con IA")
    st.markdown("**Analiza currículums y evalúa candidatos de manera objetiva usando IA**")
    st.markdown(
        "Este sistema utiliza inteligencia artificial para:\n"
        "- Extraer información clave de currículums en PDF\n"
        "- Analizar la experiencia y habilidades del candidato\n"
        "- Evaluar el ajuste al puesto específico\n"
        "- Proporcionar recomendaciones objetivas de contratación"
    )
    st.divider()


def mostrar_entradas():
    """Columna izquierda. Devuelve (archivo, descripción, se_pulsó_analizar)."""
    ronda = st.session_state.ronda
    st.header("📋 Datos de Entrada")
    archivo = st.file_uploader(
        "1. Sube el CV del candidato (PDF)", type=["pdf"], key=f"cv_{ronda}",
        help="El PDF debe tener texto seleccionable; los escaneados no se pueden leer.",
    )
    if archivo is not None:
        st.success(f"Archivo cargado: {archivo.name}", icon="✅")
        st.info(f"Tamaño: {archivo.size:,} bytes", icon="📊")
    st.divider()

    st.markdown("**2. Descripción del puesto de trabajo**")
    puesto = st.text_area(
        "Detalla los requisitos, responsabilidades y habilidades necesarias:",
        height=260, placeholder=EJEMPLO_PUESTO, key=f"puesto_{ronda}",
        help="Separa los requisitos obligatorios de los deseables: el análisis los pesa distinto.",
    )
    st.divider()

    boton_analizar, boton_limpiar = st.columns(2)
    analizar = boton_analizar.button("🔍 Analizar Candidato", type="primary", width="stretch")
    boton_limpiar.button("🗑️ Limpiar", width="stretch", on_click=limpiar_todo)
    return archivo, puesto, analizar


def procesar(archivo, puesto: str, modelos: list[str], clave: str | None) -> None:
    """Valida, lee el PDF, llama al modelo y guarda el resultado en session_state."""
    if archivo is None:
        st.error("Sube el CV del candidato en formato PDF.", icon="📄")
        return
    if not (puesto or "").strip():
        st.error("Escribe la descripción del puesto de trabajo.", icon="✍️")
        return
    try:
        with st.spinner("Leyendo el PDF..."):
            texto_cv = extraer_texto_pdf(archivo)
        _, _, recortado = validar_entradas(texto_cv, puesto)
        with st.spinner(f"Analizando el candidato con {modelos[0]}... puede tardar unos segundos"):
            analisis, usado, fallos = evaluar_con_respaldo(texto_cv, puesto, modelos, clave)
    except ErrorAnalizador as exc:
        st.error(str(exc), icon="⚠️")
        return
    st.session_state.resultado = {
        "analisis": analisis.model_dump(),
        "modelo": usado,
        "fallos": fallos,
        "archivo": archivo.name,
        "puesto": puesto.strip(),
        "texto_cv": texto_cv,
        "cv_recortado": recortado,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ------------------------------------------------------------------- resultado
def _lista_en_tarjeta(titulo: str, elementos: list[str]) -> None:
    with st.container(border=True):
        st.markdown(f"**{titulo}**")
        st.markdown("\n".join(f"- {_md(e)}" for e in elementos))


def mostrar_resultado(resultado: dict) -> None:
    a = resultado["analisis"]
    porcentaje = a["porcentaje_ajuste"]
    nivel = evaluacion_principal(porcentaje)
    recomendacion, explicacion = recomendacion_final(porcentaje)

    # 1. Evaluación principal
    st.subheader("🎯 Evaluación Principal")
    color = "normal" if porcentaje >= 60 else ("off" if porcentaje >= 40 else "inverse")
    st.metric(
        "Porcentaje de Ajuste al Puesto", f"{porcentaje}%",
        delta=f"{nivel.icono} {nivel.etiqueta.upper()}", delta_color=color,
    )
    st.progress(porcentaje / 100)
    st.markdown(f"**{recomendacion.icono} {recomendacion.etiqueta}**")
    st.divider()

    # 2. Perfil
    st.subheader("👤 Perfil del Candidato")
    izquierda, derecha = st.columns(2)
    años = a["experiencia_años"]
    izquierda.info(f"**Nombre:** {_md(a['nombre_candidato'])}", icon="🧑‍💼")
    izquierda.info(f"**Experiencia:** {años} {'año' if años == 1 else 'años'}", icon="⏱️")
    derecha.info(f"**Educación:** {_md(a['education'])}", icon="🎓")

    # 3. Experiencia relevante
    st.subheader("💼 Experiencia Relevante")
    st.info(f"**Resumen de experiencia:**\n\n{_md(a['experiencia_relevante'])}", icon="📋")
    st.divider()

    # 4. Habilidades
    st.subheader("🛠️ Habilidades Técnicas Clave")
    columnas = st.columns(3)  # con 4 columnas, palabras como «PostgreSQL» se partían
    for i, habilidad in enumerate(a["habilidades_clave"]):
        columnas[i % 3].success(_md(habilidad), icon="✅")
    st.divider()

    # 5. Fortalezas y áreas de mejora
    fortalezas, mejoras = st.columns(2)
    with fortalezas:
        st.subheader("💪 Fortalezas")
        _lista_en_tarjeta("Puntos a favor", a["fortalezas"])
    with mejoras:
        st.subheader("📈 Áreas de Desarrollo")
        _lista_en_tarjeta("Para mejorar", a["areas_mejora"])
    st.divider()

    # 6. Recomendación final
    st.subheader("📝 Recomendación Final")
    getattr(st, recomendacion.tono)(
        f"**{recomendacion.etiqueta}** ({porcentaje} %). {explicacion}", icon=recomendacion.icono
    )

    # 7. Trazabilidad: qué modelo respondió y si hubo respaldo
    if resultado.get("fallos"):
        detalle = "; ".join(f"{m}: {motivo}" for m, motivo in resultado["fallos"])
        st.warning(f"Respondió **{resultado['modelo']}** porque antes falló: {detalle}", icon="🔁")
    if resultado.get("cv_recortado"):
        st.caption("El CV era muy largo: se analizó solo la primera parte.")
    st.caption(f"Analizado con {resultado['modelo']} · {resultado['fecha']} · archivo: {resultado['archivo']}")

    # 8. Guardar: se descarga un JSON con el análisis y su contexto
    registro = {k: resultado[k] for k in ("fecha", "archivo", "modelo", "puesto", "analisis")}
    registro["evaluacion_principal"] = nivel.etiqueta
    registro["recomendacion_final"] = recomendacion.etiqueta
    nombre = a["nombre_candidato"].lower().replace(" ", "_")[:40] or "candidato"
    st.download_button(
        "💾 Guardar Análisis (JSON)",
        data=json.dumps(registro, ensure_ascii=False, indent=2),
        file_name=f"analisis_{nombre}.json", mime="application/json", width="stretch",
    )

    with st.expander("📏 ¿Cómo se calcula el porcentaje?"):
        st.markdown(
            "El modelo asigna el porcentaje siguiendo estos pesos:\n\n"
            "| Criterio | Peso |\n| --- | --- |\n"
            + "\n".join(f"| {nombre} | {peso} % |" for nombre, peso in CRITERIOS)
            + "\n\n**Evaluación principal:** 80-100 Excelente · 60-79 Bueno · 40-59 Regular · 0-39 Bajo"
            "\n\n**Recomendación final:** 70-100 recomendado · 50-69 con potencial · 0-49 no recomendado"
        )
    with st.expander("🔎 Texto extraído del PDF"):
        st.text(resultado.get("texto_cv", ""))


# ------------------------------------------------------------------ principal
def main() -> None:
    st.set_page_config(page_title="Sistema de Evaluación de CVs", page_icon="📄", layout="wide")
    iniciar_estado()
    with st.sidebar:
        modelos, clave = configurar_modelo()

    encabezado()
    col_entrada, col_resultado = st.columns(2, gap="large")
    with col_entrada:
        archivo, puesto, analizar = mostrar_entradas()
        if analizar:
            procesar(archivo, puesto, modelos, clave)
    with col_resultado:
        st.header("📊 Resultado del Análisis")
        if st.session_state.resultado:
            mostrar_resultado(st.session_state.resultado)
        else:
            st.info(INSTRUCCIONES, icon="👆")
