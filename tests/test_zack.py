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


if __name__ == "__main__":
    unittest.main()
