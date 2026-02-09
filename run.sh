#!/bin/bash
set -e

URL="http://127.0.0.1:5000/master"

echo "--- 🚀 Iniciando Centro de Mando ---"

# Comprobate venv exists
if [ ! -d "venv" ]; then
    echo "❌ Error: entorno virtual no encontrado."
    echo "👉 Ejecuta primero: ./install.sh"
    exit 1
fi

# Activate venv
source venv/bin/activate

echo "✔ Entorno virtual activado"

# Start Flask server in background
echo "Iniciando servidor Flask..."
python app.py &
FLASK_PID=$!

# Wait to Flask
sleep 2

echo "Abriendo navegador en $URL..."

# Opem URL in default browser
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
else
    echo "⚠️ No se pudo abrir el navegador automáticamente."
    echo "👉 Abre manualmente: $URL"
fi

echo ""
echo "Servidor en ejecución (PID $FLASK_PID)"
echo "Para detenerlo: Ctrl+C"

# Wait for Flask to finish
wait $FLASK_PID