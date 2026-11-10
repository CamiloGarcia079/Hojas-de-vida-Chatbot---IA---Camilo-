"""Creación del modelo de lenguaje (Gemini u OpenAI) y lista de modelos disponibles.

Es la misma lógica que funcionó en Tribuna Global:
- la clave se lee del .env de la raíz del proyecto (o de la barra lateral);
- el modelo se elige desde la página, sin escribir el nombre a mano;
- sin reintentos ocultos y con tiempo máximo, para que la página no se quede cargando.
"""
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from models.errores import ErrorEvaluacion


# ---------------------------------------------------------------------- entorno
def cargar_entorno() -> None:
    """Carga el primer .env que encuentre subiendo desde esta carpeta (no pisa variables ya definidas).

    La guía del taller exportaba la clave a mano porque su app no llamaba a load_dotenv;
    aquí basta con el archivo .env de la raíz.
    """
    aqui = Path(__file__).resolve()
    for carpeta in aqui.parents:
        candidato = carpeta / ".env"
        if candidato.is_file():
            load_dotenv(candidato, override=False)
            return


cargar_entorno()

VARIABLE_CLAVE = {"google": "GOOGLE_API_KEY", "openai": "OPENAI_API_KEY"}
_RELLENOS = ("clave_configurada", "nombre_de_un_modelo", "tu_clave", "your_")

# Espera máxima por llamada. Un CV es más largo que una opinión, por eso es más que en Tribuna.
TIEMPO_MAXIMO = 40  # segundos
TEMPERATURA = 0.2  # la del taller: respuestas estables, con algo de redacción natural


def detectar_proveedor(nombre_modelo: str) -> str:
    """'google' si el modelo es un Gemini; en cualquier otro caso 'openai'."""
    return "google" if (nombre_modelo or "").strip().lower().startswith("gemini") else "openai"


def limpiar_clave(valor: str | None) -> str:
    """Quita espacios, comillas y caracteres invisibles que se cuelan al pegar una clave."""
    valor = (valor or "").strip().strip('"').strip("'")
    return "".join(c for c in valor if c.isprintable() and not c.isspace())


def valor_real(variable: str) -> str | None:
    """Valor de una variable de entorno; vacío o de relleno = None."""
    valor = limpiar_clave(os.getenv(variable))
    if not valor or valor.lower().startswith(_RELLENOS):
        return None
    return valor


def obtener_clave(proveedor: str) -> str | None:
    return valor_real(VARIABLE_CLAVE[proveedor])


def _admite_temperatura(nombre: str) -> bool:
    """Gemini 3.x y los modelos de razonamiento de OpenAI ignoran o rechazan temperature."""
    n = nombre.strip().lower()
    if n.startswith("gemini-3"):
        return False
    return not re.match(r"^(o\d|gpt-5)", n)


def crear_modelo(nombre_modelo: str, api_key: str | None = None):
    """Devuelve ChatGoogleGenerativeAI o ChatOpenAI listo para usar."""
    nombre = (nombre_modelo or "").strip()
    if not nombre:
        raise ErrorEvaluacion("Elige o escribe el nombre de un modelo en la barra lateral.")
    proveedor = detectar_proveedor(nombre)
    clave = limpiar_clave(api_key) or obtener_clave(proveedor)
    if not clave:
        raise ErrorEvaluacion(
            f"Falta la clave {VARIABLE_CLAVE[proveedor]}. Ponla en el archivo .env "
            "o escríbela en la barra lateral."
        )
    extra = {"temperature": TEMPERATURA} if _admite_temperatura(nombre) else {}
    if proveedor == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=nombre, google_api_key=clave, timeout=TIEMPO_MAXIMO, max_retries=0, **extra
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=nombre, api_key=clave, timeout=TIEMPO_MAXIMO, max_retries=0, **extra)


# ------------------------------------------------------------ lista de modelos
# Se usan si no se puede preguntar a Google qué modelos tiene la clave.
MODELOS_GEMINI_BASE = ["gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.8-flash"]
MODELOS_OPENAI = ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4o"]
_NO_SON_DE_TEXTO = ("embedding", "image", "tts", "audio", "live", "computer", "robotics", "veo", "imagen", "aqa")


def _orden_gemini(nombre: str):
    """Primero los estables y los «flash» (rápidos, con cuota gratis), los más nuevos arriba."""
    n = nombre.lower()
    version = re.match(r"gemini-(\d+)(?:\.(\d+))?", n)
    numero = float(f"{version.group(1)}.{version.group(2) or 0}") if version else 0.0
    return ("preview" in n or "exp" in n, "flash" not in n, "pro" in n, "latest" in n, -numero, "lite" in n, n)


