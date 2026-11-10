"""Deja todo listo antes de abrir la app: el archivo .env con la clave y Streamlit sin preguntas.

Lo llaman iniciar.sh (Linux) e iniciar.ps1 (Windows). También se puede correr solo:
    python configurar_clave.py
"""
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ENV = RAIZ / ".env"
RELLENOS = ("", "clave_configurada", "tu_clave", "your_")


def limpiar(valor: str) -> str:
    """Sin espacios, comillas ni caracteres invisibles (los que se cuelan al pegar)."""
    valor = valor.strip().strip('"').strip("'")
    return "".join(c for c in valor if c.isprintable() and not c.isspace())


def leer(variable: str, lineas: list[str]) -> str:
    for linea in lineas:
        if linea.strip().startswith(f"{variable}="):
            return limpiar(linea.split("=", 1)[1])
    return ""


def es_real(valor: str) -> bool:
    return bool(valor) and not valor.lower().startswith(RELLENOS[1:])


def escribir(variable: str, valor: str, lineas: list[str]) -> list[str]:
    for i, linea in enumerate(lineas):
        if linea.strip().startswith(f"{variable}="):
            lineas[i] = f"{variable}={valor}"
            return lineas
    return [*lineas, f"{variable}={valor}"]


# 1) El .env: si no existe, se crea a partir del ejemplo
if not ENV.exists():
    ejemplo = RAIZ / ".env.example"
    if ejemplo.exists():
        shutil.copy(ejemplo, ENV)
    else:
        ENV.write_text("GOOGLE_API_KEY=\nOPENAI_API_KEY=\n", encoding="utf-8")
    print("Se creó el archivo .env")

lineas = ENV.read_text(encoding="utf-8").splitlines()
if es_real(leer("GOOGLE_API_KEY", lineas)) or es_real(leer("OPENAI_API_KEY", lineas)):
    print("Clave encontrada en .env")
else:
    print("\nNo hay clave de Gemini en el archivo .env.")
    print("Pégala aquí con CLIC DERECHO (no uses Ctrl+V) y pulsa Enter. Se verá mientras la pegas.")
    clave = limpiar(input("GOOGLE_API_KEY: "))
    if clave:
        ENV.write_text("\n".join(escribir("GOOGLE_API_KEY", clave, lineas)) + "\n", encoding="utf-8")
        print(f"Clave guardada en .env: {clave[:4]}…{clave[-4:]} ({len(clave)} caracteres). "
              "Ese archivo no se sube al repositorio.")
    else:
        print("Sin clave por ahora: podrás pegarla en la barra lateral de la app.")

# 2) Streamlit pregunta el correo la primera vez; con esto ya no lo hace
credenciales = Path.home() / ".streamlit" / "credentials.toml"
if not credenciales.exists():
    credenciales.parent.mkdir(parents=True, exist_ok=True)
    credenciales.write_text('[general]\nemail = ""\n', encoding="utf-8")
