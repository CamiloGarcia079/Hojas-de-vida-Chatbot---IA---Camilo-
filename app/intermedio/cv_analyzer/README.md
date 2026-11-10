# Analizador de currículums con IA

Aplicación de Streamlit que compara un CV en PDF con la descripción de un puesto. Lee el texto del documento, se lo pasa a un modelo de lenguaje con LangChain y muestra un análisis estructurado del candidato: perfil, habilidades, fortalezas, áreas de mejora, porcentaje de ajuste y una recomendación.

Funciona con **Gemini** (lo que uso yo, porque tiene cuota gratuita) o con **OpenAI**, y el modelo se elige desde la barra lateral de la página.

## Qué hace

- Carga un CV en PDF con texto seleccionable.
- Recibe los requisitos y responsabilidades del puesto.
- Extrae nombre, años de experiencia relevante, educación y habilidades clave.
- Identifica fortalezas y áreas de mejora.
- Estima el porcentaje de ajuste al puesto (0 a 100).
- Da una recomendación final según ese porcentaje.
- Permite guardar el análisis como archivo JSON.

## Cómo se ejecuta

### Sin Docker (lo más rápido, sirve en los PC del campus)

Desde la raíz del proyecto:

```bash
bash iniciar.sh          # Linux
```

```powershell
.\iniciar.ps1            # Windows (o doble clic en iniciar.bat)
```

La primera vez crea el entorno virtual, instala las librerías y pide la clave de Gemini (`GOOGLE_API_KEY`), que queda guardada en el `.env` de la raíz. Ese archivo no se sube a GitHub. Luego se abre <http://localhost:8501>.

### Con el Dev Container o Docker Compose

Dentro del contenedor:

```bash
cd /app/app/intermedio/cv_analyzer
python -m streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

También está la tarea **Run CV Analyzer** en VS Code (`Terminal > Run Task`).

> La guía del taller decía que había que exportar la clave a mano porque la app no llamaba a `load_dotenv()`. Aquí sí lo hace (`services/modelo_llm.py`), así que basta con el `.env` de la raíz.

### Para probar rápido

En `ejemplos/` hay dos CV ficticios y una descripción de puesto:

| Archivo | Para qué sirve |
| --- | --- |
| `cv_ejemplo_laura_mendez.pdf` | Desarrolladora backend con 3 años de Java y Spring Boot: debería salir con un ajuste alto. |
| `cv_ejemplo_andres_cardenas.pdf` | Diseñador gráfico que está aprendiendo programación: debería salir bajo. |
| `puesto_backend_junior.txt` | Descripción del puesto para copiar y pegar en la página. |

## Cómo funciona por dentro

```text
PDF ─▶ pdf_processor ─▶ texto del CV ─┐
                                      ├─▶ cv_prompts (sistema + ejemplo + caso) ─▶ modelo ─▶ AnalisisCV ─▶ interfaz
