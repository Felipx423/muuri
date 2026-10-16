"""Asset contract: Eco must stay transparent with four separate floating limbs."""
from collections import deque
import unittest

from PIL import Image

from deskpets import config_io
from deskpets.pets import PETS_DATA


def visible_parts(alpha):
    width, height = alpha.size
    remaining = {index for index, value in enumerate(alpha.tobytes()) if value}
    sizes = []
    while remaining:
        start = remaining.pop()
        queue, size = deque([start]), 0
        while queue:
            p = queue.popleft()
            size += 1
            x, y = p % width, p // width
            for neighbor in (p-1 if x else -1, p+1 if x+1 < width else -1,
                             p-width if y else -1, p+width if y+1 < height else -1):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
        if size >= 12:
            sizes.append(size)
    return len(sizes)


class EcoAssetTests(unittest.TestCase):
    def test_cycles_preserve_canvas_timing_gaps_and_motion(self):
        data = PETS_DATA['eco']
        states = data['states']['green']
        self.assertEqual(set(states), {'idle','walk','walk_fast','run','swipe','lie','drag'})
        cycles = set()
        for state, path in states.items():
            with self.subTest(state=state), Image.open(config_io.BASE_DIR/path) as gif:
                self.assertEqual(gif.size, (128,128))
                self.assertEqual(gif.n_frames, 8)
                self.assertEqual(gif.info['loop'], 0)
                frames, duration = [], 0
                for index in range(gif.n_frames):
                    gif.seek(index)
                    frame = gif.convert('RGBA')
                    alpha = frame.getchannel('A')
                    left, top, right, bottom = alpha.getbbox()
                    self.assertTrue(3 <= left < right <= 125 and 3 <= top < bottom <= 125)
                    if state in ('walk','walk_fast','run'):
                        # The far foot may be occluded by the near foot in side
                        # view. Both floating hands must stay separate from body.
                        self.assertIn(visible_parts(alpha), (4,5), (state,index))
                    else:
                        self.assertEqual(visible_parts(alpha), 5, (state,index))
                    self.assertEqual(frame.getpixel((0,0))[3], 0)
                    self.assertEqual(gif.disposal_method, 2)
                    duration += gif.info['duration']
                    frames.append(frame.tobytes())
                self.assertEqual(duration, 1000)
                self.assertGreater(len(set(frames)), 3)
                cycles.add(b''.join(frames))
        self.assertEqual(len(cycles), 7)

    def test_locomotion_face_points_right_and_mirrors_left(self):
        for state in ('walk','walk_fast','run'):
            path = PETS_DATA['eco']['states']['green'][state]
            with self.subTest(state=state), Image.open(config_io.BASE_DIR/path) as gif:
                for index in range(gif.n_frames):
                    gif.seek(index)
                    frame = gif.convert('RGBA')
                    def eye_center(image):
                        xs = [i % image.width for i, (r,g,b,a) in enumerate(image.getdata())
                              if a and b > r*1.18 and b > g*1.04]
                        self.assertTrue(xs)
                        return sum(xs)/len(xs)
                    # A frontal sprite would place the eyes near the center.
                    self.assertGreater(eye_center(frame), frame.width/2+10)
                    self.assertLess(eye_center(frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)), frame.width/2-10)
