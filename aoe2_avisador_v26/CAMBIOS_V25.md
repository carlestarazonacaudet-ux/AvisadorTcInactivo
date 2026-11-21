# AOE2 IDLE TC V25 — Filtro del fondo verde

## Motivo
Dos capturas del césped de Age of Empires II provocaban falsos positivos en la V24: el filtro `green_progress_visible` trataba el color verde como prueba de una producción. Además, la neutralización del verde convertía iconos y terreno en patrones grises similares.

## Corrección
- `green_progress_visible` queda como **indicio auxiliar**, nunca decide que un TC está ocupado.
- `match_score` requiere coincidencia estructural de la ilustración original en luminancia, antes de aceptar el emparejamiento; los píxeles verdes del terreno dejan de tener una similitud artificial elevada.
- `match_green_icon_structure` confirma mediante comparación directa la presencia de una ilustración de aldeano o tecnología bajo velos verdes transparentes, incluidos los que cubren toda la imagen y aún dejan ver su silueta.
- Sin icono confirmado, el color verde no detiene la suma de IDLE. Los iconos rojos mantienen la interpretación de inactividad.
- Las dos capturas reales de césped se incluyen como pruebas de regresión negativas, además de composiciones sintéticas de iconos válidos sobre césped.

## Cómo probar
1. Ejecuta `INICIAR.bat` en Windows (no necesita recompilar un EXE).
2. Comprueba que la zona de producción calibrada muestre solo la cola y no el escenario. Recalibra si cambiaste la escala del HUD.
3. Verifica una cola vacía con fondo verde (IDLE aumenta) y una producción real parcialmente teñida de verde (IDLE no aumenta).
4. Usa `python -m unittest discover -s tests -p "test_*.py" -q` para ejecutar las pruebas locales si tienes Python y librerías instaladas.

## Limitación
Una cobertura verde **totalmente opaca** que oculte icono, marco y dígitos resulta indistinguible de otros objetos completamente verdes a partir de una imagen aislada. En ese caso no se puede garantizar la detección; se requiere contexto temporal o indicadores adicionales. Se mantiene la detección de progreso **translúcido**, que conserva la textura del icono.

No se ha podido comprobar la V25 durante partidas reales en Windows; se han realizado pruebas automatizadas y de regresión con imágenes.
