import unittest
from types import SimpleNamespace
from unittest.mock import patch

from deskpets.clicks import ClickSequence
from deskpets.physics import Motion


def pet(enabled=True):
    return SimpleNamespace(physics_enabled=enabled, mouse_pressed=False, dragging=False,
                           wall_scene_step=None, settings_clicks=4, click_sequence=ClickSequence(),
                           x=200.0, y=100.0, y_def=100.0, floor_y=600, screen_height=664,
                           height=64, width=80, screen_width=1000, free_roam=True)


class PhysicsTests(unittest.TestCase):
    def test_disabled_keeps_drop_position(self):
        motion, body = Motion(), pet(False)
        motion.vx, motion.vy = 1000, 1000
        self.assertFalse(motion.advance(body, 0.016))
        self.assertEqual((body.x, body.y, motion.vx, motion.vy), (200, 100, 0, 0))

    def test_gravity_lands_on_taskbar_floor_and_settles(self):
        motion, body = Motion(), pet()
        motion.advance(body, 0.016)
        self.assertGreater(body.y, 100)
        bounced = False
        for _ in range(500):
            motion.advance(body, 0.016)
            bounced |= motion.vy < 0
            self.assertLessEqual(body.y, body.floor_y)
        self.assertTrue(bounced)
        self.assertEqual((body.y, body.y_def, motion.vy), (600, 600, 0))

    def test_throw_uses_recent_pointer_velocity_and_is_bounded(self):
        motion = Motion()
        motion.begin(100, 200, 10)
        motion.track(150, 170, 10.05)
        motion.launch(10.06)
        self.assertAlmostEqual(motion.vx, 1000)
        self.assertAlmostEqual(motion.vy, -600)
        body = pet()
        motion.advance(body, 0.016)
        self.assertGreater(body.x, 200)
        self.assertLess(body.y, 100)
        motion.begin(0, 0, 20)
        motion.track(10000, -10000, 20.01)
        motion.launch(20.02)
        self.assertEqual((motion.vx, motion.vy), (1400, -1400))

    def test_stationary_or_old_release_does_not_throw(self):
        motion = Motion()
        motion.begin(0, 0, 1)
        motion.track(100, 0, 1.05)
        motion.launch(1.3)
        self.assertEqual((motion.vx, motion.vy), (0, 0))
        motion.begin(100, 100, 2)
        motion.track(100, 100, 2.05)
        motion.launch(2.06)
        self.assertEqual((motion.vx, motion.vy), (0, 0))

    def test_bounds_collide_and_floor_friction_stops_slide(self):
        motion, body = Motion(), pet()
        body.x, body.y = 919, 1
        motion.vx, motion.vy = 1400, -1400
        motion.advance(body, 0.016)
        self.assertTrue(0 <= body.x <= 920 and 0 <= body.y <= 600)
        self.assertLess(motion.vx, 0)
        self.assertGreater(motion.vy, 0)
        body.y = body.floor_y
        motion.vy = 0
        for _ in range(100):
            motion.advance(body, 0.016)
        self.assertEqual(motion.vx, 0)

    def test_drag_and_four_clicks_pause_then_resume_gravity(self):
        motion, body = Motion(), pet()
        body.mouse_pressed = True
        self.assertFalse(motion.advance(body, 0.016))
        body.mouse_pressed = False
        body.click_sequence.press((0, 0), 10)
        body.click_sequence.release((0, 0), 10.01)
        with patch("deskpets.physics.time.monotonic", return_value=10.5):
            self.assertFalse(motion.advance(body, 0.016))
        with patch("deskpets.physics.time.monotonic", return_value=12):
            self.assertTrue(motion.advance(body, 0.016))
        self.assertEqual(body.click_sequence.count, 0)

    def test_simulation_is_stable_across_frame_rates(self):
        outcomes = []
        for elapsed in (1/120, 1/60, 1/30):
            motion, body = Motion(), pet()
            motion.vx = 600
            for _ in range(round(0.3/elapsed)):
                motion.advance(body, elapsed)
            outcomes.append((body.x, body.y))
        self.assertLess(max(x for x, y in outcomes)-min(x for x, y in outcomes), 10)
        self.assertLess(max(y for x, y in outcomes)-min(y for x, y in outcomes), 10)


if __name__ == "__main__":
    unittest.main()
