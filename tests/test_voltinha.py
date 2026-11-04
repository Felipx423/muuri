"""Asset and catalog contract for the Voltinha desktop pet."""
import unittest

from PIL import Image

from deskpets import config_io
from deskpets.pets import PETS_DATA


class VoltinhaAssetTests(unittest.TestCase):
    def test_catalog_has_complete_generic_state_set(self):
        data = PETS_DATA["voltinha"]
        self.assertEqual(data["colors"], ["green"])
        self.assertEqual(
            set(data["states"]["green"]),
            {"idle", "walk", "walk_fast", "run", "swipe", "lie", "drag"},
        )
        self.assertNotIn("physics", data)

    def test_cycles_are_transparent_aligned_and_animated(self):
        cycles = []
        for state, path in PETS_DATA["voltinha"]["states"]["green"].items():
            with self.subTest(state=state), Image.open(config_io.BASE_DIR / path) as gif:
                self.assertEqual(gif.size, (128, 128))
                self.assertEqual(gif.n_frames, 8)
                self.assertEqual(gif.info["loop"], 0)
                frames, total = [], 0
                for index in range(gif.n_frames):
                    gif.seek(index)
                    frame = gif.convert("RGBA")
                    bounds = frame.getchannel("A").getbbox()
                    self.assertTrue(bounds)
                    self.assertTrue(2 <= bounds[0] < bounds[2] <= 126)
                    self.assertTrue(2 <= bounds[1] < bounds[3] <= 126)
                    self.assertEqual(frame.getpixel((0, 0))[3], 0)
                    total += gif.info["duration"]
                    frames.append(frame.tobytes())
                self.assertEqual(total, 1000)
                self.assertGreaterEqual(len(set(frames)), 6)
                cycles.append(b"".join(frames))
        self.assertEqual(len(set(cycles)), 7)

    def test_base_keeps_green_arrow_and_dark_face(self):
        path = PETS_DATA["voltinha"]["states"]["green"]["idle"]
        with Image.open(config_io.BASE_DIR / path) as gif:
            frame = gif.convert("RGBA")
        visible = [pixel for pixel in frame.getdata() if pixel[3]]
        green = sum(g > r * 1.15 and g > b * 1.05 for r, g, b, _ in visible)
        dark = sum(max(r, g) < 50 and b < 100 for r, g, b, _ in visible)
        self.assertGreater(green, len(visible) * .55)
        self.assertGreater(dark, 10)


if __name__ == "__main__":
    unittest.main()
