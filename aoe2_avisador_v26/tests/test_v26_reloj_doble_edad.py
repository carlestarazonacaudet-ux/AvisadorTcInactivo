"""Pruebas de regresión V26: reloj en mapa verde y edad escudo+texto."""
import ast
import difflib
import re
import unittest
import unicodedata
from pathlib import Path

import cv2
import numpy as np
import pytesseract

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'avisador_v26.py'
MODULE = ast.parse(SOURCE.read_text(encoding='utf-8'))
NAMES = {
    'hud_ocr_variants', '_parse_hud_clock', '_clock_ocr_variants',
    'ocr_game_clock', 'ocr_digits', '_normalize_age_text',
    'identify_age_text', 'detect_game_age_text',
    'reconcile_age_observations'
}
CONTEXT = {
    'cv2': cv2, 'np': np, 'pytesseract': pytesseract,
    're': re, 'unicodedata': unicodedata, 'difflib': difflib,
    'AGE_TEXT_HINTS': {
        'oscura': ('alta edad media', 'edad oscura'),
        'feudal': ('edad feudal', 'feudal'),
        'castillos': ('edad de los castillos', 'edad castillos'),
        'imperial': ('edad imperial', 'imperial'),
    }
}
exec(compile(ast.Module(body=[n for n in MODULE.body if isinstance(n, ast.FunctionDef)
                              and n.name in NAMES], type_ignores=[]), str(SOURCE), 'exec'), CONTEXT)

class DualAgeAndClockTests(unittest.TestCase):
    def test_composite_clock_in_green_terrain(self):
        image = cv2.imread(str(ROOT / 'tests/fixtures/reloj_verde_modo_y_dificultad.png'))
        self.assertIsNotNone(image)
        self.assertEqual(CONTEXT['ocr_digits'](image, 'tiempo'), 450)

    def test_clock_alone_white_and_cyan(self):
        for name in ('clock_cyan_hud.png', 'clock_cyan_fondo_mapa.png'):
            img = cv2.imread(str(ROOT / 'tests/fixtures' / name))
            self.assertEqual(CONTEXT['ocr_digits'](img, 'tiempo'), 68, name)

    def test_bad_clock_does_not_become_valid(self):
        self.assertIsNone(CONTEXT['_parse_hud_clock']('1.7 (Extremo)'))
        self.assertIsNone(CONTEXT['_parse_hud_clock']('00:77:30'))
        self.assertEqual(CONTEXT['_parse_hud_clock']('00:01::08'), 68)

    def test_age_text_yellow_and_white(self):
        image = cv2.imread(str(ROOT / 'tests/fixtures/edad_texto_amarillo.png'))
        self.assertEqual(CONTEXT['detect_game_age_text'](image)[0], 'oscura')
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        yellow = cv2.inRange(hsv, (10,80,100), (45,255,255))
        white = image.copy()
        white[yellow > 0] = (250,250,250)
        self.assertEqual(CONTEXT['detect_game_age_text'](white)[0], 'oscura')

    def test_names_and_minor_ocr_errors(self):
        samples = {'Alta Edad Media': 'oscura', 'Edad Feudal': 'feudal',
                   'Edad de los Castillos':'castillos', 'Edad Imperial':'imperial',
                   'Edad de los Castillos ': 'castillos'}
        for label, expected in samples.items():
            with self.subTest(label=label):
                self.assertEqual(CONTEXT['identify_age_text'](label)[0], expected)
        self.assertIsNone(CONTEXT['identify_age_text']('Edad')[0])

    def test_age_fusion(self):
        fuse = CONTEXT['reconcile_age_observations']
        self.assertEqual(fuse('feudal','feudal'), ('feudal','ESCUDO + TEXTO'))
        self.assertEqual(fuse('feudal',None), ('feudal','ESCUDO'))
        self.assertEqual(fuse(None,'feudal'), ('feudal','TEXTO'))
        self.assertEqual(fuse('feudal','castillos'), (None,'CONFLICTO'))

    def test_calibration_persistence_code_present(self):
        content = SOURCE.read_text(encoding='utf-8')
        for part in ("'zona_edad_texto'", 'def calibrate_age_text(self)',
                     'def export_zones(self)', 'def import_zones(self)',
                     'detect_game_age_text(', 'reconcile_age_observations('):
            self.assertIn(part,content)

if __name__ == '__main__':
    unittest.main()
