"""Validación de los cuatro WebP confirmados por el usuario y máscaras V23."""
import ast
import unittest
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXACT = [
    ('oscura', 'DarkAgeIconDE_confirmado.webp', 'Alta Edad Media (I)'),
    ('feudal', 'FeudalAgeIconDE_confirmado.webp', 'Edad Feudal (II)'),
    ('castillos', 'CastleAgeIconDE_confirmado.webp', 'Edad de los Castillos (III)'),
    ('imperial', 'ImperialAgeIconDE_confirmado.webp', 'Edad Imperial (IV)'),
]
source=(ROOT/'avisador_v26.py').read_text(encoding='utf-8')
tree=ast.parse(source)
needed={'shield_alpha_mask','score_shield_at_scale','age_shield_scores','load_age_signatures','detect_game_age'}
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in needed]
ns={'cv2':cv2,'np':np,'BASE':ROOT,
    'AGE_ORDER':('oscura','feudal','castillos','imperial'),
    'AGE_IMAGES':ROOT/'age_shields'}
exec(compile(ast.Module(body=functions,type_ignores=[]),'test_v23', 'exec'),ns)

class TestEscudosConfirmados(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signatures=ns['load_age_signatures']()

    def test_archivos_confirmados_preservados(self):
        self.assertEqual(len(self.signatures),4)
        for age,name,_ in EXACT:
            with self.subTest(age=age):
                original=cv2.imread(str(ROOT/'age_shields'/'fuentes_confirmadas'/name))
                actual=cv2.imread(str(ROOT/'age_shields'/f'{age}.png'))
                self.assertTrue(np.array_equal(original,actual))

    def test_mascara_excluye_fondo_y_conserva_escudo(self):
        for age,_,_ in EXACT:
            with self.subTest(age=age):
                ref,mask=self.signatures[age]
                self.assertEqual(mask.shape,ref.shape[:2])
                self.assertEqual(int(mask[0,0]),0)
                self.assertGreater(np.count_nonzero(mask),3500)
                self.assertLess(np.count_nonzero(mask),9000)
                self.assertEqual(int(mask[50,50]),255)

    def test_cuatro_edades_identificadas(self):
        for age,_,_ in EXACT:
            with self.subTest(age=age):
                ref,_=self.signatures[age]
                found,score=ns['detect_game_age'](ref,self.signatures)
                self.assertEqual(found,age)
                self.assertGreater(score,.95)

    def test_diferentes_fondos_de_partida(self):
        rng=np.random.default_rng(2302)
        backgrounds=[
            np.full((135,142,3),(32,79,148),dtype=np.uint8),
            np.full((135,142,3),(180,187,214),dtype=np.uint8),
            rng.integers(0,255,(135,142,3),dtype=np.uint8),
        ]
        for age,_,_ in EXACT:
            ref,mask=self.signatures[age]
            for j,bg in enumerate(backgrounds):
                with self.subTest(age=age,bg=j):
                    img=bg.copy()
                    r=cv2.resize(ref,(80,80),interpolation=cv2.INTER_AREA)
                    m=cv2.resize(mask,(80,80),interpolation=cv2.INTER_NEAREST)>0
                    roi=img[30:110,34:114]
                    roi[m]=r[m]
                    found,score=ns['detect_game_age'](img,self.signatures)
                    self.assertEqual(found,age, f'{age} recognized as {found}, score={score}')

    def test_ruido_sin_escudo_no_es_edad(self):
        for n in (20,80,160,240):
            blank=np.full((105,110,3),n,dtype=np.uint8)
            self.assertIsNone(ns['detect_game_age'](blank,self.signatures)[0])

if __name__=='__main__': unittest.main()
