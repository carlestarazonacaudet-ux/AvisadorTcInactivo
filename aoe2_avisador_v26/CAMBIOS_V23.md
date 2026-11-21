# Cambios V23 — Escudos correctos confirmados

- Referencias de edad: exactamente los 4 WebP entregados y confirmados en esta conversación.
- Relación fija: I Alta Edad Media (`oscura`), II Edad Feudal (`feudal`), III Edad de los Castillos (`castillos`), IV Edad Imperial (`imperial`).
- Los archivos originales están en `age_shields/fuentes_confirmadas/` y las copias PNG sin cambio de color ni forma en `age_shields/`.
- Cada escudo cuenta con su máscara PNG (`*_mask.png`), que elimina el fondo exterior conservando bordes, trazos oscuros internos y el número romano.
- En V22 el umbral de brillo excluía partes oscuras *dentro* de la insignia: ahora la máscara se basa en el contorno cerrado, con el interior completo.
- Comparación en gris para mejorar el rendimiento y tolerar variaciones de tonalidad; se exige una puntuación mínima y ventaja respecto al segundo escudo antes de reconocer una edad.
- Se mantienen la confirmación de lecturas consecutivas, reloj de partida, pausa, IDLE total, edades, controles flotantes, calibración y configuración persistente.
- Las calibraciones del escudo realizadas con V22 se conservan. Si falla la detección, recalibrar únicamente el recuadro del escudo, sin texto ni reloj.

**Limitación:** validado con imágenes y fondos simulados, no con el juego en ejecución en Windows. El código fuente se ejecuta con `INICIAR.bat`; `CREAR_EXE.bat` genera el EXE en un ordenador Windows, no está incluido precompilado.
