@echo off
setlocal
set SCRIPT_DIR=%~dp0
if exist "%SCRIPT_DIR%venv\Scripts\pythonw.exe" (
    start "" "%SCRIPT_DIR%venv\Scripts\pythonw.exe" "%SCRIPT_DIR%astro_collision_gui.py"
    exit /b 0
)
if exist "%SCRIPT_DIR%venv\Scripts\python.exe" (
    "%SCRIPT_DIR%venv\Scripts\python.exe" "%SCRIPT_DIR%astro_collision_gui.py"
    exit /b %ERRORLEVEL%
)
echo No se encontro el entorno virtual en %SCRIPT_DIR%venv\Scripts
pause
