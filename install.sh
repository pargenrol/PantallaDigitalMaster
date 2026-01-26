#!/bin/bash

echo "--- 🐉 Instalando Centro de Mando RPG ---"

# Comprobar si python3 está instalado
if ! command -v python3 &> /dev/null
then
    echo "❌ Error: Python 3 no encontrado. Por favor instálalo antes de continuar."
    exit 1
fi

echo "1. Creando entorno virtual (venv)..."
python3 -m venv venv

echo "2. Activando entorno..."
source venv/bin/activate

echo "3. Actualizando pip e instalando librerías..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "--- ✅ Instalación completada ---"
echo "Para iniciar el programa, ejecuta: ./run.sh"
