#!/bin/bash

# 1. Activar entorno y lanzar servidor en segundo plano (silencioso)
source venv/bin/activate
python3 app.py > /dev/null 2>&1 &
SERVER_PID=$!

echo "Iniciando servidor RPG (PID: $SERVER_PID)..."
sleep 5

# 2. Detectar Sistema Operativo y Navegador
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - Usando Google Chrome
    BROWSER="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    MONITOR_2="--window-position=1920,0"
else
    # Linux - Intenta encontrar chrome o chromium
    BROWSER=$(which google-chrome || which chromium-browser || which chromium)
    MONITOR_2="--window-position=1920,0"
fi

echo "Abriendo pantallas..."

# PANTALLA MASTER (Ventana independiente limpia)
"$BROWSER" --app=http://127.0.0.1:5000 --user-data-dir="$PWD/venv/p_master" --start-maximized &

# PANTALLA JUGADOR (Modo Kiosco / Pantalla completa)
"$BROWSER" --kiosk --user-data-dir="$PWD/venv/p_player" $MONITOR_2 http://127.0.0.1:5000/player &

echo "Todo listo. Para cerrar el servidor, cierra esta terminal o usa: kill $SERVER_PID"