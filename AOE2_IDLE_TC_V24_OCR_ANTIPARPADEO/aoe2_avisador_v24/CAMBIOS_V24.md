# Cambios V24

## Novedades V24

### Reconocimiento de texto multicolor

- El reloj de partida se lee aunque los dígitos estén en **blanco, amarillo, dorado o cian**, y haya un fondo de mapa o de HUD oscuro.
- OCR en escala de grises, contraste adaptativo y máscaras HSV por color; reconoce también el texto amarillo de las capturas para diagnóstico (`ocr_hud_text`).
- Normaliza casos como `00:01::08` y valida horas, minutos y segundos; **no se usa el reloj de Windows** como sustituto.
- **La detección de edades continúa por los escudos enmascarados I–IV, no por el nombre escrito.**

### Confirmación antiparpadeo de producción

- Nueva opción **Confirmar producción tras (s de juego)**, por defecto **1 s**. Se puede ajustar a 1, 2 o 3 segundos.
- Una detección aislada de aldeano/tecnología en una cola previamente inactiva **no borra el IDLE ni desactiva el aviso**.
- Si reaparece producción de forma continua durante el intervalo de confirmación, la app da por terminada la inactividad.
- Los segundos dudosos se mantienen en reserva hasta saber qué sucedió. Si fue un parpadeo de detección, se suman al IDLE; si realmente había producción, se descartan. Así el acumulado nunca necesita retroceder y el desglose por edades se mantiene consistente.
- Una lectura OCR fallida **congela el cronómetro**; no se añaden segundos inventados. Una zona de iconos temporalmente ilegible no reinicia el IDLE ya identificado.

La confirmación depende de **segundos del reloj de partida**, así que no vence durante las pausas o cuando el reloj está detenido. Si el OCR es incorrecto durante un periodo largo, el contador no podrá estimar el tiempo perdido.

### Pruebas con imágenes del juego

Las tres muestras de HUD recibidas están en `tests/fixtures/` y se usan para verificar los dígitos cian sobre fondo oscuro y sobre el mapa, además del rótulo amarillo. Las pruebas no requieren iniciar Age of Empires II, pero **todavía falta validar la app durante partidas reales en Windows**.

