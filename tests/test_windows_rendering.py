import unittest

from PIL import Image

from deskpets.remove_alpha import GifHelper


class PremultipliedBgraTests(unittest.TestCase):
    def test_channel_order_alpha_and_vertical_orientation(self):
        image = Image.new("RGBA", (1, 2))
        image.putpixel((0, 0), (200, 100, 50, 128))
        image.putpixel((0, 1), (17, 33, 65, 0))

        data = GifHelper._premultiplied_bgra(image)

        self.assertEqual(len(data), 8)
        # The bitmap conversion flips vertically; fully transparent RGB is zeroed
        # by Pillow's premultiplied mode.
        self.assertEqual(tuple(data[:4]), (0, 0, 0, 0))
        self.assertEqual(tuple(data[4:]), (25, 50, 100, 128))

    def test_native_conversion_matches_floor_premultiplication_within_one(self):
        image = Image.new("RGBA", (17, 13))
        image.putdata([
            ((x * 29) % 256, (y * 47) % 256, ((x + y) * 31) % 256,
             (x * 19 + y * 23) % 256)
            for y in range(image.height)
            for x in range(image.width)
        ])

        actual = GifHelper._premultiplied_bgra(image)
        expected = bytearray()
        for y in reversed(range(image.height)):
            for x in range(image.width):
                r, g, b, a = image.getpixel((x, y))
                expected.extend((b * a // 255, g * a // 255,
                                 r * a // 255, a))

        for offset in range(0, len(actual), 4):
            self.assertEqual(actual[offset + 3], expected[offset + 3])
            for channel in range(3):
                self.assertLessEqual(abs(actual[offset + channel] -
                                         expected[offset + channel]), 1)


if __name__ == "__main__":
    unittest.main()
