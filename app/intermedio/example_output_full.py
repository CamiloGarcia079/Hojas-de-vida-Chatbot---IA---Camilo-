"""Output Parsers: ejemplo completo con PydanticOutputParser (archivo teórico, sección «Output Parsers»).

Los seis pasos de la guía: modelo de datos -> parser -> prompt -> LLM -> cadena -> ejecución.
La diferencia con la guía es el LLM: crear_llm() usa Gemini u OpenAI según la clave del .env.

Uso (desde app/intermedio):
    python example_output_full.py
"""
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field

from modelo_llm import crear_llm, texto


# 1. Modelo de datos: las descripciones se convierten en instrucciones para el modelo
class AnalisisTexto(BaseModel):
    resumen: str = Field(description="Resumen breve del texto")
    sentimiento: str = Field(description="Sentimiento: Positivo, Neutro o Negativo")
    palabras_clave: list[str] = Field(description="3-5 palabras clave principales")


# 2. Parser
parser = PydanticOutputParser(pydantic_object=AnalisisTexto)

# 3. Prompt: {format_instructions} se llena una sola vez con partial_variables
prompt = PromptTemplate(
    template="""Analiza este texto cuidadosamente y proporciona un análisis estructurado:

{format_instructions}

TEXTO:
{texto}

ANÁLISIS:""",
    input_variables=["texto"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

# 4. LLM (temperatura baja: respuestas más consistentes)
llm = crear_llm(temperature=0.2)

# 5. Cadena: prompt -> LLM -> texto plano -> parser
#    RunnableLambda(texto) hace falta porque Gemini 3.x responde en bloques, no en un str.
chain = prompt | llm | RunnableLambda(texto) | parser

# 6. Ejecución
if __name__ == "__main__":
    print("Instrucciones que el parser agrega al prompt:\n")
    print(parser.get_format_instructions()[:400], "...\n")

    entrada = "Me encantó la nueva película de acción, tiene efectos especiales increíbles."
    try:
        resultado = chain.invoke({"texto": entrada})
        print("✅ Análisis exitoso:")
        print(resultado.model_dump_json(indent=2))
        print(f"\nTipo de objeto: {type(resultado).__name__}")
    except Exception as e:
        print(f"❌ Error: {e}")
