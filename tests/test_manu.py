import unittest

from PIL import Image

from deskpets import config_io
from deskpets.pets import PETS_DATA


class ManuAssetTests(unittest.TestCase):
    def test_seven_128px_cycles_keep_transparency_margins_and_motion(self):
        data = PETS_DATA['manu']
        states = {'idle', 'walk', 'walk_fast', 'run', 'swipe', 'lie', 'drag'}
        self.assertEqual(data['colors'], ['blue'])
        self.assertEqual(set(data['states']['blue']), states)
        cycles = set()
        for state, path in data['states']['blue'].items():
            with self.subTest(state=state), Image.open(config_io.BASE_DIR/path) as gif:
                self.assertEqual(gif.size, (128, 128))
                self.assertEqual(gif.n_frames, 8)
                self.assertEqual(gif.info['loop'], 0)
                frames = []
                duration = 0
                for index in range(gif.n_frames):
                    gif.seek(index)
                    frame = gif.convert('RGBA')
                    left, top, right, bottom = frame.getchannel('A').getbbox()
                    self.assertTrue(0 < left < right < 128 and 0 < top < bottom < 128)
                    self.assertEqual(frame.getpixel((0, 0))[3], 0)
                    self.assertEqual(gif.disposal_method, 2)
                    duration += gif.info['duration']
                    frames.append(frame.tobytes())
                self.assertEqual(duration, 1000)
                self.assertGreater(len(set(frames)), 3)
                cycles.add(b''.join(frames))
        self.assertEqual(len(cycles), 7)