def listar_modelos(proveedor: str, api_key: str | None = None) -> list[str]:
    """Modelos de texto que puede usar la clave. Si Google no responde, una lista fija."""
    if proveedor == "openai":
        return list(MODELOS_OPENAI)
    clave = limpiar_clave(api_key) or obtener_clave("google")
    if not clave:
        return list(MODELOS_GEMINI_BASE)
    try:
        from google import genai
        from google.genai import types

        cliente = genai.Client(api_key=clave, http_options=types.HttpOptions(timeout=10_000))
        nombres = [
            nombre
            for m in cliente.models.list()
            if (nombre := (m.name or "").removeprefix("models/")).startswith("gemini")
            and "generateContent" in (m.supported_actions or [])
            and not any(x in nombre for x in _NO_SON_DE_TEXTO)
        ]
    except Exception:
        return list(MODELOS_GEMINI_BASE)
    return sorted(set(nombres), key=_orden_gemini)[:15] or list(MODELOS_GEMINI_BASE)


def cadena_de_respaldo(elegido: str, disponibles: list[str], extras: int = 2) -> list[str]:
    """El modelo elegido y, detrás, hasta `extras` del mismo proveedor por si falla.

    Se prefieren los «lite» y los alias «latest»: suelen estar menos saturados.
    """
    proveedor = detectar_proveedor(elegido)
    otros = [
        m for m in disponibles
        if m != elegido and detectar_proveedor(m) == proveedor and "preview" not in m and "pro" not in m
    ]
    otros.sort(key=lambda m: ("lite" not in m, "latest" not in m))
    return [elegido, *otros[:extras]]


# --------------------------------------------------------- errores del servicio
def sanear(mensaje, limite: int = 300) -> str:
    """Recorta el mensaje de error y oculta cualquier cosa que parezca una clave."""
    mensaje = re.sub(r"(AIza|AQ\.|sk-)[A-Za-z0-9_\-\.]{8,}", "[clave oculta]", str(mensaje))
    mensaje = " ".join(mensaje.split())
    return mensaje if len(mensaje) <= limite else mensaje[:limite] + "…"


def _codigo(exc: Exception):
    return getattr(exc, "status_code", None) or getattr(exc, "code", None)


_PATRON_OTRO_MODELO = (
    r"\b(404|408|429|500|502|503|504)\b|unavailable|overload|high demand|resource.?exhausted|"
    r"quota|rate.?limit|deadline|time.?out|timed out|not.?found|no longer available"
)


def debe_probar_otro_modelo(exc: Exception) -> bool:
    """Saturado, sin cuota, inexistente o lento: otro modelo SÍ puede responder."""
    if _codigo(exc) in (404, 408, 429, 500, 502, 503, 504):
        return True
    return isinstance(exc, TimeoutError) or bool(re.search(_PATRON_OTRO_MODELO, str(exc), re.I))


def es_error_de_servicio(exc: Exception) -> bool:
    """Clave, permisos o disponibilidad: cambiar de método (parser) no lo arregla.

    Un 400 NO entra aquí: también puede ser que el proveedor rechace el esquema JSON,
    y en ese caso el camino con PydanticOutputParser sí puede funcionar.
    """
    if _codigo(exc) in (401, 403):
        return True
    return debe_probar_otro_modelo(exc) or bool(
        re.search(r"api[_ ]?key|unauthori|permission|connection|connect|proxy|network",
                  f"{type(exc).__name__} {exc}", re.I)
    )


def motivo_corto(exc: Exception) -> str:
    texto = f"{_codigo(exc) or ''} {exc}"
    if re.search(r"503|unavailable|overload|high demand", texto, re.I):
        return "saturado (503)"
    if re.search(r"429|quota|rate.?limit|exhausted", texto, re.I):
        return "sin cuota por ahora (429)"
    if re.search(r"404|not.?found|no longer available", texto, re.I):
        return "no disponible para esta clave (404)"
    if isinstance(exc, TimeoutError) or re.search(r"time.?out|deadline", texto, re.I):
        return f"tardó más de {TIEMPO_MAXIMO} s"
    return type(exc).__name__


def texto_de_respuesta(contenido) -> str:
    """Gemini 3.x devuelve una lista de bloques; OpenAI y Gemini 2.x, un str."""
    contenido = getattr(contenido, "content", contenido)
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        return "".join(
            b if isinstance(b, str) else b.get("text", "")
            for b in contenido
            if isinstance(b, str) or (isinstance(b, dict) and b.get("type") == "text")
        )
    return str(contenido)
