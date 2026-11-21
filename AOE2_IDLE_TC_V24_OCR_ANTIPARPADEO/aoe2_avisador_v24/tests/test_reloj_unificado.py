"""No importa librerías de Windows; comprueba el contador puro y el reinicio."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).parents[1].joinpath('avisador_v24.py').read_text(encoding='utf-8')
tree = ast.parse(SOURCE)
nodes = [n for n in tree.body if isinstance(n, ast.ClassDef) and
         n.name in ('ClockSynchronizedIdle', 'MatchClockResetDetector')]
namespace = {}
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<aislado>', 'exec'), namespace)
Engine = namespace['ClockSynchronizedIdle']
Reset = namespace['MatchClockResetDetector']


class TestClockSynchronizedIdle(unittest.TestCase):
    def sample(self, engine, sec, active=False, tick=True, paused=False, name='TC1'):
        return engine.sample([(name,active)], clock_read=tick, game_seconds=sec,paused=paused)

    def test_synchronization_and_sound_alert(self):
        engine=Engine(25)
        self.sample(engine,100)
        for sec in range(101,178):
            snap=self.sample(engine,sec)
            self.assertEqual(snap['idle'],snap['total'])
            self.assertEqual(snap['lost'],snap['idle']//25)
        self.assertEqual(snap['idle'],77)
        self.assertEqual(snap['lost'],3)
        self.sample(engine,177,active=True)
        snap=self.sample(engine,178,active=True)
        self.assertEqual(snap['idle'],0)
        self.assertEqual(snap['total'],77)
        self.sample(engine,178,active=False)
        snap=self.sample(engine,179,active=False)
        self.assertEqual(snap['idle'],1)
        self.assertEqual(snap['total'],78)

    def test_no_idle_during_pause_or_frozen_game_clock(self):
        e=Engine()
        self.sample(e,100)
        self.sample(e,101)
        for _ in range(10):
            snap=self.sample(e,101)
            self.assertEqual((snap['idle'],snap['total']),(1,1))
        for _ in range(10):
            snap=self.sample(e,101,paused=True)
            self.assertEqual((snap['idle'],snap['total']),(1,1))
        snap=self.sample(e,101)
        self.assertEqual(snap['total'],1)
        snap=self.sample(e,102)
        self.assertEqual((snap['idle'],snap['total']),(2,2))

    def test_unreadable_clock_no_estimation(self):
        e=Engine()
        self.sample(e,10)
        self.sample(e,11)
        snap=self.sample(e,None)
        self.assertFalse(snap['clock_ok'])
        self.assertEqual(snap['total'],1)
        snap=self.sample(e,13)
        self.assertEqual(snap['total'],1)
        self.assertEqual(self.sample(e,14)['total'],2)

    def test_outlier_ignored(self):
        e=Engine()
        self.sample(e,20)
        self.sample(e,21)
        self.assertEqual(self.sample(e,99)['total'],1)
        self.assertEqual(self.sample(e,22)['total'],1)
        self.assertEqual(self.sample(e,23)['total'],2)

    def test_multiple_centers_and_reset(self):
        e=Engine()
        def snap(sec,a,b): return e.sample([('TC1',a),('TC2',b)], True, sec)
        snap(100,False,False)
        s=snap(101,False,False)
        self.assertEqual((s['idle'],s['total']),(1,2))
        s=snap(102,True,False)
        self.assertEqual((s['idle'],s['total']),(2,3))
        snap(103,True,True)
        self.assertEqual(e.total_seconds,3)
        e.reset()
        self.assertEqual(snap(0,False,False)['total'],0)
        self.assertEqual(snap(1,False,False)['total'],2)

    def test_reset_only_accumulated(self):
        e=Engine()
        self.sample(e,1)
        self.sample(e,2)
        e.reset_accumulated()
        s=self.sample(e,3)
        self.assertEqual(s['idle'],2)
        self.assertEqual(s['total'],1)

    def test_not_advanced_between_ocr(self):
        e=Engine()
        self.sample(e,80)
        for _ in range(100):
            s=self.sample(e,None,tick=False)
        self.assertEqual(s['total'],0)
        self.assertEqual(self.sample(e,81)['total'],1)

    def test_new_game_confirmed(self):
        r=Reset()
        self.assertFalse(r.observe(34))
        self.assertFalse(r.observe(36))
        self.assertFalse(r.observe(0))
        self.assertTrue(r.observe(1))
        self.assertFalse(r.observe(2))

if __name__ == '__main__':
    unittest.main(verbosity=2)
