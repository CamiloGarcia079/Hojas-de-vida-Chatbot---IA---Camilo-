"""ChatPromptTemplate: una plantilla de MENSAJES con roles (system / human)."""
from langchain_core.prompts import ChatPromptTemplate

chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "Eres un traductor del español al inglés muy preciso."),
    ("human", "{texto}"),
])

mensajes = chat_prompt.format_messages(texto="Hola mundo, ¿cómo estás?")

for m in mensajes:
    print(f"{type(m)}: {m.content}")

# invoke() devuelve un ChatPromptValue; todavía no consulta al modelo.
valor = chat_prompt.invoke({"texto": "Buenos días"})
for m in valor.to_messages():
    print(f"{m.type}: {m.content}")
