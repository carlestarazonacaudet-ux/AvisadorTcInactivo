"""Pruebas de tecnología y aldeano: los 13 recortes aportados por el usuario."""
import ast
from pathlib import Path
import unittest
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
TREE=ast.parse((ROOT/'avisador_v26.py').read_text(encoding='utf8'))
NAMES={'neutralize_green','icon_similarity','match_score','choose_production_kind','load_technology_templates','prepared_queue_templates','red_overlay_on_icon','green_progress_visible','match_green_icon_structure','classify_queue_region'}
CODE=ast.Module(body=[n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name in NAMES], type_ignores=[])
ns={'cv2':cv2,'np':np,'TECH_DIR':ROOT/'tech_templates','_MATCH_PREPARED_CACHE':{}}
exec(compile(CODE,'<v20_detector>','exec'),ns)
SCALES=[.85,.95,1.,1.05,1.15]

class TestTechnologyIcons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.technologies=ns['load_technology_templates']()
        cls.villagers=[]
        for p in sorted((ROOT/'templates_builtin').glob('*.png')):
            cls.villagers.append((p.name,cv2.imread(str(p))))

    def classify(self, img):
        v=ns['match_score'](img,self.villagers,SCALES)[0]
        t=ns['match_score'](img,self.technologies,SCALES)[0]
        return ns['classify_queue_region'](img,self.villagers,self.technologies,SCALES)[:2]

    def test_all_13_technology_samples_are_production(self):
        self.assertEqual(len(self.technologies),23)
        for name,image in self.technologies:
            with self.subTest(icon=name):
                is_busy, category=self.classify(image)
                self.assertTrue(category)
                self.assertTrue(is_busy)

    def test_all_six_villagers_remain_villagers(self):
        self.assertEqual(len(self.villagers),8)
        for name,image in self.villagers:
            with self.subTest(icon=name):
                is_busy, category=self.classify(image)
                self.assertTrue(category)
                self.assertTrue(is_busy)

    def test_green_progress_still_counts_as_active(self):
        original=cv2.imread(str(ROOT/'tech_templates'/'tecnologia_183758.png'))
        h,w=original.shape[:2]
        for progress in (.2,.5,.75,.95):
            image=original.copy()
            tint=image.copy()
            tint[:,:int(w*progress)]=(10,150,35)
            image=cv2.addWeighted(image,.42,tint,.58,0)
            with self.subTest(progress=progress):
                busy,_=self.classify(image)
                self.assertTrue(busy)

    def test_blank_queue_does_not_count_as_production(self):
        self.assertEqual(ns['choose_production_kind'](.05,.03),('vacio',False))

    def test_greened_villager_not_confused_with_technology(self):
        t=cv2.imread(str(ROOT/'templates_builtin'/'tpl5.png'))
        self.assertTrue(self.classify(t)[0])

    def test_technology_match_in_global_queue(self):
        image=cv2.imread(str(ROOT/'tech_templates'/'tecnologia_183801.png'))
        area=np.zeros((85,320,3),dtype=np.uint8)
        area[13:13+image.shape[0],155:155+image.shape[1]]=image
        active,_=self.classify(area)
        self.assertTrue(active)

    def test_correct_default_flags(self):
        defs=next(n.value for n in TREE.body if isinstance(n,ast.Assign)
                  and any(isinstance(t,ast.Name) and t.id=='DEFAULTS' for t in n.targets))
        val=ast.literal_eval(defs)
        self.assertTrue(val['tecnologias_activo'])
        self.assertTrue(val['mostrar_aviso_visual'])

if __name__=='__main__':unittest.main()
