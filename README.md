# AOE2 IDLE TC — Avisador de aldeanos para Age of Empires II: DE
V21 · Windows · Proyecto experimental (beta)

AOE2 IDLE TC es una aplicación de escritorio para Age of Empires II: Definitive Edition que observa la pantalla y avisa cuando deja de detectar producción activa en la cola calibrada del centro urbano. Muestra el tiempo sin producir, el IDLE TC acumulado y una estimación de los aldeanos que se podrían haber creado.

Importante: Es una herramienta externa de reconocimiento de imágenes; no es un mod interno, no automatiza acciones ni lee la memoria del juego. El detector es experimental y sus resultados dependen de la interfaz, la resolución y la calibración. No se ha validado completamente durante partidas reales en Windows. Consulta las normas de torneos y comunidades antes de utilizar avisos externos en competición.

Funciones principales
- Alertas configurables: voz («Crea aldeanos»), pitidos, audio MP3/WAV propio, aviso visual o ambos. Volumen, tamaño, posición y repetición del sonido personalizables.
- Estado de producción: utiliza plantillas de aldeanos masculinos y femeninos, tecnologías del centro urbano y distintos grados del progreso verde. Los iconos reconocidos en estado normal o verde se tratan como actividad; el icono teñido de rojo o la cola sin iconos activos se tratan como inactividad.
- Tiempo IDLE: el cálculo utiliza el reloj leído de la partida; no se inventan segundos cuando el OCR no puede leerlo. El aviso inicial está previsto tras 3 segundos de IDLE y la repetición sonora es ajustable entre 1 y 120 segundos de partida.
- Aldeanos no creados (estimación): uno por cada 25 segundos completos de IDLE. No equivale a una medición real de producción perdida: no descuenta situaciones estratégicas o limitaciones del juego.
- Acumulado permanente: panel flotante con IDLE TC total y reloj de arena animado cuando aumenta.
- Desglose por edades: Alta Edad Media, Feudal, Castillos e Imperial, con tiempo IDLE, aldeanos no creados y total, y exportación CSV.
- Inicio de partida y pausas: intenta detectar reinicios del reloj, incluso si la primera lectura es 00:00:30, y permite calibrar la pausa con F3; también cuenta con pausa manual del avisador.
- Ventanas flotantes: monitor, posición, escala, opacidad y visibilidad independientes para aviso grande, contador y panel de edades; botones flotantes de silencio, pausa y mostrar/ocultar.
- Preferencias persistentes: zonas, monitor, sonidos y demás opciones guardados en %LOCALAPPDATA%\AoE2Avisador\.
Regla de detección
Contenido reconocido en la cola de producción	IDLE de esa cola
Aldeano o tecnología normal (sin velo de progreso)	No aumenta
Aldeano o tecnología parcialmente / totalmente verde	No aumenta
Icono bloqueado por velo rojo	Aumenta si no hay otro icono activo en la misma cola
Cola vacía o sin producción activa reconocida	Aumenta


Límite esencial: la cola global permite detectar si hay producción visible, pero no identifica necesariamente qué TC está parado si otro produce. El modo por indicadores independientes exige que cada TC tenga su propia región de estado permanentemente visible.
Instalación rápida en Windows
Opción 1: ejecutar el proyecto
1. Descarga el contenido del repositorio (botón Code → Download ZIP) y descomprímelo.
2. Instala Python 3.12 en Windows, si aún no lo tienes. Necesitarás Internet la primera vez que se descarguen las dependencias.
3. Ejecuta INICIAR.bat. El script crea un entorno .venv, instala los paquetes de requirements.txt y abre avisador_v21.py.
4. Para leer el reloj y el número de aldeanos, instala Tesseract OCR con el idioma inglés (eng): ejecuta INSTALAR_OCR.bat y sigue sus indicaciones.
5. En AoE2: DE activa la cola global y utiliza preferentemente el modo de pantalla ventana sin bordes para mostrar las superposiciones.
6. Abre Detección y límites → Calibrar pantalla. Selecciona la región con los iconos de producción y la zona que contiene solo los dígitos del reloj. Si vas a usar el límite de población, calibra también su contador.
7. Selecciona el tipo de alerta, prueba el audio y los avisos flotantes, guarda preferencias y pulsa Iniciar monitorización.
Las zonas deben cubrir únicamente los iconos de la cola de producción, no la barra de recursos ni los botones de investigación del edificio. Si cambias la resolución o la escala del HUD, vuelve a calibrar.
Opción 2: generar un .exe de Windows
En un equipo Windows x64, ejecuta CREAR_EXE.bat. El generador instala, si es necesario, dependencias de compilación y utiliza PyInstaller para intentar crear:
dist\Avisador_Aldeanos_AoE2.exe
Para empaquetar OCR, el equipo de compilación necesita Tesseract OCR con eng.traineddata. La compilación no está garantizada en todos los equipos y el ejecutable NO viene incluido en este repositorio. Antes de distribuir un .exe, pruébalo en otro equipo Windows limpio. Más detalles en [la guía de uso](docs/GUIA_DE_USO.md).
Configuración y datos
%LOCALAPPDATA%\AoE2Avisador\configuracion.json
El directorio local permite mantener la calibración entre versiones. No subas a GitHub tus configuraciones personales, capturas privadas ni rutas de archivos de audio. La carpeta .venv, los ejecutables compilados y los archivos temporales están excluidos mediante .gitignore.
Estructura del proyecto
avisador_v21.py         # Aplicación de escritorio
INICIAR.bat             # Inicio e instalación de dependencias
INSTALAR_OCR.bat        # Ayuda para OCR
CREAR_EXE.bat           # Generación de ejecutable Windows
build_windows.py        # Configuración del empaquetado PyInstaller
requirements.txt        # Dependencias Python
aviso_visual.png        # Imagen predeterminada del aviso
age_templates/          # Referencias de las cuatro edades
tech_templates/         # Plantillas de tecnologías
iconos_originales/      # Iconos originales aportados como referencia
templates_builtin/      # Plantillas de aldeanos
tests/                  # Pruebas automatizadas
docs/                   # Manual, publicación y avisos de derechos
Pruebas
Tras instalar las dependencias Python:
.venv\Scripts\python.exe -m unittest discover -s tests -q
El paquete de V21 incluye un registro histórico de 45 pruebas automatizadas (RESULTADOS_PRUEBAS.txt), realizadas con capturas, imágenes y simulaciones. No sustituyen la validación del reconocimiento y de la superposición sobre el juego real.