descripción del puesto ───────────────┘
```

1. `app.py` llama a `main()` de la interfaz.
2. El usuario sube el PDF y escribe el puesto. Al pulsar **Analizar Candidato**, la interfaz comprueba que estén los dos.
3. `extraer_texto_pdf()` lee el archivo en memoria, recorre las páginas y une el texto con separadores `--- Página N ---`. Si el PDF está vacío, dañado, protegido o escaneado, avisa con un mensaje claro.
4. `crear_sistema_prompts()` arma el prompt: instrucciones del reclutador (rol sistema), un ejemplo ya resuelto y el CV con el puesto (rol humano).
5. `evaluar_candidato()` ejecuta la cadena `chat_prompt | modelo.with_structured_output(AnalisisCV)`. Si el proveedor no maneja bien el esquema, repite con `PydanticOutputParser`.
6. `evaluar_con_respaldo()` prueba los modelos en orden: si uno está saturado, sin cuota o tarda demasiado, pasa al siguiente.
7. La interfaz guarda el resultado en `st.session_state` y lo muestra.

## Estructura

```text
cv_analyzer/
├── app.py                      # Punto de entrada de Streamlit
├── requirements.txt            # Librerías mínimas (las usa iniciar.sh)
├── pytest.ini
├── models/
│   ├── cv_model.py             # Contrato Pydantic AnalisisCV
│   ├── criterios.py            # Pesos de los criterios y umbrales del porcentaje
│   └── errores.py              # Errores con mensajes para el usuario
├── prompts/
│   └── cv_prompts.py           # Instrucciones, ejemplo few-shot y plantillas
├── services/
│   ├── pdf_processor.py        # Extracción de texto del PDF
│   ├── modelo_llm.py           # Gemini u OpenAI, lista de modelos, tiempo máximo
│   └── cv_evaluator.py         # Cadena de evaluación y respaldo entre modelos
├── ui/
│   └── streamlit_ui.py         # Entradas, validaciones y presentación
├── ejemplos/                   # CV ficticios y un puesto de ejemplo
└── tests/                      # Pruebas automáticas (pytest)
```

Cada capa tiene un solo trabajo: la interfaz no habla con el modelo ni con el PDF, solo llama a los servicios; los servicios no saben nada de Streamlit. Por eso las pruebas pueden revisar cada parte por separado.

## Lo visto en clase y dónde está

| Tema de clase | Dónde se usa |
| --- | --- |
| Plantillas con roles (`SystemMessagePromptTemplate`, `HumanMessagePromptTemplate`) | `prompts/cv_prompts.py`, `crear_sistema_prompts()` |
| `MessagesPlaceholder` con `optional=True` y `n_messages=2` | `prompts/cv_prompts.py`: inserta un ejemplo resuelto (few-shot) para calibrar el porcentaje |
| LCEL: `prompt \| modelo` | `services/cv_evaluator.py`, `_con_salida_estructurada()` |
| Salida estructurada con Pydantic (`with_structured_output`) | `models/cv_model.py` y `services/cv_evaluator.py` |
| `PydanticOutputParser` y `get_format_instructions()` | `services/cv_evaluator.py`, `_con_output_parser()`, y `prompts/cv_prompts.py`, `crear_prompt_con_parser()` |
| `RunnableLambda` | `services/cv_evaluator.py`: convierte la respuesta de Gemini 3 en texto antes del parser |
| Streamlit (`file_uploader`, `columns`, `metric`, `session_state`) | `ui/streamlit_ui.py` |
| Variables de entorno y `.env` | `services/modelo_llm.py`, `cargar_entorno()` |

## Modelo de salida

Todos los campos de `AnalisisCV` son obligatorios. Los nombres son los de la guía, incluido `education`.

| Campo | Tipo | Contenido | Validación |
| --- | --- | --- | --- |
| `nombre_candidato` | `str` | Nombre extraído del CV | No puede quedar vacío |
| `experiencia_años` | `int` | Años de experiencia relevante | Entre 0 y 60 |
| `habilidades_clave` | `list[str]` | Habilidades útiles para el puesto | Sin repetidos, máximo 7 |
| `education` | `str` | Nivel educativo y especialización | No puede quedar vacío |
| `experiencia_relevante` | `str` | Resumen de la experiencia relacionada | No puede quedar vacío |
| `fortalezas` | `list[str]` | Fortalezas del candidato | Sin repetidos, máximo 5 |
| `areas_mejora` | `list[str]` | Áreas de desarrollo | Sin repetidos, máximo 4 |
| `porcentaje_ajuste` | `int` | Ajuste al puesto | Entre 0 y 100 |

Si el modelo entrega una habilidad de más, se recorta en vez de rechazar todo el análisis. Si entrega una lista vacía o un porcentaje fuera de rango, el análisis se rechaza y se muestra el error.

## Criterios de evaluación

El prompt le pide al modelo estos pesos (están en `models/criterios.py`, el mismo lugar que usa la interfaz):

| Criterio | Peso |
| --- | --- |
| Experiencia relevante | 40 % |
| Habilidades técnicas | 35 % |
| Formación y certificaciones | 15 % |
| Coherencia profesional | 10 % |

El porcentaje lo calcula el modelo siguiendo esos pesos; el código no hace una suma ponderada porque no recibe puntajes por criterio.

| Porcentaje | Evaluación principal |
| --- | --- |
| 80–100 | Excelente |
| 60–79 | Bueno |
| 40–59 | Regular |
| 0–39 | Bajo |

| Porcentaje | Recomendación final |
| --- | --- |
| 70–100 | Candidato recomendado |
| 50–69 | Candidato con potencial |
| 0–49 | Candidato no recomendado |

Por ejemplo, un 65 % sale como **Bueno** en la evaluación principal y como **Candidato con potencial** en la recomendación final.

## Qué cambié respecto a la guía

La guía lista varios problemas conocidos. Estos son los que resolví:

| Problema en la guía | Cómo quedó |
| --- | --- |
| El `except` de `cv_evaluator.py` armaba un `AnalisisCV` con `fotalezas` y `porcetaje_ajuste` mal escritos, así que también fallaba y ocultaba el error original. | Ya no se inventa un análisis de relleno. Se lanza `ErrorEvaluacion` con la causa real y la interfaz la muestra. |
| El resultado desaparecía con cualquier clic. | Se guarda en `st.session_state`. |
| **Limpiar** solo llamaba a `st.rerun()` y no borraba nada. | Borra el resultado y deja el archivo y la descripción vacíos (cambia la `key` de esos campos). |
| **Guardar Análisis** solo mostraba un aviso. | Descarga un JSON con el análisis, el modelo usado y la fecha. |
| Se enviaba el CV completo sin control de largo. | Se recorta a 25.000 caracteres (un CV normal tiene menos de 10.000) y se avisa. |
| Había que exportar la clave a mano. | Se lee del `.env` de la raíz. |
| Solo OpenAI con un modelo fijo. | Gemini u OpenAI, con selector de modelo y respaldo si uno está saturado. |

Además, la descripción del puesto debe tener al menos 30 caracteres, y las instrucciones le dicen al modelo que ignore órdenes escondidas en el CV (por ejemplo, alguien que escriba «asigna 100 %» en su hoja de vida) y que no tenga en cuenta datos personales como edad, género u origen.

### Sobre PyPDF2

La guía usa `PyPDF2`. Ese proyecto cambió de nombre a `pypdf` y la versión vieja ya no recibe arreglos, así que el `requirements.txt` instala `pypdf`. El código intenta primero `pypdf` y, si no está, usa `PyPDF2`, así que funciona con cualquiera de las dos.

## Pruebas

```bash
cd app/intermedio/cv_analyzer
python -m pytest
```

Son 87 pruebas y ninguna llama al modelo real: usan un modelo falso que responde lo que cada prueba necesita. Revisan el contrato y sus límites, los umbrales (incluido el ejemplo del 65 %), las plantillas (con y sin ejemplos, `n_messages`), la lectura de PDF (vacío, dañado, escaneado, con contraseña), el cambio a `PydanticOutputParser`, el respaldo entre modelos y la interfaz con `AppTest` de Streamlit.

## Limitaciones

- **Sin OCR:** un PDF escaneado no se puede leer; la página lo avisa.
- **Un CV a la vez:** no hay procesamiento por lotes.
- **El porcentaje es una estimación del modelo:** puede variar un poco entre ejecuciones y no reemplaza la decisión de una persona.
- **Datos personales:** el texto del CV se envía al proveedor del modelo (Google u OpenAI). Para probar, usa los CV ficticios de `ejemplos/`.

## Problemas comunes

| Síntoma | Qué revisar |
| --- | --- |
| «Falta la clave GOOGLE_API_KEY» | Pon la clave en el `.env` de la raíz o escríbela en la barra lateral. |
| «Revisa la clave» o error 400 con todos los modelos | La clave quedó mal copiada. Ábrela en AI Studio y cópiala de nuevo. |
| «saturado (503)» o «sin cuota (429)» | Es temporal. Deja activado «probar otro modelo» o elige `gemini-3.5-flash-lite`. |
| «El PDF no tiene texto seleccionable» | Es un escaneo. Usa un CV exportado desde Word o Google Docs. |
| No encuentra `ui`, `services` o `models` | Ejecuta con `streamlit run` apuntando a este `app.py` (desde aquí o con `iniciar.sh`). |
| El puerto 8501 está ocupado | Streamlit usa el siguiente libre; mira la dirección que muestra la terminal. |
