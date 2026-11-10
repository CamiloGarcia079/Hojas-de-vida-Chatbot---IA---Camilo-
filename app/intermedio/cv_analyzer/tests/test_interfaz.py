"""Interfaz de Streamlit probada con AppTest (sin navegador y sin llamar al modelo)."""
from datetime import datetime

from streamlit.testing.v1 import AppTest

from conftest import CARPETA_APP, analisis_valido

APP = str(CARPETA_APP / "app.py")


def _abrir() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception
    return at


def _con_resultado(porcentaje=72, fallos=None) -> AppTest:
    at = _abrir()
    at.session_state["resultado"] = {
        "analisis": analisis_valido(porcentaje_ajuste=porcentaje),
        "modelo": "gemini-3.5-flash-lite",
        "fallos": fallos or [],
        "archivo": "cv_ejemplo_laura_mendez.pdf",
        "puesto": "Desarrollador Backend Junior",
        "texto_cv": "--- Página 1 ---\nLaura Méndez Rojas",
        "cv_recortado": False,
        "fecha": datetime.now().isoformat(timespec="seconds"),
    }
    at.run()
    assert not at.exception
    return at


def _boton(at, texto):
    return next(b for b in at.button if texto in b.label)


def test_pantalla_inicial():
    at = _abrir()
    assert at.title[0].value == "📄 Sistema de Evaluación de CVs con IA"
    assert [h.value for h in at.header if "Datos" in h.value or "Resultado" in h.value] == [
        "📋 Datos de Entrada", "📊 Resultado del Análisis",
    ]
    assert "Instrucciones" in at.info[0].value
    assert _boton(at, "Analizar Candidato") and _boton(at, "Limpiar")
    assert at.selectbox[0].label == "Modelo"


def test_analizar_sin_archivo_muestra_error():
    at = _abrir()
    _boton(at, "Analizar Candidato").click().run()
    assert any("Sube el CV" in e.value for e in at.error)
    assert at.session_state["resultado"] is None


def test_resultado_bueno_y_recomendado():
    at = _con_resultado(72)
    assert at.metric[0].value == "72%"
    assert "BUENO" in at.metric[0].delta
    assert any("Candidato recomendado" in s.value for s in at.success)
    assert any(s.value == "Spring Boot" for s in at.success)  # habilidades
    assert any("Laura Méndez Rojas" in i.value for i in at.info)
    assert any("3 años" in i.value for i in at.info)


def test_resultado_regular_y_no_recomendado():
    at = _con_resultado(45)
    assert "REGULAR" in at.metric[0].delta
    assert any("Candidato no recomendado" in e.value for e in at.error)


def test_se_avisa_cuando_respondio_un_modelo_de_respaldo():
    at = _con_resultado(80, fallos=[["gemini-3.8-flash", "tardó más de 40 s"]])
    assert any("porque antes falló" in w.value for w in at.warning)


def test_limpiar_borra_el_resultado():
    at = _con_resultado(72)
    ronda = at.session_state["ronda"]
    _boton(at, "Limpiar").click().run()
    assert at.session_state["resultado"] is None
    assert at.session_state["ronda"] == ronda + 1
    assert "Instrucciones" in at.info[0].value


def test_el_resultado_no_desaparece_al_interactuar():
    """En la guía el análisis se perdía con cualquier clic; aquí vive en session_state."""
    at = _con_resultado(72)
    at.checkbox[0].uncheck().run()
    assert at.metric[0].value == "72%"
