"""Pruebas de regresión con los iconos originales y estados de producción."""
import ast
import unittest
from pathlib import Path
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
TREE=ast.parse((ROOT/'avisador_v26.py').read_text(encoding='utf-8'))
NAMES={'neutralize_green','icon_similarity','prepared_queue_templates',
       'match_score','load_technology_templates','load_templates',
       'red_overlay_on_icon','green_progress_visible','match_green_icon_structure','classify_queue_region'}
MOD=ast.Module(body=[x for x in TREE.body if isinstance(x,ast.FunctionDef) and x.name in NAMES],type_ignores=[])
ns={'cv2':cv2,'np':np,'TECH_DIR':ROOT/'tech_templates','BUILTIN_DIR':ROOT/'templates_builtin',
    'TEMPLATE_FILE':ROOT/'unavailable','LEGACY_TEMPLATE':ROOT/'unavailable',
    '_MATCH_PREPARED_CACHE':{}}
exec(compile(MOD,'<recognizer_v21>','exec'),ns)
SCALES=(.85,.95,1.,1.05,1.15)

class TestOriginalIcons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v=ns['load_templates']()
        cls.t=ns['load_technology_templates']()

    def detect(self,im):
        return ns['classify_queue_region'](im,self.v,self.t,SCALES)

    def original(self,name):
        return cv2.resize(cv2.imread(str(ROOT/'iconos_originales'/f'{name}.png')),
                          (46,46),interpolation=cv2.INTER_AREA)

    def test_all_twelve_originals_are_busy(self):
        self.assertEqual(len(list((ROOT/'iconos_originales').glob('*.png'))),12)
        for path in (ROOT/'iconos_originales').glob('*.png'):
            with self.subTest(path=path.name):
                active,kind,_=self.detect(self.original(path.stem))
                self.assertTrue(active,kind)

    def test_all_old_ingame_samples_are_busy(self):
        for folder,pattern in [('tech_templates','tecnologia_*.png'),('templates_builtin','tpl*.png')]:
            for path in (ROOT/folder).glob(pattern):
                with self.subTest(path=path.name):
                    active,kind,_=self.detect(cv2.imread(str(path)))
                    self.assertTrue(active,kind)

    def test_progress_green_all_levels(self):
        for name in ['WheelbarrowDE','FeudalAgeIconDE','TownWatchDE','LoomDE','FEMALEVILLDE','MaleVillDE']:
            original=self.original(name)
            for progress in [0,.12,.35,.60,.85,1.]:
                im=original.copy()
                count=round(im.shape[1]*progress)
                if count:
                    tint=im[:,:count,:].astype('float32')
                    im[:,:count,:]=(tint*.28 + np.array([26,145,28])*.72).astype('uint8')
                with self.subTest(icon=name, progress=progress):
                    active,kind,_=self.detect(im)
                    self.assertTrue(active,kind)

    def test_red_overlay_is_idle_even_with_template_match(self):
        for name in ['WheelbarrowDE','FeudalAgeIconDE','FEMALEVILLDE','MaleVillDE','TownWatchDE']:
            original=self.original(name).astype('float32')
            red=np.clip(original*.55 + np.array([8,12,125],dtype='float32')*.75,0,255).astype('uint8')
            with self.subTest(icon=name):
                active,kind,_=self.detect(red)
                self.assertFalse(active,kind)
                self.assertIn('rojo',kind)

    def test_actual_user_red_sample_is_idle(self):
        path=Path('/mnt/data/image(20261120-155756).png')
        if not path.exists(): self.skipTest('Muestra de imagen roja no montada')
        active,kind,_=self.detect(cv2.imread(str(path)))
        self.assertFalse(active,kind)

    def test_blank_and_random_are_idle(self):
        for im in [np.zeros((46,46,3),dtype='uint8'),np.full((60,300,3),18,dtype='uint8')]:
            self.assertFalse(self.detect(im)[0])

    def test_global_queue_has_any_active_even_with_red_icon(self):
        active=self.original('LoomDE')
        red_original=self.original('MaleVillDE').astype('float32')
        red=np.clip(red_original*.55 + np.array([8,12,125],dtype='float32')*.75,0,255).astype('uint8')
        global_roi=np.full((60,250,3),8,dtype='uint8')
        global_roi[5:51,20:66]=red
        global_roi[5:51,130:176]=active
        self.assertTrue(self.detect(global_roi)[0])

    def test_global_red_only_still_idle(self):
        for name in ['MaleVillDE','FeudalAgeIconDE','WheelbarrowDE']:
            raw=self.original(name).astype('float32')
            red=np.clip(raw*.55 + np.array([8,12,125],dtype='float32')*.75,0,255).astype('uint8')
            area=np.full((64,300,3),10,dtype='uint8')
            area[10:56,20:66]=red
            with self.subTest(icon=name):
                self.assertFalse(self.detect(area)[0])

    def test_global_red_and_any_other_active(self):
        names=['MaleVillDE','FeudalAgeIconDE','WheelbarrowDE','FEMALEVILLDE']
        for red_name in names:
            raw=self.original(red_name).astype('float32')
            red=np.clip(raw*.55 + np.array([8,12,125],dtype='float32')*.75,0,255).astype('uint8')
            for active_name in ['DarkAgeIconDE','WheelbarrowDE','LoomDE','FEMALEVILLDE','MaleVillDE']:
                roi=np.full((64,300,3),10,dtype='uint8')
                roi[10:56,20:66]=red
                roi[10:56,130:176]=self.original(active_name)
                with self.subTest(rojo=red_name,produciendo=active_name):
                    self.assertTrue(self.detect(roi)[0])

    def test_opaque_green_without_visible_icon_is_not_proven_active(self):
        # Un bloque verde por sí solo no demuestra que haya producción.
        global_roi=np.full((60,250,3),8,dtype='uint8')
        global_roi[6:52,130:176]=(26,145,28)
        self.assertFalse(self.detect(global_roi)[0])

if __name__ == '__main__':
    unittest.main()
