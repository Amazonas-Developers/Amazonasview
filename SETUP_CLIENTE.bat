@echo off
REM ============================================================
REM  SETUP (una sola vez) del CLIENTE Windows.
REM  Detecta venv roto/relocalizado (de otra PC) y lo recrea.
REM  Usa --system-site-packages (reusa PySide6/opencv globales).
REM ============================================================
cd /d "%~dp0"
title SETUP CLIENTE - ELDE

REM 1) Si el venv existe pero su python no corre, esta roto -> borrar
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe --version >nul 2>&1
    if errorlevel 1 (
        echo [!] venv roto detectado, recreando...
        rmdir /s /q venv
    )
)

REM 2) Crear venv si no existe
if not exist "venv\Scripts\python.exe" (
    echo Creando venv (--system-site-packages)...
    python -m venv venv --system-site-packages
)

REM 3) Instalar/verificar dependencias (las globales se omiten)
echo Instalando/verificando dependencias...
venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo SETUP COMPLETO. Ejecuta:  INICIAR_CLIENTE.bat
pause
