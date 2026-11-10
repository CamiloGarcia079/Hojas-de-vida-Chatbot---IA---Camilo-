"""Punto de entrada del Analizador de CVs.

Ejecución (desde esta carpeta):
    python -m streamlit run app.py --server.port=8501

Streamlit agrega la carpeta de este archivo a la ruta de Python, por eso funcionan
los imports de las capas (ui, services, models, prompts) aunque se ejecute desde
la raíz del proyecto, como hace iniciar.sh.
"""
from ui.streamlit_ui import main

main()
