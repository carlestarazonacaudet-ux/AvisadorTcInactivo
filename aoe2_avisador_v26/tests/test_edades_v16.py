"""Tests autocontenidos del módulo de edades y sincronización, sin interfaz Windows."""
import ast
from pathlib import Path
import unittest
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
source = ROOT.joinpath('avisador_v26.py').read_text(encoding='utf-8')
program = ast.parse(source)
needed = {'shield_alpha_mask','score_shield_at_scale','age_shield_scores','load_age_signatures', 'detect_game_age'}
classes = {'AgeIdleTracker', 'ClockSynchronizedIdle'}
code = []
for node in program.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('AGE_ORDER','AGE_NAMES','AGE_IMAGES') for t in node.targets):
        # AGE_IMAGES refers to BASE; initialize BASE in test namespace.
        code.append(node)
    elif isinstance(node, ast.FunctionDef) and node.name in needed:
        code.append(node)
    elif isinstance(node, ast.ClassDef) and node.name in classes:
        code.append(node)
ns = {'cv2': cv2, 'np': np, 'BASE': ROOT}
exec(compile(ast.Module(body=code, type_ignores=[]), '<modulo_aislado>', 'exec'), ns)
Tracker = ns['AgeIdleTracker']
Engine = ns['ClockSynchronizedIdle']


class AgeDetectionTests(unittest.TestCase):
    def test_four_templates_recognized(self):
        templates = ns['load_age_signatures']()
        self.assertEqual(len(templates),4)
        for age in ns['AGE_ORDER']:
            original = cv2.imread(str(ROOT/'age_shields'/(age+'.png')))
            result, score = ns['detect_game_age'](original,templates)
            self.assertEqual(result,age)
            self.assertGreater(score, .9)

    def test_detection_when_roi_has_margins(self):
        signatures=ns['load_age_signatures']()
        for age in ns['AGE_ORDER']:
            raw=cv2.imread(str(ROOT/'age_shields'/(age+'.png')))
            canvas=np.zeros((raw.shape[0]+25,raw.shape[1]+32,3),dtype=np.uint8)
            canvas[11:11+raw.shape[0],17:17+raw.shape[1]]=raw
            found,score=ns['detect_game_age'](canvas,signatures)
            self.assertEqual(found,age)

    def test_blank_is_not_an_age(self):
        self.assertEqual(ns['detect_game_age'](np.zeros((40,250,3),dtype=np.uint8),
                     ns['load_age_signatures']())[0],None)

class AgeTrackerTests(unittest.TestCase):
    def confirm(self, tracker, stage, total):
        tracker.observe(stage,total)
        return tracker.observe(stage,total)

    def test_age_boundaries_and_total_consistency(self):
        a=Tracker()
        self.confirm(a,'oscura',0)
        self.assertEqual(a.observe('oscura',25)['values']['oscura'],25)
        a.observe('feudal',35)
        result=a.observe('feudal',36)
        self.assertEqual(result['values']['oscura'],36)
        self.assertEqual(result['values']['feudal'],0)
        a.observe('feudal',61)
        self.assertEqual(a.snapshot()['values']['feudal'],25)
        self.confirm(a,'castillos',61)
        a.observe('castillos',101)
        self.confirm(a,'imperial',101)
        a.observe('imperial',111)
        r=a.snapshot()
        self.assertEqual((r['values']['oscura'],r['values']['feudal'],
                          r['values']['castillos'],r['values']['imperial']),(36,25,40,10))
        self.assertEqual(sum(r['values'].values()),111)
        self.assertEqual(r['unassigned'],0)

    def test_pause_or_clock_frozen_adds_nothing(self):
        engine=Engine()
        tracker=Tracker()
        self.confirm(tracker,'oscura',0)
        engine.sample([('TC',False)],True,200)
        one=engine.sample([('TC',False)],True,201)
        tracker.observe('oscura',one['total'])
        for _ in range(30):
            shot=engine.sample([('TC',False)],True,201,paused=True)
            r=tracker.observe('oscura',shot['total'],clock_valid=False)
            self.assertEqual(r['values']['oscura'],1)
        engine.sample([('TC',False)],True,201)
        shot=engine.sample([('TC',False)],True,202)
        self.assertEqual(shot['total'],2)
        tracker.observe('oscura',shot['total'])
        self.assertEqual(tracker.snapshot()['values']['oscura'],2)

    def test_new_game_resets_ages(self):
        t=Tracker()
        self.confirm(t,'oscura',0)
        t.observe('oscura',77)
        t.reset()
        r=t.snapshot()
        self.assertEqual(sum(r['values'].values()),0)
        self.assertEqual(r['age'],None)
        self.assertEqual(r['seen'],[])

    def test_skipped_age_cannot_be_fabricated(self):
        a=Tracker()
        self.confirm(a,'castillos',25)
        a.observe('castillos',45)
        r=a.snapshot()
        self.assertEqual(r['values']['castillos'],20)
        self.assertEqual(r['values']['oscura'],0)
        self.assertNotIn('oscura',r['seen'])
        self.assertEqual(r['unassigned'],25)

    def test_no_age_regression_on_noisy_frame(self):
        a=Tracker()
        self.confirm(a,'feudal',0)
        self.confirm(a,'castillos',10)
        self.confirm(a,'feudal',20)
        self.assertEqual(a.snapshot()['age'],'castillos')

if __name__=='__main__':
    unittest.main(verbosity=2)
