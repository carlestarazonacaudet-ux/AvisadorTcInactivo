"""Pruebas de V19: reloj de partida, reinicio tardío, red, edades y pérdidas."""
import ast
import pathlib
import unittest
import numpy as np
import cv2

root=pathlib.Path(__file__).parents[1]
source=(root/'avisador_v24.py').read_text(encoding='utf8')
tree=ast.parse(source)
classes={'AgeIdleTracker','ClockSynchronizedIdle','MatchClockResetDetector'}
funcs={'red_coverage','red_idle_detected','rect_overlap'}
assigns={'AGE_ORDER'}
nodes=[]
for n in tree.body:
    if isinstance(n,ast.ClassDef) and n.name in classes: nodes.append(n)
    if isinstance(n,ast.FunctionDef) and n.name in funcs: nodes.append(n)
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assigns for t in n.targets):nodes.append(n)
ns={'cv2':cv2,'np':np}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<v18_test>','exec'),ns)

class TestRestart(unittest.TestCase):
    def test_restarts_at_thirty_seconds(self):
        d=ns['MatchClockResetDetector']()
        for i in (920,921,922):self.assertFalse(d.observe(i))
        self.assertFalse(d.observe(30))
        self.assertTrue(d.observe(31))
        self.assertFalse(d.observe(32))

    def test_restarts_at_zero(self):
        d=ns['MatchClockResetDetector']()
        d.observe(400)
        self.assertFalse(d.observe(0))
        self.assertTrue(d.observe(0))

    def test_ignores_single_bad_clock(self):
        d=ns['MatchClockResetDetector']()
        for s in (1500,1501,30,1502,1503):
            self.assertFalse(d.observe(s))
        self.assertFalse(d.observe(31))
        # next will be confirmed only if another coherent low reading follows
        self.assertTrue(d.observe(32))

class TestRed(unittest.TestCase):
    def test_red_takes_priority_over_green(self):
        frame=np.zeros((48,48,3),dtype=np.uint8)
        frame[:,:]=[0,130,255] # orange: not red HSV threshold
        self.assertFalse(ns['red_idle_detected'](frame,.28))
        frame[:,:]=[30,30,245] # red RGB
        self.assertTrue(ns['red_idle_detected'](frame,.28))

    def test_ignores_decoration_and_no_calibration(self):
        frame=np.zeros((45,45,3),dtype=np.uint8)
        frame[:3,:,2]=255 # external border excluded
        self.assertFalse(ns['red_idle_detected'](frame,.2))
        self.assertEqual(ns['rect_overlap']([0,0,20,20],[30,0,10,10]),0)

class TestAges(unittest.TestCase):
    def test_lost_by_age_adds_up_to_total(self):
        t=ns['AgeIdleTracker'](25)
        t.observe('oscura',0);t.observe('oscura',0)
        t.observe('oscura',60)
        t.observe('feudal',61);t.observe('feudal',62)
        t.observe('feudal',150)
        r=t.snapshot()
        self.assertEqual(r['lost_total'],6)
        self.assertEqual(sum(r['lost_by_age'].values())+r['unassigned_lost'],6)
        self.assertEqual(sum(r['values'].values())+r['unassigned'],150)
        t.reset()
        r=t.snapshot()
        self.assertEqual(r['total'],0)
        self.assertEqual(r['lost_total'],0)

    def test_clock_freezes_during_pause(self):
        e=ns['ClockSynchronizedIdle']()
        e.sample([('TC',False)],True,199)
        e.sample([('TC',False)],True,201)
        a=e.sample([('TC',False)],True,201,paused=True)
        self.assertEqual(a['total'],2)
        for i in range(10):
            self.assertEqual(e.sample([('TC',False)],True,201,paused=True)['total'],2)
        e.sample([('TC',False)],True,201)
        self.assertEqual(e.sample([('TC',False)],True,202)['total'],3)

if __name__=='__main__':unittest.main()
