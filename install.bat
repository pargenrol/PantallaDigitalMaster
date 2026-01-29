@echo off
title Servidor Pantalla de Master
setlocal

:: Cambiar al directorio del script
cd /d "%~dp0"

:: Activar el entorno virtual (IMPORTANTE para que encuentre las librerias)
if exist venv\Scripts\activate (
    call venv\Scripts\activate
) else (
    echo [ERROR] No se encuentra el entorno virtual. Ejecuta primero install.bat
    pause
    exit /b
)

:: Iniciar el servidor de Flask en segundo plano
echo Iniciando servidor en Python 3...
start /b python app.py

:: Esperar a que el servidor arranque
timeout /t 5 /nobreak >nul

echo Abriendo pantallas en tu navegador por defecto...

:: Abrir MASTER (Ventana nueva)
start "" http://127.0.0.1:5000

:: Abrir PLAYER (Ventana nueva)
:: Al ser el navegador por defecto, Windows la abrira donde estuviera la ultima vez.
:: Simplemente arrastrala a la segunda pantalla; la proxima vez recordara la posicion.
start "" http://127.0.0.1:5000/player

echo.
echo TODO LISTO. No cierres esta ventana durante la partida.