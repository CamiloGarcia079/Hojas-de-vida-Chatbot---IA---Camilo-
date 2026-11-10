"""Contrato de salida del análisis (modelo Pydantic AnalisisCV).

Las descripciones de cada Field no son decoración: LangChain las envía al modelo,
tanto con with_structured_output (como JSON Schema) como con PydanticOutputParser
(dentro de get_format_instructions). Por eso están redactadas como instrucciones.

Los nombres de los campos son los del taller (incluido `education`), para que el
resultado sea el mismo que espera la guía.
"""
from pydantic import BaseModel, Field, field_validator

# Cantidades que pide la guía. El modelo a veces entrega una de más: se recorta
# en vez de rechazar todo el análisis por un elemento extra.
MAX_HABILIDADES = 7
MAX_FORTALEZAS = 5
MAX_AREAS_MEJORA = 4


def _limpiar_lista(valores: list[str], maximo: int) -> list[str]:
    """Quita espacios, vacíos y repetidos (sin importar mayúsculas) y aplica el máximo."""
    limpios, vistos = [], set()
    for valor in valores:
        texto = " ".join(str(valor).split())
        if texto and texto.lower() not in vistos:
            vistos.add(texto.lower())
            limpios.append(texto)
    if not limpios:
        raise ValueError("la lista no puede quedar vacía")
    return limpios[:maximo]


class AnalisisCV(BaseModel):
    """Modelo de datos para el análisis completo de un CV."""

    nombre_candidato: str = Field(
        min_length=1,
        description="Nombre completo del candidato extraído del CV. Si no aparece, escribe 'No especificado'.",
    )
    experiencia_años: int = Field(
        ge=0,
        le=60,
        description="Años totales de experiencia laboral relevante para el puesto (número entero).",
    )
    habilidades_clave: list[str] = Field(
        description="Lista de las 5-7 habilidades del candidato más relevantes para el puesto."
    )
    education: str = Field(
        min_length=1, description="Nivel educativo más alto y especialización principal."
    )
    experiencia_relevante: str = Field(
        min_length=1,
        description="Resumen conciso de la experiencia más relevante para el puesto específico.",
    )
    fortalezas: list[str] = Field(
        description="3-5 principales fortalezas del candidato basadas en su perfil."
    )
    areas_mejora: list[str] = Field(
        description="2-4 áreas donde el candidato podría desarrollarse o mejorar para este puesto."
    )
    porcentaje_ajuste: int = Field(
        ge=0,
        le=100,
        description="Porcentaje de ajuste al puesto (0-100) basado en experiencia, habilidades y formación.",
    )

    @field_validator("nombre_candidato", "education", "experiencia_relevante")
    @classmethod
    def _texto_sin_espacios_sobrantes(cls, valor: str) -> str:
        valor = " ".join(valor.split())
        if not valor:
            raise ValueError("el texto no puede quedar vacío")
        return valor

    @field_validator("habilidades_clave")
    @classmethod
    def _habilidades(cls, valor: list[str]) -> list[str]:
        return _limpiar_lista(valor, MAX_HABILIDADES)

    @field_validator("fortalezas")
    @classmethod
    def _fortalezas(cls, valor: list[str]) -> list[str]:
        return _limpiar_lista(valor, MAX_FORTALEZAS)

    @field_validator("areas_mejora")
    @classmethod
    def _areas_mejora(cls, valor: list[str]) -> list[str]:
        return _limpiar_lista(valor, MAX_AREAS_MEJORA)
