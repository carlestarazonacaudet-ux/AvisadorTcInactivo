"""El pesquero queda fuera del cómputo aunque comparta la cola."""
import unittest

import cv2
import numpy as np

import avisador_v26 as app


class FishingShipQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scales = app.DEFAULTS['escalas']
        cls.models = app.load_fishing_ship_models(cls.scales)
        cls.villagers = app.load_templates()
        cls.technologies = app.load_technology_templates()
        ship = cv2.imread(str(app.BASE / 'FishingShipDE.webp'))
        cls.ship = cv2.resize(ship, (46, 46), interpolation=cv2.INTER_AREA)

    def test_ship_does_not_stop_idle_but_other_tc_production_does(self):
        clock = app.ClockSynchronizedIdleFiltered(25, 1)
        states = ((0, (0, 0, 0)), (39, (26, 145, 28)), (46, (26, 145, 28)),
                  (46, (8, 12, 165)))
        for tick, (extent, color) in enumerate(states, start=100):
            with self.subTest(extent=extent, color=color):
                queue = np.full((60, 160, 3), 16, dtype=np.uint8)
                ship = self.ship.copy()
                ship[:, :extent] = .28 * ship[:, :extent] + .72 * np.array(color)
                queue[6:52, 8:54] = ship
                self.assertTrue(app.fishing_ship_boxes(queue, self.models))
                active, _, _ = app.classify_queue_region(
                    queue, self.villagers, self.technologies, self.scales,
                    fishing_models=self.models)
                self.assertFalse(active)
                self.assertEqual(clock.sample([('TC', active)], True, tick)['total'], tick - 100)

                for _, model in (self.villagers[0], self.technologies[0]):
                    queue[6:52, 61:107] = model
                    self.assertTrue(app.classify_queue_region(
                        queue, self.villagers, self.technologies, self.scales,
                        fishing_models=self.models)[0])
