"""Mini-proyecto (parte 2): ramas en paralelo con RunnableParallel y batch().

                         ┌─> resumen ─────┐
texto -> preprocesador ──┤                ├─> merger -> resultado
                         └─> sentimiento ─┘
"""
import json

from langchain_core.runnables import RunnableLambda, RunnableParallel

from modelo_llm import crear_llm, texto

# Configuración del modelo
llm = crear_llm(temperature=0)


# Preprocesador: limpia espacios y limita a 500 caracteres
def preprocess_text(text):
    """Limpia el texto eliminando espacios extras y limitando longitud"""
    return text.strip()[:500]


preprocessor = RunnableLambda(preprocess_text)


# Generación de resumen
def generate_summary(text):
    """Genera un resumen conciso del texto"""
    prompt = f"Resume en una sola oración: {text}"
    return texto(llm.invoke(prompt))


summary_brach = RunnableLambda(generate_summary)


# Análisis de sentimiento con formato JSON
def analyze_sentiment(text):
    prompt = f"""Analiza el sentimiento del siguiente texto.
    Responde ÚNICAMENTE en formato JSON válido:
    {{"sentimiento": "positivo|negativo|neutro", "razon": "justificación breve"}}

    Texto: {text}"""

    response = texto(llm.invoke(prompt)).strip()
    response = response.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"sentimiento": "neutro", "razon": "Error en análisis"}


sentiment_branch = RunnableLambda(analyze_sentiment)


# Combinación de resultados
def merge_results(data):
    """Combina los resultados de ambas ramas en un formato unificado"""
    return {
        "resumen": data["resumen"],
        "sentimiento": data["sentimiento_data"]["sentimiento"],
        "razon": data["sentimiento_data"]["razon"],
    }


merger = RunnableLambda(merge_results)

# Las dos ramas reciben el MISMO texto y se ejecutan en paralelo
parallel_analysis = RunnableParallel({
    "resumen": summary_brach,
    "sentimiento_data": sentiment_branch,
})

# Cadena completa
chain = preprocessor | parallel_analysis | merger

if __name__ == "__main__":
    reviews_batch = [
        "Excelente producto, muy satisfecho con la compra",
        "Terrible calidad, no lo recomiendo para nada",
        "Está bien, cumple su función básica pero nada especial",
    ]
    # batch(): varias entradas al mismo Runnable
    print(chain.batch(reviews_batch))
