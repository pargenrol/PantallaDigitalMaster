@echo off
call venv\Scripts\activate
if not defined PORT set PORT=5001
start http://127.0.0.1:%PORT%/master
python app.py
