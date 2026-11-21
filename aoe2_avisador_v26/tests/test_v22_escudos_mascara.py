"""V22: pruebas del escudo con fondo variable sin importar dependencias GUI."""
import ast
import unittest
from pathlib import Path
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
TREE=ast.parse((ROOT/'avisador_v26.py').read_text(encoding='utf-8'))
needed={'shield_alpha_mask','score_shield_at_scale','age_shield_scores','load_age_signatures','detect_game_age'}
nodes=[n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name in needed]
ns={'cv2':cv2,'np':np,'BASE':ROOT,'AGE_ORDER':('oscura','feudal','castillos','imperial'),'AGE_IMAGES':ROOT/'age_shields'}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'isolated_v22','exec'),ns)

class TestEscudosV22(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.refs=ns['load_age_signatures']()

    def test_four_signatures_and_masks_ignore_background(self):
        self.assertEqual(len(self.refs),4)
        for age,(image,mask) in self.refs.items():
            self.assertEqual(image.shape[:2],mask.shape)
            # Los bordes en negro del archivo original NO participan.
            self.assertEqual(int(mask[0,0]),0)
            self.assertGreater(np.count_nonzero(mask),1200)
            self.assertEqual(ns['detect_game_age'](image,self.refs)[0],age)

    def test_variable_backgrounds_and_smaller_icons(self):
        rng=np.random.default_rng(123)
        backgrounds=[
            np.full((120,120,3),(28,90,150),np.uint8),
            np.full((120,120,3),(240,221,185),np.uint8),
            rng.integers(15,140,(120,120,3),dtype=np.uint8),
        ]
        for age,(image,mask) in self.refs.items():
            for background in backgrounds:
                with self.subTest(age=age,bg=int(background.mean())):
                    dst=background.copy()
                    template=cv2.resize(image,(60,60))
                    binary=cv2.resize(mask,(60,60),interpolation=cv2.INTER_NEAREST)>0
                    y,x=25,30
                    dst[y:y+60,x:x+60][binary]=template[binary]
                    predicted,confidence=ns['detect_game_age'](dst,self.refs)
                    self.assertEqual(predicted,age)
                    self.assertGreater(confidence,.9)

    def test_no_random_age_on_blank(self):
        for value in (0,20,170,255):
            blank=np.full((100,100,3),value,np.uint8)
            self.assertIsNone(ns['detect_game_age'](blank,self.refs)[0])

    def test_no_reliance_on_text_ocr(self):
        s=(ROOT/'avisador_v26.py').read_text(encoding='utf-8')
        self.assertNotIn('def age_text_signature(',s)
        self.assertIn('def shield_alpha_mask(',s)
        self.assertIn('def capture_after_pause_button(',s)
        self.assertNotIn('def capture_on_f3(',s)

if __name__=='__main__':
    unittest.main()
