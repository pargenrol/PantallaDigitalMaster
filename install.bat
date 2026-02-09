@echo off
echo === Creando entorno virtual ===

python -m venv venv
if errorlevel 1 (
    echo ERROR: No se pudo crear el entorno virtual
    pause
    exit /b 1
)

call venv\Scripts\activate

echo === Actualizando pip ===
python -m pip install --upgrade pip setuptools wheel

echo === Instalando dependencias ===
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Fallo instalando requirements
    pause
    exit /b 1
)

echo === Instalacion completada correctamente ===
pause