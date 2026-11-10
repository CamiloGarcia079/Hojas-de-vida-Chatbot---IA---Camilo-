"""Revisa que el entorno esté bien armado: paquetes, base de datos y claves."""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

print("1. Paquetes")
for nombre in ["langchain", "langchain_openai", "langchain_google_genai", "chromadb", "streamlit"]:
    try:
        __import__(nombre)
        print(f"   OK  {nombre}")
    except ImportError:
        print(f"   FALTA  {nombre}")

print("\n2. PostgreSQL")
try:
    engine = create_engine(os.getenv("DATABASE_URL"))
    with engine.connect() as conexion:
        version = conexion.execute(text("SELECT version();")).scalar()
    print("   OK ", version)
except Exception as error:
    print("   ERROR", error)

print("\n3. Claves (solo digo si están, nunca su valor)")
for clave in ["OPENAI_API_KEY", "GOOGLE_API_KEY"]:
    print(f"   {clave}: {'configurada' if os.getenv(clave) else 'vacía'}")
