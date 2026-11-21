@echo off
cd /d "%~dp0"
echo Instalacion opcional para leer el reloj y el numero de aldeanos.
echo Para el reinicio automatico al empezar otra partida, Tesseract OCR es necesario.
where winget >nul 2>nul
if errorlevel 1 (
  echo No se encuentra winget. Instala Tesseract OCR manualmente.
  pause
  exit /b 1
)
winget install --id UB-Mannheim.TesseractOCR -e --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
 echo Si no se ha podido instalar, busca Tesseract OCR Windows UB Mannheim.
)
echo Cierra y vuelve a abrir INICIAR.bat tras instalarlo.
pause
