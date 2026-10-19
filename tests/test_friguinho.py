"""Asset contract for the Friguinho desktop pet."""
import unittest

from PIL import Image

from deskpets import config_io
from deskpets.pets import PETS_DATA


class FriguinhoAssetTests(unittest.TestCase):
    def test_catalog_has_complete_generic_state_set(self):
        self.assertEqual(PETS_DATA["friguinho"]["colors"], ["blue"])
        self.assertEqual(
            set(PETS_DATA["friguinho"]["states"]["blue"]),
            {"idle", "walk", "walk_fast", "run", "swipe", "lie", "drag"},
        )
        self.assertNotIn("physics", PETS_DATA["friguinho"])

    def test_cycles_have_consistent_canvas_transparency_and_motion(self):
        cycles = []
        for state, path in PETS_DATA["friguinho"]["states"]["blue"].items():
            with self.subTest(state=state), Image.open(config_io.BASE_DIR / path) as gif:
                self.assertEqual(gif.size, (128, 128))
                self.assertEqual(gif.n_frames, 8)
                self.assertEqual(gif.info["loop"], 0)
                frames = []
                duration = 0
                for index in range(gif.n_frames):
                    gif.seek(index)
                    frame = gif.convert("RGBA")
                    bounds = frame.getchannel("A").getbbox()
                    self.assertTrue(bounds)
                    self.assertTrue(2 <= bounds[0] < bounds[2] <= 126)
                    self.assertTrue(2 <= bounds[1] < bounds[3] <= 126)
                    self.assertEqual(frame.getpixel((0, 0))[3], 0)
                    duration += gif.info["duration"]
                    frames.append(frame.tobytes())
                self.assertEqual(duration, 1000)
                self.assertGreaterEqual(len(set(frames)), 6)
                cycles.append(b"".join(frames))
        self.assertEqual(len(set(cycles)), 7)


if __name__ == "__main__":
    unittest.main()
