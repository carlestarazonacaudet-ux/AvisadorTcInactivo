# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('C:/Users/karle/Downloads/AOE2_IDLE_TC_V23_ESCUDOS_CONFIRMADOS/aoe2_avisador_v23/templates_builtin', 'templates_builtin'), ('C:/Users/karle/Downloads/AOE2_IDLE_TC_V23_ESCUDOS_CONFIRMADOS/aoe2_avisador_v23/age_shields', 'age_shields'), ('C:/Users/karle/Downloads/AOE2_IDLE_TC_V23_ESCUDOS_CONFIRMADOS/aoe2_avisador_v23/tech_templates', 'tech_templates'), ('C:/Users/karle/Downloads/AOE2_IDLE_TC_V23_ESCUDOS_CONFIRMADOS/aoe2_avisador_v23/aviso_visual.png', '.'), ('C:/Program Files/Tesseract-OCR/tessdata/eng.traineddata', 'ocr/tessdata')]
binaries = [('C:/Program Files/Tesseract-OCR/tesseract.exe', 'ocr'), ('C:/Program Files/Tesseract-OCR/libarchive-13.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libb2-1.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libbrotlicommon.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libbrotlidec.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libbz2-1.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libcairo-2.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libcrypto-3-x64.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libdatrie-1.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libdeflate.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libexpat-1.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libffi-8.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libfontconfig-1.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libfreetype-6.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libfribidi-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libgcc_s_seh-1.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libgif-7.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libgio-2.0-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libglib-2.0-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libgmodule-2.0-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libgobject-2.0-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libgraphite2.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libharfbuzz-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libiconv-2.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libicudt75.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libicuin75.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libicuuc75.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libintl-8.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libjbig-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libjpeg-8.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libleptonica-6.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libLerc.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/liblz4.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/liblzma-5.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libopenjp2-7.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libpango-1.0-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libpangocairo-1.0-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libpangoft2-1.0-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libpangowin32-1.0-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libpcre2-8-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libpixman-1-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libpng16-16.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libsharpyuv-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libstdc++-6.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libtesseract-5.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libthai-0.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libtiff-6.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libwebp-7.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libwebpmux-3.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libwinpthread-1.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/libzstd.dll', 'ocr'), ('C:/Program Files/Tesseract-OCR/zlib1.dll', 'ocr')]
hiddenimports = []
tmp_ret = collect_all('pygame')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:/Users/karle/Downloads/AOE2_IDLE_TC_V23_ESCUDOS_CONFIRMADOS/aoe2_avisador_v23/avisador_v23.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Avisador_Aldeanos_AoE2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
