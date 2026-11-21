"""V24: mismo reloj de partida, un segundo de confirmación y OCR multicolor.
Se prueban clases aisladas para no necesitar pygame/mss en CI/Linux.
"""
import ast
import re
import unittest
from pathlib import Path

import cv2
import numpy as np
import pytesseract

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'avisador_v24.py').read_text(encoding='utf-8')
AST=ast.parse(SOURCE)
NEEDED={'ClockSynchronizedIdle','ClockSynchronizedIdleFiltered','hud_ocr_variants','ocr_digits','ocr_hud_text'}
nodes=[n for n in AST.body if getattr(n,'name','') in NEEDED]
ns={'cv2':cv2,'np':np,'re':re,'pytesseract':pytesseract}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'V24_Test', 'exec'),ns)
Engine=ns['ClockSynchronizedIdleFiltered']

class FilterTests(unittest.TestCase):
    def send(self,e,t,active=False,read=True,paused=False):
        return e.sample([('TC',active)],read,t,paused)

    def idle_three_seconds(self,e):
        self.send(e,10)
        for t in [11,12,13]: self.send(e,t)
        self.assertEqual(e.total_seconds,3)

    def test_flicker_does_not_end_alert_and_preserves_time(self):
        e=Engine(25,1)
        self.idle_three_seconds(e)
        a=self.send(e,13,True,False)
        self.assertEqual(a['idle'],3)
        self.assertTrue(a['pendientes_produccion'])
        a=self.send(e,13,False,False)
        self.assertEqual(a['idle'],3)
        a=self.send(e,14,False)
        self.assertEqual((a['idle'],a['total']),(4,4))

    def test_flicker_over_clock_tick_recovered_without_losing_seconds(self):
        e=Engine(25,2)
        self.idle_three_seconds(e)
        self.send(e,13,True,False)
        pending=self.send(e,14,True)
        self.assertEqual((pending['idle'],pending['total']),(3,3))
        self.assertEqual(pending['pendientes_produccion'],['TC'])
        final=self.send(e,14,False,False)
        self.assertEqual((final['idle'],final['total']),(4,4))

    def test_production_real_discards_reserved_second(self):
        e=Engine(25,1)
        self.idle_three_seconds(e)
        self.send(e,13,True,False)
        a=self.send(e,14,True)
        self.assertEqual((a['idle'],a['total']),(0,3))
        self.assertFalse(a['pendientes_produccion'])
        self.assertEqual(e.confirmed['TC'],True)
        self.send(e,15,True)
        self.assertEqual(e.total_seconds,3)
        # Nuevo IDLE después de producción comprobada.
        self.send(e,15,False,False)
        self.send(e,16,False)
        self.assertEqual(e.total_seconds,4)

    def test_no_confirmation_without_game_seconds(self):
        e=Engine(25,1)
        self.idle_three_seconds(e)
        for _ in range(20):
            a=self.send(e,13,True,False)
            self.assertEqual(a['idle'],3)
        self.assertEqual(e.total_seconds,3)

    def test_paused_does_not_count_or_confirm(self):
        e=Engine(25,1)
        self.idle_three_seconds(e)
        self.send(e,13,True,False)
        a=self.send(e,14,True,True,True)
        self.assertTrue(a['paused'])
        self.assertEqual((a['idle'],a['total']),(3,3))
        a=self.send(e,14,False)
        self.assertEqual(a['total'],3)
        a=self.send(e,15,False)
        self.assertEqual(a['total'],4)

    def test_one_zone_glitch_two_zones_totals(self):
        e=Engine(25,1)
        def snap(t,a=False,b=False,read=True):
            return e.sample([('A',a),('B',b)],read,t)
        snap(10)
        snap(11)
        self.assertEqual(e.total_seconds,2)
        snap(11,True,False,False)
        r=snap(12,True,False)
        self.assertEqual(r['total'],3) # B suma, A queda en reserva y se descuenta
        self.assertEqual(r['idle'],2)
        r=snap(13,True,False)
        self.assertEqual(r['total'],4)

    def test_time_jump_ignored(self):
        e=Engine(25,1)
        self.idle_three_seconds(e)
        self.send(e,13,True,False)
        invalid=self.send(e,130,True)
        self.assertFalse(invalid['clock_ok'])
        self.assertEqual(invalid['total'],3)

    def test_snapshot_total_monotonic_for_age_distribution(self):
        e=Engine(25,1)
        seq=[]
        self.send(e,100)
        for t in range(101,131):
            raw=(t % 7 == 0)
            s=self.send(e,t,raw)
            seq.append(s['total'])
        self.assertEqual(seq,sorted(seq))
        self.assertEqual(e.total_seconds,30)

class OCRColorsTests(unittest.TestCase):
    def test_uploaded_clock_cyan_over_dark_and_scene(self):
        fixtures=['clock_cyan_hud.png','clock_cyan_fondo_mapa.png']
        for name in fixtures:
            with self.subTest(name=name):
                img=cv2.imread(str(ROOT/'tests'/'fixtures'/name))
                self.assertEqual(ns['ocr_digits'](img,'tiempo'),68)

    def test_uploaded_age_text_yellow_visible(self):
        image=cv2.imread(str(ROOT/'tests'/'fixtures'/'edad_texto_amarillo.png'))
        self.assertIn('Alta Edad Media',ns['ocr_hud_text'](image))

    def test_clock_white_rendered_on_dark(self):
        im=np.zeros((45,180,3),np.uint8)
        cv2.putText(im,'00:05:25',(3,33),cv2.FONT_HERSHEY_SIMPLEX,.75,(255,255,255),2,cv2.LINE_AA)
        self.assertEqual(ns['ocr_digits'](im,'tiempo'),325)

if __name__=='__main__': unittest.main()
