# Abre el Analizador de CVs SIN Docker en Windows.
# Uso, desde la carpeta del proyecto en PowerShell:   .\iniciar.ps1
# (o doble clic en iniciar.bat). La primera vez instala todo; después es rápido.

Set-Location $PSScriptRoot
$req = "app\intermedio\cv_analyzer\requirements.txt"

# Python 3.10 o superior: primero "python", si no el lanzador "py -3"
$prueba = "import sys; sys.exit(sys.version_info < (3, 10))"
$py = $null; $pyArgs = @()
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python -c $prueba 2>$null
    if ($LASTEXITCODE -eq 0) { $py = "python" }
}
if (-not $py -and (Get-Command py -ErrorAction SilentlyContinue)) {
    & py -3 -c $prueba 2>$null
    if ($LASTEXITCODE -eq 0) { $py = "py"; $pyArgs = @("-3") }
}
if (-not $py) { Write-Host "No encontre Python 3.10 o superior. Instalalo desde python.org (marca 'Add to PATH')."; exit 1 }

# 1) Entorno virtual
$vpy = ".venv\Scripts\python.exe"
if (-not (Test-Path $vpy)) {
    Write-Host "== Creando el entorno virtual (.venv)"
    & $py @pyArgs -m venv .venv
}
if (-not (Test-Path $vpy)) { Write-Host "No se pudo crear el entorno virtual."; exit 1 }

# 2) Librerias (si ya estan, pip solo lo comprueba)
Write-Host "== Revisando librerias"
& $vpy -m pip install --quiet --disable-pip-version-check -r $req
if ($LASTEXITCODE -ne 0) { Write-Host "   Aviso: pip no pudo instalar todo (sin internet?). Se intenta abrir igual." }

# 3) Clave de Gemini en .env (la pide si falta)
& $vpy configurar_clave.py
if ($LASTEXITCODE -ne 0) { exit 1 }

# 4) La app. Si el puerto 8501 esta ocupado, Streamlit usa el siguiente libre.
Write-Host "== Abriendo el Analizador de CVs (Ctrl+C para detenerlo)"
& $vpy -m streamlit run app\intermedio\cv_analyzer\app.py --browser.gatherUsageStats false
