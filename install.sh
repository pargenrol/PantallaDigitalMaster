#!/bin/bash
echo "--- Instalando Dependencias en Unix/Mac ---"

# Crear entorno
python3 -m venv venv
source venv/bin/activate

# Instalar librerías
pip install --upgrade pip
pip install -r requirements.txt
pip install Flask Werkzeug python-frontmatter markdown requests deep-translator

# Dar permiso al lanzador
chmod +x run.sh

echo "--- Proceso finalizado ---"