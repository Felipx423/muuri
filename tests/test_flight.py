import math
import unittest
from types import SimpleNamespace

from deskpets.clicks import ClickSequence
from deskpets.pets import PETS_DATA
from deskpets.physics import Motion


def body():
    return SimpleNamespace(physics_enabled=True, mouse_pressed=False, dragging=False,
                           wall_scene_step=None, settings_clicks=0, click_sequence=ClickSequence(),
                           x=400.0, y=100.0, y_def=100.0, floor_y=600, screen_height=728,
                           height=128, width=128, screen_width=2000, free_roam=True)


class FlightPhysicsTests(unittest.TestCase):
    def setUp(self):
        self.profile = PETS_DATA["fefo"]["physics"]

    def test_default_drop_matches_previous_muuri_physics(self):
        self.assertNotIn("physics", PETS_DATA["muuri"])
        motion, pet = Motion(), body()
        expected = {15: (160, 450), 30: (332.5, 900),
                    60: (575.625, 112.5), 180: (600, 0)}
        for step in range(1, 181):
            motion.advance(pet, 1/60)
            if step in expected:
                self.assertAlmostEqual(pet.y, expected[step][0])
                self.assertAlmostEqual(motion.vy, expected[step][1])

    def test_fefo_falls_slower_has_more_air_drag_and_lands_without_bounce(self):
        light, heavy = Motion(self.profile), Motion()
        fefo, muuri = body(), body()
        light.vx = heavy.vx = 600
        for _ in range(60):
            light.advance(fefo, 1/60)
            heavy.advance(muuri, 1/60)
            self.assertLessEqual(light.vy, self.profile["max_fall_speed"])
        self.assertLess(fefo.y, muuri.y-200)
        self.assertLess(light.vx, heavy.vx)
        for _ in range(600):
            light.advance(fefo, 1/60)
            self.assertGreaterEqual(light.vy, 0)
        self.assertEqual((fefo.y, light.vx, light.vy), (600, 0, 0))

    def test_horizontal_speed_supports_gliding_and_caps_downward_throw(self):
        glide, fall = Motion(self.profile), Motion(self.profile)
        flying, dropping = body(), body()
        glide.vx = 800
        glide.vy = fall.vy = 1400
        glide.advance(flying, 1/60)
        fall.advance(dropping, 1/60)
        self.assertLess(glide.vy, fall.vy)
        self.assertLess(flying.y, dropping.y)
        self.assertLessEqual(fall.vy, 180)

    def test_horizontal_toss_from_floor_gets_lift_but_stationary_release_does_not(self):
        motion, pet = Motion(self.profile), body()
        pet.y = pet.floor_y
        motion.begin(0, 0, 10)
        motion.track(50, 0, 10.05)
        motion.launch(10.06)
        self.assertAlmostEqual(motion.vx, 850)
        self.assertEqual(motion.vy, -180)
        motion.advance(pet, 1/60)
        self.assertLess(pet.y, pet.floor_y)
        motion.begin(50, 0, 11)
        motion.track(50, 0, 11.05)
        motion.launch(11.06)
        self.assertEqual((motion.vx, motion.vy), (0, 0))

    def test_disabled_physics_and_drag_pause_flight(self):
        motion, pet = Motion(self.profile), body()
        motion.vx, motion.vy = 600, -180
        pet.dragging = True
        self.assertFalse(motion.advance(pet, 0.016))
        self.assertEqual((pet.x, pet.y, motion.vx, motion.vy), (400, 100, 600, -180))
        pet.dragging = False
        pet.physics_enabled = False
        self.assertFalse(motion.advance(pet, 0.016))
        self.assertEqual((pet.x, pet.y, motion.vx, motion.vy), (400, 100, 0, 0))

    def test_flight_remains_stable_across_frame_rates(self):
        outcomes = []
        for dt in (1/120, 1/60, 1/30):
            motion, pet = Motion(self.profile), body()
            motion.vx, motion.vy = 600, -180
            for _ in range(round(1/dt)):
                motion.advance(pet, dt)
                self.assertTrue(math.isfinite(pet.x) and math.isfinite(pet.y))
                self.assertTrue(0 <= pet.y <= pet.floor_y)
            outcomes.append((pet.x, pet.y))
        self.assertLess(max(x for x, y in outcomes)-min(x for x, y in outcomes), 10)
        self.assertLess(max(y for x, y in outcomes)-min(y for x, y in outcomes), 10)


if __name__ == "__main__":
    unittest.main()
