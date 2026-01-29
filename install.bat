@echo off
setlocal
title Instalador Pantalla de Master

echo ============================================
echo   INSTALANDO ENTORNO PYTHON 3
echo ============================================

:: 1. Verificar/Instalar Python 3
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Python 3 no detectado. Descargando...
    powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe -OutFile py_inst.exe"
    echo Instalando...
    start /wait py_inst.exe /quiet InstallAllUsers=1 PrependPath=1
    del py_inst.exe
)

:: 2. Crear entorno virtual y librerias
echo [1/2] Creando entorno virtual (venv)...
python -m venv venv
call venv\Scripts\activate

echo [2/2] Instalando librerias...
python -m pip install --upgrade pip
pip install Flask==2.3.3 Werkzeug==2.3.7 python-frontmatter markdown requests deep-translator

echo ============================================
echo   INSTALACION COMPLETADA
echo ============================================
pause