#!/bin/bash

# Activar el entorno virtual
source venv/bin/activate

# URL de inicio
URL="http://127.0.0.1:5000/master"

echo "--- 🚀 Iniciando Centro de Mando ---"
echo "Abriendo navegador en $URL..."

# Intentar abrir el navegador según el Sistema Operativo
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open $URL
elif command -v xdg-open &> /dev/null; then
    # Linux (Gnome/KDE/etc)
    xdg-open $URL &> /dev/null &
else
    # Si no detecta navegador, solo avisa
    echo "⚠️  No pudimos abrir el navegador automáticamente."
    echo "👉  Por favor abre manualmente: $URL"
fi

# Iniciar la aplicación Flask
python3 app.py
