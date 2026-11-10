# LangChain + Streamlit — Analizador de CVs

Proyecto de la clase de Inteligencia Artificial 2 (CampusLands, bases de datos vectoriales y LangChain). Parte del entorno Docker que armó el profe Johlver Pardo y lo adapta para trabajar con Gemini u OpenAI. Encima de eso está el taller **Analizador de currículums con IA**: subes un CV en PDF, escribes el puesto y la app te dice qué tan bien encaja el candidato.

Autor: Camilo Andrés García Almeida.

## Qué hay aquí

- **Entorno de desarrollo.** Un Dev Container de VS Code con tres servicios: la app de Python, PostgreSQL y pgAdmin (`docker-compose.yml`, `Dockerfile`, `.devcontainer/`).
- **Ejemplos de clase** en `app/`: el hola mundo con OpenAI y con Gemini, y los chatbots de Streamlit.
- **Ejercicios de LangChain** en `app/intermedio/`, en el orden de la clase (tabla de abajo).
- **Taller Analizador de CVs** en `app/intermedio/cv_analyzer/`, organizado en capas. Tiene su propio README con todos los detalles.

```text
app/intermedio/cv_analyzer/
├── app.py            # punto de entrada
├── models/           # contrato Pydantic AnalisisCV y criterios
├── prompts/          # instrucciones y plantillas
├── services/         # PDF, modelo y evaluación
├── ui/               # interfaz de Streamlit
├── ejemplos/         # CV ficticios para probar
└── tests/            # pruebas automáticas
```

## Cómo correrlo

La forma recomendada es **sin Docker**: un script crea el entorno, instala lo necesario, pide la clave de Gemini si falta y abre la app. Funciona igual en el PC del campus (Linux, sin permisos de administrador) y en Windows.

**Linux**, desde la carpeta del proyecto:

```bash
bash iniciar.sh
```

**Windows**, desde la carpeta del proyecto en PowerShell (o doble clic en `iniciar.bat`):

```powershell
.\iniciar.bat
```

La primera vez tarda unos minutos instalando librerías. Si no hay `.env`, el script lo crea y te pide la `GOOGLE_API_KEY`: la pegas y queda guardada solo en tu PC. Después se abre http://localhost:8501. Para detenerla, `Ctrl + C`.

Para probar, sube `app/intermedio/cv_analyzer/ejemplos/cv_ejemplo_laura_mendez.pdf` y pega el contenido de `puesto_backend_junior.txt` de esa misma carpeta.

### Con el Dev Container (opcional)

Si Docker funciona en tu equipo: crea el `.env` en la raíz, abre la carpeta en VS Code y elige **Dev Containers: Reopen in Container**. En la terminal del contenedor:

```bash
cd /app/app/intermedio/cv_analyzer
python -m streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

O con Docker sin el Dev Container, como dice la guía del taller:

```bash
docker build -t cv-analyzer .
docker run --rm -p 8501:8501 --env-file .env \
  -w /app/app/intermedio/cv_analyzer \
  cv-analyzer \
  python -m streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

## Ejercicios de `app/intermedio/`

Cada archivo se corre solo con `python nombre.py` desde esa carpeta. Los que no usan modelo no necesitan clave.

| Archivo | Tema | ¿Usa modelo? |
| --- | --- | --- |
| `ejemplo_runnables.py` | `RunnableLambda`, `invoke`/`batch`, el operador `\|`, `RunnableParallel`, `RunnablePassthrough` | No |
| `prompt_templates.py` | `PromptTemplate` (plantilla de texto) | No |
| `chat_prompt_template.py` | `ChatPromptTemplate` con roles `system` y `human` | No |
| `rol_prompt_templates.py` | `SystemMessagePromptTemplate` y `HumanMessagePromptTemplate` | No |
| `message_placeholders.py` | `MessagesPlaceholder` para el historial (`--modelo` consulta al modelo real) | Opcional |
| `analisis_sentimientos_parte1.py` | Mini-proyecto: `RunnableLambda` y cadena `preprocesador \| process` | Sí |
| `analisis_sentimientos_parte2.py` | Mini-proyecto: `RunnableParallel` y `batch()` | Sí |
| `output_parsers_parte1.py` | `StrOutputParser` y `JsonOutputParser` | Sí |
| `output_parsers_parte2.py` | `PydanticOutputParser` y `with_structured_output` | Sí |
| `example_output_full.py` | Ejemplo completo de `PydanticOutputParser` en seis pasos | Sí |
| `streamlit_chatbot2.py` | Chatbot con historial como mensajes (`streamlit run streamlit_chatbot2.py`) | Sí |

`modelo_llm.py` solo crea el modelo: usa OpenAI si hay `OPENAI_API_KEY` real y, si no, Gemini con `GOOGLE_API_KEY`.

## Pruebas

```bash
cd app/intermedio/cv_analyzer
python -m pytest
```

Ninguna prueba gasta API: usan un modelo falso.

## Cosas a tener en cuenta

- Solo puede haber un entorno levantado a la vez: los nombres de los contenedores y los puertos se repiten.
- Si Docker da problemas (`docker.sock ... no such file`, `permission denied`), no hace falta: usa `bash iniciar.sh`.
- Los scripts de Linux van con `bash iniciar.sh`, no con `./iniciar.sh`: al pasar por Windows o GitHub el archivo puede perder el permiso de ejecución.
- Nunca subas claves. Si alguna se expone, bórrala y crea otra.
