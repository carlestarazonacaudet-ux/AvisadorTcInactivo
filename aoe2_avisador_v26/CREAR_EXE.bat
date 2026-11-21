@echo off
setlocal
cd /d "%~dp0"
title Crear Avisador_Aldeanos_AoE2.exe (Windows x64)
echo.
echo === GENERADOR DE EXE AUTONOMO ===
echo Se necesita Internet y Windows x64 SOLO para compilar.
echo El EXE generado no necesitara instalar Python ni Tesseract.
echo.
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
  echo Python no disponible. Instalando Python 3.12 con winget...
  where winget >nul 2>nul
  if errorlevel 1 goto missing_winget
  winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
  echo.
  echo Vuelve a ejecutar CREAR_EXE.bat para continuar.
  pause
  exit /b 0
)
if not exist "C:\Program Files\Tesseract-OCR\tesseract.exe" if not exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
  where tesseract >nul 2>nul
  if errorlevel 1 (
    echo Instalando Tesseract OCR, que quedara EMPAQUETADO dentro del EXE...
    where winget >nul 2>nul
    if errorlevel 1 goto missing_winget
    winget install --id UB-Mannheim.TesseractOCR -e --source winget --accept-package-agreements --accept-source-agreements
    if errorlevel 1 goto error
  )
)
if not exist ".build-venv\Scripts\python.exe" (
  %PYTHON_CMD% -m venv ".build-venv"
  if errorlevel 1 goto error
)
".build-venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt "pyinstaller>=6.10,<7"
if errorlevel 1 goto error
".build-venv\Scripts\python.exe" build_windows.py
if errorlevel 1 goto error
echo.
echo EXITO: se ha creado dist\Avisador_Aldeanos_AoE2.exe
explorer "%~dp0dist"
pause
exit /b 0
:missing_winget
echo Windows no tiene winget. Instala Python 3.12 y Tesseract OCR y repite.
goto error
:error
echo.
echo NO SE HA GENERADO UN EXE AUTONOMO. Revisa el mensaje anterior.
pause
exit /b 1
