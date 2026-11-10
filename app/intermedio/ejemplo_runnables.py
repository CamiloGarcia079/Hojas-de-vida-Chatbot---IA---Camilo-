"""Runnables y el operador | (LCEL). No necesita modelo ni clave."""
from langchain_core.runnables import RunnableLambda

paso1 = RunnableLambda(lambda x: f"Numero {x}")


def duplicar_texto(texto):
    return [texto] * 2


paso2 = RunnableLambda(duplicar_texto)
# El operador | indica que la salida de paso1 se entrega como entrada a paso2.
cadena = paso1 | paso2

resultado = cadena.invoke(43)
print(resultado)  # ['Numero 43', 'Numero 43']

# --- invoke y batch sobre un Runnable --------------------------------------
def normalizar_texto(texto: str) -> str:
    return texto.strip().lower()


normalizador = RunnableLambda(normalizar_texto)
print(normalizador.invoke("  HOLA LANGCHAIN  "))  # hola langchain
print(normalizador.batch(["  JAVA ", " PYTHON  "]))  # ['java', 'python']

# --- Cadena de tres pasos ---------------------------------------------------
saludo = (
    RunnableLambda(lambda t: t.strip())
    | RunnableLambda(lambda t: t.upper())
    | RunnableLambda(lambda n: f"Hola, {n}. Bienvenido al curso.")
)
print(saludo.invoke("  Johlver  "))  # Hola, JOHLVER. Bienvenido al curso.

# --- RunnableParallel y RunnablePassthrough -------------------------------------
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

analizador = RunnableParallel(
    mayusculas=RunnableLambda(lambda t: t.upper()),
    caracteres=RunnableLambda(lambda t: len(t)),
    palabras=RunnableLambda(lambda t: len(t.split())),
)
print(analizador.invoke("Hola mundo"))  # {'mayusculas': 'HOLA MUNDO', 'caracteres': 10, 'palabras': 2}

conserva = RunnableParallel(
    original=RunnablePassthrough(),
    normalizado=RunnableLambda(lambda t: t.strip().lower()),
)
print(conserva.invoke("  JAVA  "))  # {'original': '  JAVA  ', 'normalizado': 'java'}

# Lo mismo, sin LangChain:
def convertir_a_texto(numero):
    return f"Numero {numero}"


print(duplicar_texto(convertir_a_texto(43)))
