"""PromptTemplate: una plantilla de TEXTO con variables. No consulta al modelo."""
from langchain_core.prompts import PromptTemplate

template = "Eres un experto en marketing. Sugiere un eslogan creativo para un producto {producto}"

prompt = PromptTemplate(
    template=template,
    input_variables=["producto"],
)

prompt_lleno = prompt.format(producto="café orgánico")
print(prompt_lleno)

# Otra forma: from_template detecta solo las variables.
plantilla = PromptTemplate.from_template(
    """La tarea consiste en clasificar el sentimiento.
La respuesta debe contener únicamente:
positivo, negativo o neutro.

Comentario: {texto}"""
)
print(plantilla.format(texto="La atención fue excelente"))
