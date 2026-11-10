"""Configuración e invocación del modelo para evaluar un candidato.

Flujo de evaluar_candidato:
    validar entradas -> recortar CV largo -> chat_prompt | modelo.with_structured_output(AnalisisCV)
    si el proveedor no soporta bien el esquema -> chat_prompt | modelo | PydanticOutputParser
    -> objeto AnalisisCV validado

Diferencia con la versión de la guía: si algo falla NO se fabrica un AnalisisCV de
relleno (allí tenía los campos mal escritos y además ocultaba el error original).
Aquí se lanza ErrorEvaluacion con la causa, y la interfaz la muestra.
"""
import re

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from models.cv_model import AnalisisCV
from models.errores import ErrorEntrada, ErrorEvaluacion
from prompts.cv_prompts import EJEMPLOS_CALIBRACION, crear_prompt_con_parser, crear_sistema_prompts
from services import modelo_llm

MIN_CARACTERES_PUESTO = 30
# Un CV de 3-4 páginas tiene unos 10.000 caracteres. Por encima de este límite se
# recorta, para no mandar documentos enormes (costo y tiempo) al modelo.
MAX_CARACTERES_CV = 25_000
MAX_CARACTERES_PUESTO = 5_000


def validar_entradas(texto_cv: str, descripcion_puesto: str) -> tuple[str, str, bool]:
    """Limpia y valida. Devuelve (cv, puesto, se_recorto_el_cv)."""
    cv = (texto_cv or "").strip()
    puesto = (descripcion_puesto or "").strip()
    if not cv:
        raise ErrorEntrada("El CV no tiene texto para analizar.")
    if not puesto:
        raise ErrorEntrada("Escribe la descripción del puesto de trabajo.")
    if len(puesto) < MIN_CARACTERES_PUESTO:
        raise ErrorEntrada(
            f"La descripción del puesto es muy corta ({len(puesto)} caracteres). "
            "Incluye al menos el cargo y los requisitos principales."
        )
    if len(puesto) > MAX_CARACTERES_PUESTO:
        raise ErrorEntrada(
            f"La descripción del puesto es muy larga ({len(puesto)} caracteres; máximo {MAX_CARACTERES_PUESTO})."
        )
    recortado = len(cv) > MAX_CARACTERES_CV
    if recortado:
        cv = cv[:MAX_CARACTERES_CV] + "\n[... el resto del CV se omitió por longitud ...]"
    return cv, puesto, recortado


def crear_evaluador_cv(nombre_modelo: str, api_key: str | None = None):
    """Modelo con salida estructurada: devuelve directamente un AnalisisCV."""
    return modelo_llm.crear_modelo(nombre_modelo, api_key).with_structured_output(AnalisisCV)


def _con_salida_estructurada(entrada: dict, modelo) -> AnalisisCV:
    """Camino principal: el proveedor obliga a respetar el esquema de AnalisisCV."""
    cadena = crear_sistema_prompts() | modelo.with_structured_output(AnalisisCV)
    resultado = cadena.invoke(entrada)
    if resultado is None:
        raise ErrorEvaluacion("El modelo no devolvió una respuesta estructurada.")
    if isinstance(resultado, dict):
        resultado = AnalisisCV.model_validate(resultado)
    return resultado


def _con_output_parser(entrada: dict, modelo) -> AnalisisCV:
    """Camino alterno: PydanticOutputParser (las instrucciones de formato van en el prompt).

    RunnableLambda pasa la respuesta a texto plano, porque Gemini 3.x la entrega en bloques.
    """
    parser = PydanticOutputParser(pydantic_object=AnalisisCV)
    cadena = (
        crear_prompt_con_parser(parser)
        | modelo
        | RunnableLambda(modelo_llm.texto_de_respuesta)
        | parser
    )
    return cadena.invoke(entrada)


def evaluar_candidato(texto_cv: str, descripcion_puesto: str, modelo, metodo: str = "auto") -> AnalisisCV:
    """Evalúa UN candidato con UN modelo.

    metodo: "auto" (salida estructurada y, si el esquema da problemas, el parser),
            "estructurada" o "parser".
    Lanza ErrorEntrada o ErrorEvaluacion; nunca inventa un resultado.
    """
    cv, puesto, _ = validar_entradas(texto_cv, descripcion_puesto)
    entrada = {"texto_cv": cv, "descripcion_puesto": puesto, "ejemplos": EJEMPLOS_CALIBRACION}
    try:
        if metodo == "parser":
            return _con_output_parser(entrada, modelo)
        try:
            return _con_salida_estructurada(entrada, modelo)
        except Exception as exc:
            if metodo == "estructurada" or modelo_llm.es_error_de_servicio(exc):
                raise
            return _con_output_parser(entrada, modelo)
    except ErrorEvaluacion:
        raise
    except ValidationError as exc:
        raise ErrorEvaluacion(
            f"La respuesta del modelo no cumple el formato esperado: {modelo_llm.sanear(exc, 250)}"
        ) from exc
    except Exception as exc:  # red, cuota, clave, modelo inexistente...
        pista = ""
        if re.search(r"\b40[013]\b|api[_ ]?key|bad request|unauthori|permission", str(exc), re.I):
            pista = (" Revisa la clave: suele estar mal copiada (con espacios o caracteres ocultos), "
                     "vencida o borrada. Cópiala de nuevo en el archivo .env.")
        elif re.search(r"connection|connect|proxy|network", f"{type(exc).__name__} {exc}", re.I):
            pista = " Revisa la conexión a internet del equipo."
        raise ErrorEvaluacion(
            f"El modelo no pudo responder ({type(exc).__name__}): {modelo_llm.sanear(exc, 220)}{pista}"
        ) from exc


def evaluar_con_respaldo(texto_cv: str, descripcion_puesto: str, modelos: list[str], api_key: str | None = None):
    """Prueba los modelos en orden: si uno está saturado o no existe, pasa al siguiente.

    Devuelve (analisis, modelo_que_respondio, fallos) con fallos = [(modelo, motivo), ...].
    Un problema de clave, de entrada o de formato NO salta al siguiente: se muestra.
    Es la idea de `with_fallbacks` de LangChain, hecha a mano para saber qué modelo respondió.
    """
    validar_entradas(texto_cv, descripcion_puesto)  # entrada inválida: no se gasta ninguna llamada
    fallos = []
    for nombre in modelos:
        try:
            analisis = evaluar_candidato(texto_cv, descripcion_puesto, modelo_llm.crear_modelo(nombre, api_key))
            return analisis, nombre, fallos
        except ErrorEvaluacion as exc:
            causa = exc.__cause__ or exc
            if not modelo_llm.debe_probar_otro_modelo(causa):
                raise
            fallos.append((nombre, modelo_llm.motivo_corto(causa)))
    detalle = "; ".join(f"{m}: {motivo}" for m, motivo in fallos)
    raise ErrorEvaluacion(
        f"Ningún modelo respondió ({detalle}). Suele ser algo temporal del proveedor: "
        "espera un momento y vuelve a pulsar «Analizar Candidato», o elige otro modelo."
    )
