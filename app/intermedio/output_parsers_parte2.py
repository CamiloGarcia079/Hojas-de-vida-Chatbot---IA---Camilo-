"""Output parsers (parte 2): salida ESTRUCTURADA con Pydantic.

Es lo que usa el Analizador de CVs (cv_analyzer): el modelo devuelve directamente un objeto validado.
Dos caminos:
  A) PydanticOutputParser: se piden las instrucciones de formato en el prompt y se parsea el texto.
  B) with_structured_output(Modelo): el proveedor obliga al esquema (el recomendado).
"""
from typing import Literal

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from modelo_llm import crear_llm


class Sentimiento(BaseModel):
    sentimiento: Literal["positivo", "negativo", "neutro", "mixto"] = Field(
        description="Categoría del comentario"
    )
    razon: str = Field(min_length=1, max_length=300, description="Justificación breve")


llm = crear_llm(temperature=0)

# A) PydanticOutputParser
parser = PydanticOutputParser(pydantic_object=Sentimiento)
prompt_a = ChatPromptTemplate.from_messages([
    ("system", "Clasifica el sentimiento del comentario.\n{formato}"),
    ("human", "{texto}"),
]).partial(formato=parser.get_format_instructions())
cadena_a = prompt_a | llm | parser

# B) with_structured_output (como en cv_analyzer)
prompt_b = ChatPromptTemplate.from_messages([
    ("system", "Clasifica el sentimiento del comentario."),
    ("human", "{texto}"),
])
cadena_b = prompt_b | llm.with_structured_output(Sentimiento)

if __name__ == "__main__":
    comentario = "Tiene gran técnica, pero su actitud me decepciona"
    resultado_a = cadena_a.invoke({"texto": comentario})
    print("A:", type(resultado_a).__name__, resultado_a)
    resultado_b = cadena_b.invoke({"texto": comentario})
    print("B:", type(resultado_b).__name__, resultado_b)
    print("Se usa como objeto:", resultado_b.sentimiento)  # no como response.content
