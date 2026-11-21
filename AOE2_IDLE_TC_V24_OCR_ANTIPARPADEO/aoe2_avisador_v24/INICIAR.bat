@echo off
setlocal
cd /d "%~dp0"
title Avisador de aldeanos AoE2 DE V24
set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3.12"
)
if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    echo No se encuentra Python. Ejecuta CREAR_EXE.bat en Windows para generar el EXE autonomo.
    pause
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto error
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto error
".venv\Scripts\python.exe" avisador_v24.py
if errorlevel 1 goto error
exit /b 0
:error
echo Ha habido un error.
pause
exit /b 1
