@echo off
title Lanzador Pantalla de Master
setlocal enabledelayedexpansion

:: 1. Ir a la carpeta
cd /d "%~dp0"

:: 2. Activar entorno
echo [1/4] Activando entorno virtual...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: No se encuentra venv. Ejecuta install.bat primero.
    pause
    exit /b
)

:: 3. Limpiar procesos de Edge (Para que el modo Kiosco no se bloquee)
echo [2/4] Limpiando procesos de Edge previos...
taskkill /f /im msedge.exe >nul 2>&1

:: 4. Iniciar el servidor Python
echo [3/4] Iniciando servidor de Flask...
:: Usamos 'start' sin '/b' para que veas si el servidor da error en otra ventana
start "SERVIDOR FLASK" python app.py

:: 5. Esperar a que el servidor arranque
echo [4/4] Esperando 5 segundos para abrir navegadores...
timeout /t 5 /nobreak >nul

:: 6. Ruta de Edge
set "EDGE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

:: 7. Lanzar pantallas con PERFILES TEMPORALES (Esto fuerza que sean independientes)
echo Lanzando Master...
start "" "%EDGE%" --app=http://127.0.0.1:5000 --user-data-dir="%CD%\venv\p1" --start-maximized

echo Lanzando Jugadores (Kiosco)...
:: El parametro --kiosk DEBE ir antes de la URL
start "" "%EDGE%" --user-data-dir="%CD%\venv\p2" --window-position=1920,0 --kiosk http://127.0.0.1:5000/player

echo.
echo ============================================
echo   PROCESO TERMINADO
echo ============================================
echo Si no se ven bien, mira los errores en las ventanas negras.
echo Para cerrar todo, cierra esta ventana y la del servidor.
pause