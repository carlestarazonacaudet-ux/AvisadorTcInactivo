# AOE2 IDLE TC — Cambios V26

## 1. OCR del reloj de partida
- Se aíslan las cifras del reloj a la izquierda antes de analizar textos auxiliares del HUD (velocidad, modo o dificultad).
- Máscaras por color y escala de grises, con validación estricta de HH:MM:SS.
- Validado con la imagen real `00:07:30 (Normal - 1.7) (Extremo)` sobre césped verde.
- Si no se consigue una lectura válida, no se añade tiempo de IDLE inventado.

## 2. Doble detección de edad
- Escudo con máscaras de fondo, usando los cuatro archivos confirmados por el usuario.
- OCR del texto de edad como fuente de respaldo en blanco o amarillo.
- Calibración por separado, con guardado persistente de ambas zonas.
- El display informa si la lectura procede del escudo, del texto, de ambos, o si existe conflicto.
- Si las dos lecturas discrepan, se mantiene la última edad confirmada.
- Se conserva el reconocimiento de edades por escudo ya calibrado; no se obliga a recalibrar el HUD entero.

## Verificación
- `python -m unittest discover -s tests -p "test_*.py" -q`
- 77 pruebas automatizadas superadas, incluidas las regresiones de versiones anteriores.
- No se ha validado todavía en una partida real con Windows y múltiples monitores.

## Instalación
Descomprimir y abrir `INICIAR.bat`; el archivo `CREAR_EXE.bat` permite crear un ejecutable en Windows, pero el ZIP NO contiene un EXE precompilado.
