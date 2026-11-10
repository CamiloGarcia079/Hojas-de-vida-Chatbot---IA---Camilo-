"""Plantillas de prompt (roles, MessagesPlaceholder, parser) y lectura del PDF."""
from io import BytesIO

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pypdf import PdfWriter

from conftest import EJEMPLOS
from models.cv_model import AnalisisCV
from models.errores import ErrorPDF
from prompts.cv_prompts import (
    _EJEMPLO_RESPUESTA,
    EJEMPLOS_CALIBRACION,
    crear_prompt_con_parser,
    crear_sistema_prompts,
)
from services.pdf_processor import extraer_texto_pdf

ENTRADA = {"descripcion_puesto": "Desarrollador Java con Spring Boot", "texto_cv": "Ana Pérez, 2 años en Java"}


# ---------------------------------------------------------------------- prompts
def test_plantilla_con_roles_sin_ejemplos():
    """optional=True: la plantilla funciona aunque no se pasen ejemplos."""
    mensajes = crear_sistema_prompts().format_messages(**ENTRADA)
    assert [type(m) for m in mensajes] == [SystemMessage, HumanMessage]
    assert "Experiencia relevante: 40 %" in mensajes[0].content
    assert "<cv>\nAna Pérez, 2 años en Java\n</cv>" in mensajes[1].content


def test_ejemplo_few_shot_va_entre_sistema_y_caso_real():
    mensajes = crear_sistema_prompts().format_messages(**ENTRADA, ejemplos=EJEMPLOS_CALIBRACION)
    assert [type(m) for m in mensajes] == [SystemMessage, HumanMessage, AIMessage, HumanMessage]
    assert "Carlos Ruiz" in mensajes[1].content and "Ana Pérez" in mensajes[3].content


def test_n_messages_limita_el_historial_a_dos():
    extra = [HumanMessage(content="viejo 1"), AIMessage(content="viejo 2")]
    mensajes = crear_sistema_prompts().format_messages(**ENTRADA, ejemplos=extra + EJEMPLOS_CALIBRACION)
    contenido = " ".join(m.content for m in mensajes)
    assert "viejo" not in contenido and len(mensajes) == 4


def test_el_ejemplo_resuelto_cumple_el_contrato():
    assert AnalisisCV.model_validate(_EJEMPLO_RESPUESTA).porcentaje_ajuste == 38


def test_prompt_con_parser_incluye_instrucciones_de_formato():
    parser = PydanticOutputParser(pydantic_object=AnalisisCV)
    mensajes = crear_prompt_con_parser(parser).format_messages(**ENTRADA)
    assert "porcentaje_ajuste" in mensajes[-1].content
    assert "JSON" in mensajes[-1].content


def test_las_llaves_del_cv_no_rompen_la_plantilla():
    """Un CV con { } (código, JSON) se trata como texto, no como variable."""
    entrada = {**ENTRADA, "texto_cv": 'Proyecto: {"api": "rest"} y {variable}'}
    mensajes = crear_sistema_prompts().format_messages(**entrada)
    assert '{"api": "rest"} y {variable}' in mensajes[-1].content


# -------------------------------------------------------------------------- PDF
def _pdf(paginas_en_blanco=1, clave=None) -> bytes:
    escritor = PdfWriter()
    for _ in range(paginas_en_blanco):
        escritor.add_blank_page(width=200, height=200)
    if clave is not None:
        escritor.encrypt(user_password=clave, owner_password="dueño")
    salida = BytesIO()
    escritor.write(salida)
    return salida.getvalue()


def test_extrae_texto_del_cv_de_ejemplo():
    texto = extraer_texto_pdf(EJEMPLOS / "cv_ejemplo_laura_mendez.pdf")
    assert texto.startswith("--- Página 1 ---")
    assert "Laura Méndez Rojas" in texto and "Spring Boot" in texto


def test_acepta_bytes_y_archivos_abiertos():
    datos = (EJEMPLOS / "cv_ejemplo_andres_cardenas.pdf").read_bytes()
    assert "Andrés Felipe Cárdenas" in extraer_texto_pdf(datos)
    assert "Andrés Felipe Cárdenas" in extraer_texto_pdf(BytesIO(datos))


@pytest.mark.parametrize("datos, mensaje", [
    (b"", "vacío"),
    (b"Hola, esto es un .txt renombrado", "no es un PDF"),
    (b"%PDF-1.4 basura sin estructura", "No se pudo leer"),
])
def test_archivos_invalidos(datos, mensaje):
    with pytest.raises(ErrorPDF, match=mensaje):
        extraer_texto_pdf(datos)


def test_pdf_sin_texto_como_un_escaneado():
    with pytest.raises(ErrorPDF, match="texto seleccionable"):
        extraer_texto_pdf(_pdf(paginas_en_blanco=2))


def test_pdf_con_contrasena():
    with pytest.raises(ErrorPDF, match="contraseña"):
        extraer_texto_pdf(_pdf(clave="secreta"))


def test_pdf_protegido_sin_contrasena_de_apertura_se_intenta_leer():
    """Contraseña de usuario vacía: se abre; como está en blanco, el aviso es de texto, no de clave."""
    with pytest.raises(ErrorPDF, match="texto seleccionable"):
        extraer_texto_pdf(_pdf(clave=""))


def test_archivo_demasiado_grande():
    with pytest.raises(ErrorPDF, match="10 MB"):
        extraer_texto_pdf(b"%PDF" + b"0" * (10 * 1024 * 1024 + 1))
