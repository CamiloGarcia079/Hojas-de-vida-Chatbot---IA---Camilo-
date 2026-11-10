"""Reglas de evaluación: pesos de los criterios y umbrales del porcentaje.

Están en un solo lugar para que el prompt (que le pide los pesos al modelo) y la
interfaz (que interpreta el porcentaje) usen siempre los mismos valores.

Importante: el porcentaje lo calcula el modelo siguiendo estos pesos; el código
no hace una suma ponderada porque no recibe puntajes por criterio.
"""
from typing import NamedTuple

# (criterio, peso en %). Suman 100.
CRITERIOS = (
    ("Experiencia relevante", 40),
    ("Habilidades técnicas", 35),
    ("Formación y certificaciones", 15),
    ("Coherencia profesional", 10),
)


class Nivel(NamedTuple):
    etiqueta: str
    icono: str
    tono: str  # "success" | "info" | "warning" | "error": cómo lo pinta la interfaz


# Evaluación principal: (mínimo, nivel). Se recorre de mayor a menor.
_EVALUACION = (
    (80, Nivel("Excelente", "🟢", "success")),
    (60, Nivel("Bueno", "🟡", "info")),
    (40, Nivel("Regular", "🟠", "warning")),
    (0, Nivel("Bajo", "🔴", "error")),
)

# Recomendación final: (mínimo, nivel, explicación).
_RECOMENDACION = (
    (70, Nivel("Candidato recomendado", "✅", "success"),
     "Su perfil cumple con los requisitos principales del puesto."),
    (50, Nivel("Candidato con potencial", "⚠️", "warning"),
     "Cumple parte de los requisitos; conviene una entrevista para revisar los vacíos."),
    (0, Nivel("Candidato no recomendado", "❌", "error"),
     "Su perfil está lejos de los requisitos principales de este puesto."),
)


def _validar(porcentaje: int) -> int:
    if not isinstance(porcentaje, int) or isinstance(porcentaje, bool) or not 0 <= porcentaje <= 100:
        raise ValueError(f"El porcentaje debe ser un entero entre 0 y 100 (llegó {porcentaje!r}).")
    return porcentaje


def evaluacion_principal(porcentaje: int) -> Nivel:
    """80-100 Excelente · 60-79 Bueno · 40-59 Regular · 0-39 Bajo."""
    porcentaje = _validar(porcentaje)
    return next(nivel for minimo, nivel in _EVALUACION if porcentaje >= minimo)


def recomendacion_final(porcentaje: int) -> tuple[Nivel, str]:
    """70-100 recomendado · 50-69 con potencial · 0-49 no recomendado. Devuelve (nivel, explicación)."""
    porcentaje = _validar(porcentaje)
    return next((nivel, texto) for minimo, nivel, texto in _RECOMENDACION if porcentaje >= minimo)


def criterios_como_texto() -> str:
    """Los pesos en formato de lista, para incluirlos en el prompt."""
    return "\n".join(f"- {nombre}: {peso} %" for nombre, peso in CRITERIOS)
