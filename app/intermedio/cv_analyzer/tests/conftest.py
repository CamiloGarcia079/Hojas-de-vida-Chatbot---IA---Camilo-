"""Configuración común de las pruebas. Ninguna prueba llama a Google ni a OpenAI."""
import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

CARPETA_APP = Path(__file__).resolve().parents[1]
if str(CARPETA_APP) not in sys.path:
    sys.path.insert(0, str(CARPETA_APP))

EJEMPLOS = CARPETA_APP / "ejemplos"


@pytest.fixture(autouse=True)
def sin_claves(monkeypatch):
    """Sin claves reales: así listar_modelos nunca sale a internet durante las pruebas."""
    for variable in ("GOOGLE_API_KEY", "OPENAI_API_KEY", "GEMINI_MODEL", "OPENAI_MODEL"):
        monkeypatch.delenv(variable, raising=False)


def analisis_valido(**cambios) -> dict:
    datos = {
        "nombre_candidato": "Laura Méndez Rojas",
        "experiencia_años": 3,
        "habilidades_clave": ["Java", "Spring Boot", "PostgreSQL", "Docker", "Git"],
        "education": "Tecnología en Análisis y Desarrollo de Software",
        "experiencia_relevante": "Tres años construyendo APIs REST con Spring Boot y PostgreSQL.",
        "fortalezas": ["APIs REST en producción", "Pruebas automatizadas", "Docker"],
        "areas_mejora": ["Inglés técnico", "Experiencia con Python"],
        "porcentaje_ajuste": 82,
    }
    datos.update(cambios)
    return datos


class ErrorServicio(Exception):
    """Imita un error HTTP del proveedor (trae status_code como los SDK reales)."""

    def __init__(self, mensaje, status_code):
        super().__init__(mensaje)
        self.status_code = status_code


class ModeloFalso:
    """Imita un chat model: sirve en `prompt | modelo` y en `modelo.with_structured_output(...)`."""

    def __init__(self, estructurada=None, texto=None, error_estructurada=None, error=None):
        self.estructurada = estructurada
        self.texto = texto
        self.error_estructurada = error_estructurada
        self.error = error
        self.llamadas = []

    def with_structured_output(self, esquema, **_):
        def responder(entrada):
            self.llamadas.append(("estructurada", entrada))
            if self.error:
                raise self.error
            if self.error_estructurada:
                raise self.error_estructurada
            return self.estructurada

        return RunnableLambda(responder)

    def __call__(self, entrada):  # camino del parser: prompt | modelo | parser
        self.llamadas.append(("texto", entrada))
        if self.error:
            raise self.error
        return AIMessage(content=self.texto)
