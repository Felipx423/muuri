import unittest
from pathlib import Path

from PIL import Image


ASSET = Path(__file__).resolve().parents[1] / "deskpets/media/muuri/blue_drag_8fps.gif"


class DragAssetTests(unittest.TestCase):
    def test_green_tail_is_opaque_in_every_frame(self):
        with Image.open(ASSET) as gif:
            for index in range(gif.n_frames):
                gif.seek(index)
                frame = gif.convert("RGBA")
                green = 0
                for y in range(frame.height):
                    for x in range(24):
                        red, value, blue, alpha = frame.getpixel((x, y))
                        if alpha == 255 and value >= 80 and value > red * 1.4 and value > blue * 1.2:
                            green += 1
                # The broken chroma-key conversion left only a thin green outline.
                self.assertGreaterEqual(green, 25, f"Transparent tail in frame {index}")

    def test_canvas_transparent_margins_and_timing(self):
        with Image.open(ASSET) as gif:
            self.assertEqual(gif.n_frames, 8)
            self.assertEqual(gif.size, (80, 64))
            self.assertEqual(gif.info["loop"], 0)
            for index in range(8):
                gif.seek(index)
                self.assertEqual(gif.info["duration"], 120 if index % 2 == 0 else 130)
                self.assertEqual(gif.disposal_method, 2)
                frame = gif.convert("RGBA")
                left, top, right, bottom = frame.getbbox()
                self.assertTrue(0 < left < right < 80 and 0 < top < bottom < 64)
                self.assertEqual(frame.getpixel((0, 0))[3], 0)


if __name__ == "__main__":
    unittest.main()
