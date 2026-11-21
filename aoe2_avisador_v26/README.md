# AOE2 IDLE TC — V26 (OCR del reloj + doble detección de edad)

Avisador para **Age of Empires II: Definitive Edition** en Windows. Captura los píxeles del juego para reconocer actividad del centro urbano, leer el reloj de partida mediante OCR, mostrar el IDLE acumulado y por edades, calcular aldeanos no producidos y activar avisos visuales o sonoros.

> **Versión beta.** La detección de HUD depende de la escala, mods gráficos y calidad de la imagen. No se ha probado esta versión sobre una partida real de Windows; las pruebas automatizadas se ejecutan con plantillas y escenas simuladas. El programa no lee memoria ni automatiza las unidades.

## Novedades V26 — Reloj sobre fondo verde y reconocimiento redundante de edad

- **OCR del reloj mejorado:** cuando la zona capturada incluye `00:07:30 (Normal - 1.7) (Extremo)`, se prueban primero recortes de la **parte izquierda** para que las cifras de velocidad y dificultad no interfieran. Se mantienen las máscaras para texto blanco, amarillo, cian o dorado, incluidos fondos verdes del terreno. El resultado debe tener forma HH:MM:SS y minutos/segundos válidos; si falla, **se congela el contador**.
- **Dos fuentes independientes para reconocer la edad:** (1) escudo I–IV comparado con máscaras sin fondo; (2) nombre escrito con OCR, aceptando texto **blanco o amarillo**: `Alta Edad Media`, `Edad Feudal`, `Edad de los Castillos`, `Edad Imperial`.
- **Calibración separada y guardada:** en **IDLE por edades** tienes `Calibrar escudo de edad` y `Calibrar texto de edad (respaldo)`. Puedes usar una o ambas. Las dos zonas se guardan en `%LOCALAPPDATA%\AoE2Avisador\configuracion.json` y también al exportar/importar zonas. No hay que recalibrar la cola ni el reloj al actualizar.
- **Fusión sin falsas transiciones:** si ambas coinciden, se valida la edad; si solo una se reconoce, se utiliza esa; **si se contradicen, se mantiene la última edad confirmada** hasta obtener nuevas lecturas coherentes. El cambio aún requiere confirmación temporal. En la pestaña de edades se muestra la fuente utilizada.
- **Pruebas de regresión:** captura real del reloj `00:07:30` sobre césped con las etiquetas de velocidad y dificultad, reloj cian en dos fondos, y nombre de edad en amarillo y blanco; se mantienen las pruebas históricas de IDLE, progreso verde y escudos.

**Configuración recomendada:** selecciona la zona del reloj lo más cerca posible de las cifras. Si necesitas abarcar también `(Normal - 1.7)`, el nuevo OCR intentará aislar el tiempo. Para las edades, selecciona el escudo y el rótulo por separado, preferiblemente durante una partida con la interfaz habitual.

## Novedades V25 — Corregido el falso verde del terreno

**Problema solucionado:** el detector de V24 interpretaba superficies verdes del mapa como si fueran el velo de progreso de una producción. Esto podía detener el IDLE TC incluso con la cola vacía.

**Nueva lógica:**

1. Busca una **ilustración reconocible** de aldeano o tecnología en la región calibrada, utilizando todas las plantillas existentes.
2. Comprueba la estructura de la imagen original en **escala de grises**, sin sustituir todos los píxeles verdes por el mismo gris (esto producía coincidencias falsas con césped y cuadrículas).
3. Si el progreso verde ocupa casi todo el icono, hace una comparación adicional resistente a velos verdes **translúcidos**, confirmando que continúa viéndose la silueta. El verde por sí solo **nunca** demuestra actividad.
4. Un icono rojo continúa siendo **IDLE**, y la cola vacía también. En cola global basta con detectar una producción real para considerarla ocupada; no identifica todos los TC por separado.

**Pruebas:** se incorporan dos imágenes reales aportadas por el usuario (`tests/fixtures/campo_verde_cuadricula_1.png` y `campo_verde_cuadricula_2.png`) como negativos obligatorios, además de ensayos con seis iconos sobre césped y diferentes porcentajes de progreso verde, incluidos velos completos translúcidos.

**Límite técnico:** si un color verde **opaco** tapa el 100 % de la ilustración, una captura sin bordes ni indicadores visibles no permite saber qué hay debajo; en ese caso no se certifica una producción a partir del color. Es recomendable calibrar la zona de la cola con el marco del icono visible y no seleccionar el mapa.

**Para actualizar:** descomprime esta carpeta y ejecuta `INICIAR.bat`; se conservan las zonas guardadas en `%LOCALAPPDATA%\AoE2Avisador`. Si el ROI de producción incluye terreno, recalíbralo para abarcar únicamente la cola global del HUD.

## Novedades V24

### Reconocimiento de texto multicolor

- El reloj de partida se lee aunque los dígitos estén en **blanco, amarillo, dorado o cian**, y haya un fondo de mapa o de HUD oscuro.
- OCR en escala de grises, contraste adaptativo y máscaras HSV por color; reconoce también el texto amarillo de las capturas para diagnóstico (`ocr_hud_text`).
- Normaliza casos como `00:01::08` y valida horas, minutos y segundos; **no se usa el reloj de Windows** como sustituto.
- **Desde V26 se puede activar también la lectura del nombre escrito como respaldo a los escudos enmascarados I–IV.**

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

El detector por escudos compara la imagen visible con el escudo, permite cambios de escala, descarta coincidencias ambiguas y confirma las transiciones con varias lecturas. En V26 puede complementarse con OCR independiente del texto de edad. **No es necesario recalibrar la zona del escudo si ya funciona en V22**; si sigue fallando, selecciona solo la insignia, no el rótulo ni el reloj.

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
4. **Importante si actualizas desde V21 o anterior:** calibra **el escudo de edad y, opcionalmente, el texto de respaldo**. Si venías de la detección antigua del rótulo, dicha zona queda como copia; puedes calibrar de nuevo el texto en un botón independiente. No mezcles escudo y palabras en un mismo rectángulo.
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
- Si cambias de mod de interfaz, escala o resolución, recalibra las regiones del escudo y del texto.
- Los iconos de juego se proporcionan como recursos de referencia; revisa sus condiciones de uso antes de redistribuirlos públicamente.
