"""Evaluación del candidato: salida estructurada, parser alterno, errores y respaldo de modelos."""
import json

import pytest

from conftest import ErrorServicio, ModeloFalso, analisis_valido
from models.cv_model import AnalisisCV
from models.errores import ErrorEntrada, ErrorEvaluacion
from services import cv_evaluator, modelo_llm
from services.cv_evaluator import evaluar_candidato, evaluar_con_respaldo, validar_entradas

CV = "Laura Méndez. 3 años con Java, Spring Boot y PostgreSQL. Docker y Git."
PUESTO = "Desarrollador Backend Junior: Java con Spring Boot, PostgreSQL y Git."


# ------------------------------------------------------------------- entradas
@pytest.mark.parametrize("cv, puesto, mensaje", [
    ("", PUESTO, "no tiene texto"),
    (CV, "   ", "descripción del puesto"),
    (CV, "Backend", "muy corta"),
    (CV, "x" * 5001, "muy larga"),
])
def test_entradas_invalidas(cv, puesto, mensaje):
    with pytest.raises(ErrorEntrada, match=mensaje):
        validar_entradas(cv, puesto)


def test_cv_muy_largo_se_recorta():
    cv, _, recortado = validar_entradas("a" * 30_000, PUESTO)
    assert recortado and len(cv) < 30_000 and cv.endswith("por longitud ...]")


# ---------------------------------------------------------- camino estructurado
def test_salida_estructurada_devuelve_analisis():
    modelo = ModeloFalso(estructurada=AnalisisCV(**analisis_valido()))
    resultado = evaluar_candidato(CV, PUESTO, modelo)
    assert isinstance(resultado, AnalisisCV) and resultado.porcentaje_ajuste == 82
    tipo, prompt = modelo.llamadas[0]
    textos = [m.content for m in prompt.to_messages()]
    assert tipo == "estructurada" and len(textos) == 4  # sistema + ejemplo (2) + caso real
    assert CV in textos[-1]


def test_si_el_proveedor_devuelve_dict_se_valida():
    modelo = ModeloFalso(estructurada=analisis_valido(porcentaje_ajuste=55))
    assert evaluar_candidato(CV, PUESTO, modelo).porcentaje_ajuste == 55


def test_dict_invalido_no_se_acepta():
    modelo = ModeloFalso(estructurada=analisis_valido(porcentaje_ajuste=180), texto="no es json")
    with pytest.raises(ErrorEvaluacion):
        evaluar_candidato(CV, PUESTO, modelo)


# ------------------------------------------------------------- parser alterno
def test_si_el_esquema_falla_usa_pydantic_output_parser():
    """Ej.: el proveedor rechaza el JSON Schema (400). El parser sí funciona."""
    modelo = ModeloFalso(
        error_estructurada=ErrorServicio("400 Invalid JSON schema", 400),
        texto=json.dumps(analisis_valido(porcentaje_ajuste=64), ensure_ascii=False),
    )
    resultado = evaluar_candidato(CV, PUESTO, modelo)
    assert resultado.porcentaje_ajuste == 64
    assert [tipo for tipo, _ in modelo.llamadas] == ["estructurada", "texto"]


def test_parser_entiende_bloques_de_gemini_3_y_markdown():
    contenido = "```json\n" + json.dumps(analisis_valido(), ensure_ascii=False) + "\n```"
    modelo = ModeloFalso(texto=[{"type": "text", "text": contenido}])
    assert evaluar_candidato(CV, PUESTO, modelo, metodo="parser").nombre_candidato == "Laura Méndez Rojas"


def test_parser_con_respuesta_que_no_es_json():
    modelo = ModeloFalso(texto="Lo siento, no puedo ayudar con eso.")
    with pytest.raises(ErrorEvaluacion):
        evaluar_candidato(CV, PUESTO, modelo, metodo="parser")


def test_error_de_servicio_no_cambia_de_metodo():
    """Si Google está saturado, el parser tampoco ayudaría: no se gasta otra llamada."""
    modelo = ModeloFalso(error=ErrorServicio("503 UNAVAILABLE high demand", 503))
    with pytest.raises(ErrorEvaluacion, match="no pudo responder"):
        evaluar_candidato(CV, PUESTO, modelo)
    assert len(modelo.llamadas) == 1


