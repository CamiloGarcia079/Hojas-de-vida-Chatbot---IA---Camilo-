@echo off
rem Doble clic para abrir el Analizador de CVs en Windows (sin Docker).
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1"
pause
