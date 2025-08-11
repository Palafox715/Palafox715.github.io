@echo off
REM Moverse al directorio del script
cd /d "%~dp0%"
REM Activar el entorno virtual
call venv\Scripts\activate.bat
REM Arrancar la app
python app.py
REM Pausa para ver logs al cerrar
pause
