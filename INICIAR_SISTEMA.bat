@echo off
title Lanzador de Sistema de Canibalizacion - L504
setlocal

:: Obtener la ruta de la carpeta actual
set BASE_DIR=%~dp0
cd /d "%BASE_DIR%"

echo ==========================================
echo    SISTEMA DE REGISTRO - PLANTA L504
echo ==========================================
echo.

:: 1. Verificar si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo Por favor instale Python desde python.org para continuar.
    pause
    exit /b
)

:: 2. Intentar activar entorno virtual o crear uno si no existe
if not exist "venv" (
    echo [INFO] Creando entorno virtual para primer uso...
    python -m venv venv
)

echo 1. Activando entorno...
call venv\Scripts\activate.bat

:: 3. Instalar/Actualizar dependencias
echo 2. Verificando librerias necesarias...
pip install -r requirements.txt --quiet

:: 4. Iniciar Servidor y Navegador
echo 3. Iniciando Servidor en http://localhost:8080 ...
echo.

:: Abrir el navegador despues de 3 segundos
start "" "http://localhost:8080/index.html"

:: Ejecutar la aplicacion con Uvicorn
python app.py

pause