def test_clave_invalida_da_una_pista():
    modelo = ModeloFalso(error=ErrorServicio("400 API key not valid", 400))
    with pytest.raises(ErrorEvaluacion, match="Revisa la clave"):
        evaluar_candidato(CV, PUESTO, modelo)


def test_un_error_nunca_se_convierte_en_un_analisis_inventado():
    """En la guía, el except fabricaba un AnalisisCV de relleno. Aquí se informa el error."""
    modelo = ModeloFalso(error=RuntimeError("fallo inesperado"))
    with pytest.raises(ErrorEvaluacion):
        evaluar_candidato(CV, PUESTO, modelo, metodo="estructurada")


def test_el_mensaje_de_error_oculta_la_clave():
    modelo = ModeloFalso(error=ErrorServicio("401 bad key AIzaSyA1234567890abcdefXYZ", 401))
    with pytest.raises(ErrorEvaluacion) as info:
        evaluar_candidato(CV, PUESTO, modelo)
    assert "AIzaSy" not in str(info.value) and "[clave oculta]" in str(info.value)


# ------------------------------------------------------------ respaldo de modelos
def _modelos(monkeypatch, por_nombre: dict):
    creados = []

    def crear(nombre, api_key=None):
        creados.append(nombre)
        return por_nombre[nombre]

    monkeypatch.setattr(modelo_llm, "crear_modelo", crear)
    return creados


def test_respaldo_pasa_al_siguiente_si_esta_saturado(monkeypatch):
    creados = _modelos(monkeypatch, {
        "gemini-a": ModeloFalso(error=ErrorServicio("503 UNAVAILABLE", 503)),
        "gemini-b": ModeloFalso(estructurada=AnalisisCV(**analisis_valido())),
    })
    analisis, usado, fallos = evaluar_con_respaldo(CV, PUESTO, ["gemini-a", "gemini-b"])
    assert usado == "gemini-b" and creados == ["gemini-a", "gemini-b"]
    assert fallos == [("gemini-a", "saturado (503)")]
    assert analisis.porcentaje_ajuste == 82


def test_respaldo_todos_fallan(monkeypatch):
    _modelos(monkeypatch, {
        "gemini-a": ModeloFalso(error=ErrorServicio("429 RESOURCE_EXHAUSTED", 429)),
        "gemini-b": ModeloFalso(error=TimeoutError("timed out")),
    })
    with pytest.raises(ErrorEvaluacion, match="Ningún modelo respondió") as info:
        evaluar_con_respaldo(CV, PUESTO, ["gemini-a", "gemini-b"])
    assert "sin cuota" in str(info.value) and "tardó más" in str(info.value)


def test_respaldo_se_detiene_con_error_de_clave(monkeypatch):
    creados = _modelos(monkeypatch, {
        "gemini-a": ModeloFalso(error=ErrorServicio("403 PERMISSION_DENIED", 403)),
        "gemini-b": ModeloFalso(estructurada=AnalisisCV(**analisis_valido())),
    })
    with pytest.raises(ErrorEvaluacion):
        evaluar_con_respaldo(CV, PUESTO, ["gemini-a", "gemini-b"])
    assert creados == ["gemini-a"]


def test_entrada_invalida_no_gasta_llamadas(monkeypatch):
    creados = _modelos(monkeypatch, {})
    with pytest.raises(ErrorEntrada):
        evaluar_con_respaldo(CV, "corta", ["gemini-a"])
    assert creados == []


def test_crear_evaluador_cv_usa_salida_estructurada(monkeypatch):
    modelo = ModeloFalso(estructurada=AnalisisCV(**analisis_valido()))
    _modelos(monkeypatch, {"gpt-4o-mini": modelo})
    evaluador = cv_evaluator.crear_evaluador_cv("gpt-4o-mini")
    assert evaluador.invoke("hola").nombre_candidato == "Laura Méndez Rojas"


def test_sin_internet_no_reintenta_con_el_parser():
    class ErrorDeConexion(Exception):
        pass

    modelo = ModeloFalso(error=ErrorDeConexion("Connection error."))
    with pytest.raises(ErrorEvaluacion, match="conexión a internet"):
        evaluar_candidato(CV, PUESTO, modelo)
    assert len(modelo.llamadas) == 1
