@echo off
echo --- Instalando Entorno ---
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
echo --- Instalacion Completada ---
pause
