#!/bin/bash
set -e

echo "--- 🐉 Instalando Centro de Mando RPG ---"

# Check if python3 is installed
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Error: Python 3 no encontrado. Por favor instálalo antes de continuar."
    exit 1
fi

# Create env if it does not exist or reuse it if it does
if [ ! -d "venv" ]; then
    echo "1. Creando entorno virtual (venv)..."
    python3 -m venv venv
else
    echo "1. El entorno virtual ya existe. Se reutiliza."
fi

echo "2. Activando entorno..."
source venv/bin/activate

echo "3. Actualizando pip e instalando librerías..."
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

echo ""
echo "--- ✅ Instalación completada ---"
echo "Para iniciar el programa, ejecuta: ./run.sh"