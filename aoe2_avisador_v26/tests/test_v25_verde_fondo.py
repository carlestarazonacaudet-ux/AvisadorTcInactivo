"""Regresión V25: césped no equivale a progreso, imagen bajo el verde sí."""
import ast
import unittest
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TREE = ast.parse((ROOT / 'avisador_v26.py').read_text(encoding='utf-8'))
REQUIRED = {
    'neutralize_green', 'icon_similarity', 'prepared_queue_templates',
    'match_score', 'load_technology_templates', 'load_templates',
    'red_overlay_on_icon', 'green_progress_visible',
    'match_green_icon_structure', 'classify_queue_region'
}
NAMESPACE = {'cv2': cv2, 'np': np,
             'TECH_DIR': ROOT / 'tech_templates',
             'BUILTIN_DIR': ROOT / 'templates_builtin',
             'TEMPLATE_FILE': ROOT / 'no_custom_template.png',
             'LEGACY_TEMPLATE': ROOT / 'no_legacy_template.png',
             '_MATCH_PREPARED_CACHE': {}}
exec(compile(ast.Module(body=[n for n in TREE.body if isinstance(n, ast.FunctionDef)
                              and n.name in REQUIRED], type_ignores=[]),
             'recognizer_v25', 'exec'), NAMESPACE)


class GreenBackgroundRecognition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.villagers = NAMESPACE['load_templates']()
        cls.technologies = NAMESPACE['load_technology_templates']()
        cls.scales = [.85, .95, 1.0, 1.05, 1.15]

    def classify(self, image):
        return NAMESPACE['classify_queue_region'](
            image, self.villagers, self.technologies, self.scales)

    def test_uploaded_grass_screenshots_are_not_busy(self):
        for image_name in ('campo_verde_cuadricula_1.png', 'campo_verde_cuadricula_2.png'):
            with self.subTest(img=image_name):
                image = cv2.imread(str(ROOT / 'tests' / 'fixtures' / image_name))
                self.assertIsNotNone(image)
                self.assertTrue(NAMESPACE['green_progress_visible'](image))
                occupied, kind, _ = self.classify(image)
                self.assertFalse(occupied, kind)

    def test_crops_of_grass_do_not_match_an_icon(self):
        image = cv2.imread(str(ROOT / 'tests' / 'fixtures' / 'campo_verde_cuadricula_1.png'))
        for y, x in [(5, 3), (48, 90), (95, 206)]:
            crop = image[y:y+46, x:x+46]
            with self.subTest(y=y, x=x):
                self.assertFalse(self.classify(crop)[0])

    def test_icon_in_green_landscape_is_busy_and_green_is_transparent(self):
        image = cv2.imread(str(ROOT / 'tests' / 'fixtures' / 'campo_verde_cuadricula_1.png'))
        for item in ('MaleVillDE', 'FEMALEVILLDE', 'LoomDE',
                     'WheelbarrowDE', 'FeudalAgeIconDE', 'TownPatrolDE'):
            icon = cv2.imread(str(ROOT / 'iconos_originales' / (item + '.png')))
            icon = cv2.resize(icon, (46, 46), interpolation=cv2.INTER_AREA)
            for progress in (.0, .35, .75, 1.0):
                tinted = icon.copy()
                done = round(46 * progress)
                if done:
                    tinted[:, :done] = np.clip(
                        tinted[:, :done].astype(np.float32) * .28 +
                        np.array([26, 145, 28], dtype=np.float32) * .72,
                        0, 255).astype(np.uint8)
                full = image.copy()
                full[50:96, 130:176] = tinted
                with self.subTest(icon=item, progress=progress):
                    active, reason, _ = self.classify(full)
                    self.assertTrue(active, reason)

    def test_green_block_without_silhouette_does_not_prove_activity(self):
        image = np.full((60, 250, 3), 8, dtype=np.uint8)
        image[6:52, 130:176] = (26, 145, 28)
        self.assertFalse(self.classify(image)[0])

    def test_red_icon_remains_idle_over_green_landscape(self):
        landscape = cv2.imread(str(ROOT / 'tests' / 'fixtures' / 'campo_verde_cuadricula_2.png'))
        icon = cv2.resize(cv2.imread(str(ROOT / 'iconos_originales' / 'MaleVillDE.png')),
                          (46, 46), interpolation=cv2.INTER_AREA)
        red = np.clip(icon.astype(np.float32)*.55 +
                      np.array([8, 12, 125], dtype=np.float32)*.75,
                      0,255).astype(np.uint8)
        landscape[20:66, 80:126] = red
        active, _, _ = self.classify(landscape)
        self.assertFalse(active)


if __name__ == '__main__':
    unittest.main()
