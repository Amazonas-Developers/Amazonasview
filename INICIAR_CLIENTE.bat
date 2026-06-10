@echo off
REM ============================================================
REM  Inicia el CLIENTE Windows (app de escritorio) con su venv.
REM  Conecta al servidor de inferencia (ws://IP:9000/ws).
REM ============================================================
cd /d "%~dp0"
title CLIENTE - ELDE

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] No existe el venv del cliente.
    echo Ejecuta primero:  SETUP_CLIENTE.bat
    echo.
    pause
    exit /b 1
)

echo Iniciando cliente Windows...
venv\Scripts\python.exe src\main.py

echo.
echo El cliente se cerro.
pause
