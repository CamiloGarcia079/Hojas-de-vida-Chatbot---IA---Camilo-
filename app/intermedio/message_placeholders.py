"""MessagesPlaceholder: el historial entra como MENSAJES con rol, no como texto.

Sin modelo: solo muestra cómo queda el prompt. Con modelo (opcional, al final):
la cadena prompt | modelo responde teniendo en cuenta el historial.
"""
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

prompt = ChatPromptTemplate.from_messages([
    ("system", "El asistente se llama ChatBot Pro y es útil y amigable. Responde de forma breve."),
    MessagesPlaceholder(variable_name="historial"),
    ("human", "{mensaje}"),
])

historial = [
    HumanMessage(content="Hola, me llamo Camilo."),
    AIMessage(content="¡Hola, Camilo! ¿En qué te ayudo?"),
]

mensajes = prompt.format_messages(historial=historial, mensaje="¿Cómo me llamo?")
for m in mensajes:
    print(f"{m.type}: {m.content}")

# ChatPromptTemplate NO guarda la memoria por sí mismo: el historial hay que pasárselo.
if __name__ == "__main__":
    import sys

    if "--modelo" in sys.argv:
        from modelo_llm import crear_llm, texto

        cadena = prompt | crear_llm(temperature=0.5)
        print("\nRespuesta del modelo:", texto(cadena.invoke({"historial": historial, "mensaje": "¿Cómo me llamo?"})))
    else:
        print("\n(Añade --modelo para consultar al modelo real.)")
