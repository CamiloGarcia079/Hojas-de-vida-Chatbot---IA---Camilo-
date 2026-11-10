"""Mini-proyecto (parte 1): análisis de sentimientos con RunnableLambda.

texto -> preprocesamiento -> process (resumen + sentimiento) -> resultado
"""
import json

from langchain_core.runnables import RunnableLambda

from modelo_llm import crear_llm, texto

# Configuración del modelo (temperature=0: respuestas lo más consistentes posible)
llm = crear_llm(temperature=0)


def preprocess_text(text):
    """Limpia el texto eliminando espacios extras y limitando longitud."""
    return text.strip()[:500]


preprocessor = RunnableLambda(preprocess_text)


def generate_summary(text):
    """Genera un resumen conciso del texto."""
    prompt = f"Resume en una sola oración: {text}"
    return texto(llm.invoke(prompt))


def analyze_sentiment(text):
    """Analiza el sentimiento y devuelve un diccionario."""
    prompt = f"""Analiza el sentimiento del siguiente texto.
Responde ÚNICAMENTE en formato JSON válido:
{{"sentimiento": "positivo|negativo|neutro", "razon": "justificación breve"}}

Texto: {text}"""
    respuesta = texto(llm.invoke(prompt)).strip()
    # Algunos modelos envuelven el JSON en ```json ... ```
    respuesta = respuesta.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(respuesta)
    except json.JSONDecodeError:
        # OJO: en la app real esto NO se disfraza de "neutro" (ver cv_analyzer/services/cv_evaluator.py).
        return {"sentimiento": "neutro", "razon": "Error en análisis"}


def merge_results(data):
    """Combina los resultados de ambas ramas en un formato unificado."""
    return {
        "resumen": data["resumen"],
        "sentimiento": data["sentimiento_data"]["sentimiento"],
        "razon": data["sentimiento_data"]["razon"],
    }


def process_one(t):
    resumen = generate_summary(t)  # Llamada 1 al LLM
    sentimiento_data = analyze_sentiment(t)  # Llamada 2 al LLM
    return merge_results({"resumen": resumen, "sentimiento_data": sentimiento_data})


process = RunnableLambda(process_one)

# La cadena completa
chain = preprocessor | process

if __name__ == "__main__":
    textos_prueba = [
        "¡Me encanta este producto! Funciona perfectamente y llegó muy rápido.",
        "El servicio al cliente fue terrible, nadie me ayudó con mi problema.",
        "El clima está nublado hoy, probablemente llueva más tarde.",
    ]
    for t in textos_prueba:
        print(f"Texto: {t}")
        print(f"Resultado: {chain.invoke(t)}")
        print("-" * 50)
