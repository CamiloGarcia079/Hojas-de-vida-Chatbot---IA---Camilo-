"""Output parsers (parte 1): StrOutputParser y JsonOutputParser.

El modelo devuelve un AIMessage; el parser lo convierte en el tipo que necesitamos.
"""
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from modelo_llm import crear_llm

llm = crear_llm(temperature=0)

# 1) StrOutputParser: del mensaje del modelo a un str (ya no hace falta .content)
prompt = ChatPromptTemplate.from_messages([
    ("system", "Eres un docente de programación. Explica con un ejemplo breve."),
    ("human", "Explica el concepto de {tema}."),
])
cadena_texto = prompt | llm | StrOutputParser()

# 2) JsonOutputParser: del texto JSON del modelo a un dict de Python
parser_json = JsonOutputParser()
prompt_json = ChatPromptTemplate.from_messages([
    ("system", "Clasifica el sentimiento del comentario. {instrucciones}"),
    ("human", "Comentario: {texto}\nCampos: sentimiento (positivo|negativo|neutro) y razon."),
])
cadena_json = prompt_json.partial(instrucciones=parser_json.get_format_instructions()) | llm | parser_json

if __name__ == "__main__":
    print(cadena_texto.invoke({"tema": "polimorfismo"}))
    print("-" * 50)
    print(cadena_json.invoke({"texto": "La atención fue excelente"}))
