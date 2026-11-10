"""Creación del modelo, claves y lista de modelos (sin llamadas reales)."""
import pytest

from models.errores import ErrorEvaluacion
from services import modelo_llm


def test_limpiar_clave_quita_espacios_comillas_e_invisibles():
    assert modelo_llm.limpiar_clave('  "AQ.abc​123\x1b"  ') == "AQ.abc123"


@pytest.mark.parametrize("nombre, proveedor", [
    ("gemini-3.5-flash-lite", "google"), ("GEMINI-flash-latest", "google"), ("gpt-4o-mini", "openai"),
])
def test_detectar_proveedor(nombre, proveedor):
    assert modelo_llm.detectar_proveedor(nombre) == proveedor


def test_sin_clave_avisa_claramente():
    with pytest.raises(ErrorEvaluacion, match="GOOGLE_API_KEY"):
        modelo_llm.crear_modelo("gemini-3.5-flash-lite")


def test_valor_de_relleno_cuenta_como_sin_clave(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "tu_clave_de_gemini")
    assert modelo_llm.obtener_clave("google") is None


def test_gemini_3_sin_temperatura_y_sin_reintentos():
    modelo = modelo_llm.crear_modelo("gemini-3.5-flash-lite", api_key="clave-de-prueba")
    assert type(modelo).__name__ == "ChatGoogleGenerativeAI"
    assert modelo.max_retries == 0
    assert modelo_llm._admite_temperatura("gemini-3.5-flash-lite") is False


def test_openai_con_temperatura_del_taller():
    modelo = modelo_llm.crear_modelo("gpt-4o-mini", api_key="sk-prueba")
    assert type(modelo).__name__ == "ChatOpenAI"
    assert modelo.temperature == modelo_llm.TEMPERATURA == 0.2


def test_sin_clave_la_lista_de_gemini_es_la_fija():
    assert modelo_llm.listar_modelos("google") == modelo_llm.MODELOS_GEMINI_BASE
    assert modelo_llm.listar_modelos("openai") == modelo_llm.MODELOS_OPENAI


def test_orden_pone_primero_los_flash_estables():
    modelos = ["gemini-4-pro", "gemini-3.5-flash-lite", "gemini-4-argon-preview", "gemini-3.8-flash"]
    assert sorted(modelos, key=modelo_llm._orden_gemini)[0] == "gemini-3.8-flash"


def test_cadena_de_respaldo_prefiere_lite_y_mismo_proveedor():
    disponibles = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-flash-latest", "gpt-4o-mini"]
    assert modelo_llm.cadena_de_respaldo("gemini-3.8-flash", disponibles) == [
        "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-flash-latest",
    ]
