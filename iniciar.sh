#!/usr/bin/env bash
# Abre el Analizador de CVs SIN Docker (Linux o macOS).
# Uso, desde la carpeta del proyecto:   bash iniciar.sh
# La primera vez crea el entorno e instala las librerías (unos minutos); después es rápido.

cd "$(dirname "$0")" || exit 1
REQ="app/intermedio/cv_analyzer/requirements.txt"

PY=""
for candidato in python3 python; do
  if command -v "$candidato" >/dev/null 2>&1 && "$candidato" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
    PY="$candidato"; break
  fi
done
if [ -z "$PY" ]; then
  echo "No encontré Python 3.10 o superior. Instálalo y vuelve a intentar."; exit 1
fi

# 1) Entorno virtual: se prueba de tres formas, porque en algunos PC falta python3-venv
#    y no hay permisos de administrador para instalarlo.
if [ ! -x .venv/bin/python ]; then
  echo "== Creando el entorno virtual (.venv)"
  rm -rf .venv
  if ! "$PY" -m venv .venv >/dev/null 2>&1; then
    rm -rf .venv
    echo "   venv completo no disponible; se crea sin pip y se instala pip aparte"
    if "$PY" -m venv --without-pip .venv >/dev/null 2>&1; then
      "$PY" -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', '.venv/get-pip.py')" \
        && .venv/bin/python .venv/get-pip.py --quiet
    fi
  fi
  if [ ! -x .venv/bin/python ] || ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
    rm -rf .venv
    echo "   probando con virtualenv (instalación de usuario, sin sudo)"
    "$PY" -m pip install --user --quiet virtualenv 2>/dev/null \
      || "$PY" -m pip install --user --quiet --break-system-packages virtualenv
    "$PY" -m virtualenv --quiet .venv
  fi
fi
VPY=".venv/bin/python"
if [ ! -x "$VPY" ]; then
  echo "No se pudo crear el entorno virtual. Copia este mensaje y pide ayuda."; exit 1
fi

# 2) Librerías (si ya están, pip solo lo comprueba)
echo "== Revisando librerías"
"$VPY" -m pip install --quiet --disable-pip-version-check -r "$REQ" \
  || echo "   Aviso: pip no pudo instalar todo (¿sin internet?). Se intenta abrir igual."

# 3) Clave de Gemini en .env (la pide si falta)
"$VPY" configurar_clave.py || exit 1

# 4) La app. Si el puerto 8501 está ocupado, Streamlit usa el siguiente libre.
echo "== Abriendo el Analizador de CVs (Ctrl+C para detenerlo)"
exec "$VPY" -m streamlit run app/intermedio/cv_analyzer/app.py --browser.gatherUsageStats false
