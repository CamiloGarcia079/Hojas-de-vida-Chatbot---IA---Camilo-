"""Extracción del texto de un CV en PDF.

Se usa pypdf, que es el nombre actual de PyPDF2 (el mismo proyecto, renombrado;
PyPDF2 ya no recibe actualizaciones). Si en el equipo solo está PyPDF2, también sirve.

No hay OCR: un PDF escaneado (solo imágenes) no tiene texto que extraer y se avisa.
"""
from io import BytesIO
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # equipo con la librería antigua
    from PyPDF2 import PdfReader

from models.errores import ErrorPDF

TAMANO_MAXIMO = 10 * 1024 * 1024  # 10 MB: un CV real pesa mucho menos
MIN_CARACTERES_TEXTO = 50  # menos que esto no alcanza para evaluar a nadie


def _leer_bytes(archivo) -> bytes:
    """Acepta lo que entrega st.file_uploader, bytes o una ruta."""
    if isinstance(archivo, (bytes, bytearray)):
        return bytes(archivo)
    if isinstance(archivo, (str, Path)):
        return Path(archivo).read_bytes()
    if hasattr(archivo, "getvalue"):
        return archivo.getvalue()
    if hasattr(archivo, "read"):
        return archivo.read()
    raise ErrorPDF("No se recibió un archivo válido.")


def extraer_texto_pdf(archivo) -> str:
    """Devuelve el texto de todas las páginas, separadas por '--- Página N ---'.

    Lanza ErrorPDF con un mensaje claro si el archivo no sirve.
    """
    datos = _leer_bytes(archivo)
    if not datos:
        raise ErrorPDF("El archivo está vacío.")
    if len(datos) > TAMANO_MAXIMO:
        raise ErrorPDF("El archivo pesa más de 10 MB. Sube el CV sin imágenes pesadas.")
    if not datos.lstrip()[:5].startswith(b"%PDF"):
        raise ErrorPDF("El archivo no es un PDF válido.")

    try:
        lector = PdfReader(BytesIO(datos))
        if lector.is_encrypted:
            # Muchos PDF vienen "protegidos" sin contraseña de apertura: se intenta abrir así.
            try:
                abierto = lector.decrypt("")
            except Exception:
                abierto = 0
            if not abierto:  # 0 = la contraseña vacía no sirvió
                raise ErrorPDF("El PDF está protegido con contraseña.")
        paginas, caracteres = [], 0
        for numero, pagina in enumerate(lector.pages, start=1):
            texto = (pagina.extract_text() or "").strip()
            if texto:
                caracteres += len(texto)
                paginas.append(f"--- Página {numero} ---\n{texto}")
    except ErrorPDF:
        raise
    except Exception as exc:  # PdfReadError, archivo truncado, etc.
        raise ErrorPDF(f"No se pudo leer el PDF ({type(exc).__name__}). Puede estar dañado.") from exc

    if caracteres < MIN_CARACTERES_TEXTO:
        raise ErrorPDF(
            "El PDF no tiene texto seleccionable (parece escaneado o es una imagen). "
            "Usa un CV exportado desde Word, Google Docs o similar."
        )
    return "\n\n".join(paginas)
