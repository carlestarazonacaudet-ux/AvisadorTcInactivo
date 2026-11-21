# AOE2 IDLE TC — V24 (OCR multicolor y filtro antiparpadeos)

Avisador para **Age of Empires II: Definitive Edition** en Windows. Captura los píxeles del juego para reconocer actividad del centro urbano, leer el reloj de partida mediante OCR, mostrar el IDLE acumulado y por edades, calcular aldeanos no producidos y activar avisos visuales o sonoros.

> **Versión beta.** La detección de HUD depende de la escala, mods gráficos y calidad de la imagen. No se ha probado esta versión sobre una partida real de Windows; las pruebas automatizadas se ejecutan con plantillas y escenas simuladas. El programa no lee memoria ni automatiza las unidades.

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

## Corrección de la versión 23

Los cuatro escudos confirmados por el usuario se conservan **sin redibujar ni sustituir por otras imágenes**:

| Escudo | Edad | Archivo |
|---|---|---|
| I | Alta Edad Media | `age_shields/oscura.png` |
| II | Edad Feudal | `age_shields/feudal.png` |
| III | Edad de los Castillos | `age_shields/castillos.png` |
| IV | Edad Imperial | `age_shields/imperial.png` |

Las cuatro imágenes en V22 eran ya idénticas a las confirmadas. El cambio real está en la **máscara**: V23 conserva los detalles oscuros dentro del escudo (también los números romanos) y elimina únicamente el fondo exterior. Las máscaras se incluyen como `age_shields/*_mask.png`; los WebP originales están en `age_shields/fuentes_confirmadas/`.

El detector no utiliza OCR de los nombres de edad. Compara la imagen visible con el escudo, permite pequeños cambios de escala, descarta coincidencias ambiguas y confirma las transiciones con varias lecturas. **No es necesario recalibrar la zona del escudo si ya funciona en V22**; si sigue fallando, selecciona solo la insignia, no el rótulo ni el reloj.

## Cambios heredados de la versión 22

- **Edades con escudos**: Alta Edad Media **I**, Edad Feudal **II**, Castillos **III**, Imperial **IV**. Ya no necesita reconocer las palabras del HUD.
- **Máscara de fondo**: cada escudo se compara a través de una máscara que descarta los píxeles negros del fondo de su imagen original. Se compara el contenido visible del escudo, incluso si el escenario de detrás cambia.
- **Tolerancia de escala**: pequeñas variaciones del tamaño y la posición de la insignia.
- **Pausa sin tecla predefinida**: durante la calibración se usa la tecla de pausa que tengas configurada; **F3 no es obligatorio**. El motor IDLE también se congela cuando el reloj del juego deja de avanzar.
- **OCR tolerante al color**: lectura del reloj y los números en gris, blanco o amarillento, con distintos procesados de luminosidad.
- **Mandos compactos**: 🔊/🔇 sonido, Ⅱ/▶ pausa del avisador, **↑** contador superior, **←** alerta, **→** edades. El color del botón indica si el panel está visible.
- **Vista previa en configuración**: `Mostrar/probar mandos` abre los controles y los tres paneles de prueba; puedes ocultarlos y recuperarlos sin comenzar a monitorizar. `Cerrar prueba` cierra todo.

## Puesta en marcha

1. Descomprime el ZIP en una carpeta de Windows.
2. Abre `INICIAR.bat`. Es necesaria una instalación de Python para ejecutar el proyecto fuente; el BAT crea un entorno e instala las dependencias.
3. Calibra la **cola de producción**, el **reloj** y el **contador de aldeanos** según corresponda. Para leer el reloj necesitas Tesseract OCR (`INSTALAR_OCR.bat`).
4. **Importante si actualizas desde V21 o anterior:** vuelve a calibrar **solo el escudo de edad**. Si venías de la detección del rótulo por texto, la zona anterior queda como copia, pero el detector no la reutiliza. Marca el escudo I, II, III o IV, ajustado, sin incluir reloj ni texto.
5. Opcionalmente, calibra la pausa: el programa espera 5 s mientras pausas con la tecla configurada y captura el cartel de pausa; después repite para la imagen sin pausa.
6. En la pestaña **IDLE por edades**, activa el panel, posición y monitor. Usa la prueba del display para comprobar la superposición.
7. En la misma pestaña, pulsa **Mostrar/probar mandos** para comprobar flechas, sonido y pausa sin iniciar el juego.
8. Inicia la monitorización.

Las configuraciones y zonas se guardan en `%LOCALAPPDATA%\AoE2Avisador\configuracion.json`. No es necesario recalibrar las otras zonas al pasar de V21 a V22. Las estadísticas y el acumulado se basan únicamente en los segundos leídos del reloj del juego; una lectura fallida no inventa tiempo.

## Interpretación de las flechas

| Botón | Función |
|---|---|
| ↑ | Mostrar/ocultar el contador IDLE superior |
| ← | Mostrar/ocultar el aviso grande de la izquierda |
| → | Mostrar/ocultar el desglose por edades de la derecha |
| 🔊 / 🔇 | Silenciar/activar sonido, sin detener los cálculos |
| Ⅱ / ▶ | Pausar/reanudar el avisador (no pausa el juego) |

## Ejecutable

`CREAR_EXE.bat` prepara la compilación de Windows con PyInstaller y Tesseract. **Este ZIP contiene código fuente y los archivos de compilación, no un ejecutable de Windows ya generado.** La compilación debe ejecutarse en Windows.

## Notas de detección

- Las imágenes `age_shields/oscura.png`, `feudal.png`, `castillos.png` e `imperial.png` son referencias exactas de los cuatro escudos y contienen sus números romanos.
- Las máscaras `*_mask.png` se preparan a partir del contorno visible del escudo. Se excluye el fondo exterior, pero se conservan también los detalles oscuros internos. `shield_alpha_mask` permite regenerar la máscara si falta.
- Se exige confianza mínima y separación respecto al segundo escudo para evitar cambios de edad falsos. Los cambios se confirman con lecturas consecutivas.
- Si cambias de mod de interfaz, escala o resolución, recalibra la región del escudo.
- Los iconos de juego se proporcionan como recursos de referencia; revisa sus condiciones de uso antes de redistribuirlos públicamente.
