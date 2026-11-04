"""Asset and catalog contract for the Zack desktop pet."""
import unittest

from PIL import Image

from deskpets import config_io
from deskpets.pets import PETS_DATA


class ZackAssetTests(unittest.TestCase):
    def test_catalog_has_complete_generic_state_set(self):
        data = PETS_DATA["zack"]
        self.assertEqual(data["colors"], ["cream"])
        self.assertEqual(
            set(data["states"]["cream"]),
            {"idle", "walk", "walk_fast", "run", "swipe", "lie", "drag"},
        )
        self.assertNotIn("physics", data)

    def test_cycles_are_transparent_aligned_and_animated(self):
        cycles = []
        for state, path in PETS_DATA["zack"]["states"]["cream"].items():
            with self.subTest(state=state), Image.open(config_io.BASE_DIR / path) as animation:
                self.assertEqual(animation.size, (128, 128))
                self.assertEqual(animation.n_frames, 8)
                self.assertEqual(animation.info["loop"], 0)
                frames, duration = [], 0
                for index in range(animation.n_frames):
                    animation.seek(index)
                    frame = animation.convert("RGBA")
                    bounds = frame.getchannel("A").getbbox()
                    self.assertTrue(bounds)
                    self.assertTrue(0 < bounds[0] < bounds[2] < 128)
                    self.assertTrue(0 < bounds[1] < bounds[3] < 128)
                    self.assertEqual(frame.getpixel((0, 0))[3], 0)
                    duration += animation.info["duration"]
                    frames.append(frame.tobytes())
                self.assertEqual(duration, 1000)
                self.assertGreaterEqual(len(set(frames)), 6)
                cycles.append(b"".join(frames))
        self.assertEqual(len(set(cycles)), 7)

    def test_locomotion_base_faces_right_and_mirrors_left(self):
        """The visible side module stays behind Zack's right-facing head."""
        for state in ("walk", "walk_fast", "run"):
            path = PETS_DATA["zack"]["states"]["cream"][state]
            with self.subTest(state=state), Image.open(config_io.BASE_DIR / path) as animation:
                for index in range(animation.n_frames):
                    animation.seek(index)
                    frame = animation.convert("RGBA")
                    green_x = [
                        x
                        for y in range(25, 70)
                        for x in range(frame.width)
                        if (lambda r, g, b, a: a > 100 and g > 110 and g > r * 1.2 and g > b * 0.9)(
                            *frame.getpixel((x, y))
                        )
                    ]
                    self.assertTrue(green_x)
                    self.assertLess(sum(green_x) / len(green_x), frame.width / 2)

    def test_drag_has_real_transparency_without_a_square_backdrop(self):
        path = PETS_DATA["zack"]["states"]["cream"]["drag"]
        with Image.open(config_io.BASE_DIR / path) as animation:
            for index in range(animation.n_frames):
                animation.seek(index)
                alpha = animation.convert("RGBA").getchannel("A")
                inset = 12
                border = (
                    [(x, inset) for x in range(inset, alpha.width - inset)]
                    + [(x, alpha.height - inset - 1) for x in range(inset, alpha.width - inset)]
                    + [(inset, y) for y in range(inset, alpha.height - inset)]
                    + [(alpha.width - inset - 1, y) for y in range(inset, alpha.height - inset)]
                )
                transparent = sum(alpha.getpixel(point) == 0 for point in border)
                self.assertGreater(transparent / len(border), 0.8)


if __name__ == "__main__":
    unittest.main()
