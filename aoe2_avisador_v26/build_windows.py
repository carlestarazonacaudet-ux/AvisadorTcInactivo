"""Constructor para Windows: crea dist/Avisador_Aldeanos_AoE2.exe, con OCR incluido.
Ejecutar exclusivamente mediante CREAR_EXE.bat, desde un equipo Windows x64.
"""
from pathlib import Path
import os
import shutil
import sys

BASE = Path(__file__).resolve().parent


def find_ocr_folder():
    candidates = [
        os.getenv('AOE2_TESSERACT_DIR', ''),
        r'C:\Program Files\Tesseract-OCR',
        r'C:\Program Files (x86)\Tesseract-OCR',
    ]
    exe_on_path = shutil.which('tesseract')
    if exe_on_path:
        candidates.append(str(Path(exe_on_path).parent))
    for folder in candidates:
        if folder and (Path(folder) / 'tesseract.exe').is_file() and (Path(folder) / 'tessdata' / 'eng.traineddata').is_file():
            return Path(folder)
    raise RuntimeError('Falta Tesseract OCR con el idioma eng. Instálalo y vuelve a ejecutar CREAR_EXE.bat.')


def main():
    if os.name != 'nt':
        raise SystemExit('PyInstaller necesita compilar este .exe en Windows. Este proyecto no incluye un EXE precompilado.')
    from PyInstaller.__main__ import run
    ocr = find_ocr_folder()
    binary_args = []
    for file in [ocr / 'tesseract.exe', *ocr.glob('*.dll')]:
        binary_args += ['--add-binary', f'{file};ocr']
    # Recursos del OCR: lectura de cifras de HUD y reloj. Solo inglés, suficiente para dígitos.
    data_args = [
        '--add-data', f'{BASE / "templates_builtin"};templates_builtin',
        '--add-data', f'{BASE / "age_shields"};age_shields',
        '--add-data', f'{BASE / "tech_templates"};tech_templates',
        '--add-data', f'{BASE / "aviso_visual.png"};.',
        '--add-data', f'{ocr / "tessdata" / "eng.traineddata"};ocr/tessdata',
    ]
    # Algunos instaladores incluyen dependencias nativas en subdirectorios.
    # Empaquetar todos los DLL del directorio principal cubre el caso habitual UB Mannheim.
    run([
        '--onefile', '--windowed', '--noconfirm', '--clean',
        '--name', 'Avisador_Aldeanos_AoE2',
        '--distpath', str(BASE / 'dist'), '--workpath', str(BASE / 'build'),
        '--specpath', str(BASE),
        '--collect-all', 'pygame',
        *binary_args, *data_args,
        str(BASE / 'avisador_v26.py'),
    ])
    out = BASE / 'dist' / 'Avisador_Aldeanos_AoE2.exe'
    if not out.exists():
        raise SystemExit('No se ha generado el archivo EXE. Revisa el registro de PyInstaller.')
    print(f'\nEXE GENERADO: {out}\n')


if __name__ == '__main__':
    main()
