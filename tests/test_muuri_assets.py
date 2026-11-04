import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

from deskpets.pets import PETS_DATA, Pet, states_for
from deskpets.remove_alpha import GifHelper
from deskpets.state import State


ASSET = Path(__file__).resolve().parents[1] / "deskpets/media/muuri/blue_drag_8fps.gif"


class SmoothStyleTests(unittest.TestCase):
    def test_cursor_rest_keeps_selected_style(self):
        for style in ("pixel", "smooth"):
            with self.subTest(style=style):
                pet = SimpleNamespace(
                    species="muuri", color="blue", style=style,
                    mouse_pressed=False, dragging=False, physics_enabled=False,
                    wall_scene_step=None, drag_previous_state=None, settings_clicks=0,
                    x=800, y=100, height_lie=128, immunity=False, lie_duration=24,
                    free_roam=False, screen_width=1000, width=160,
                    state=State("idle", states_for("muuri", "blue", style)["idle"]),
                    frame_animation=Mock(),
                )
                with patch("deskpets.pets.Desktop.cursor_position", return_value=(800, 100)):
                    Pet.update_state(pet)
                self.assertEqual(pet.state.name, "lie")
                self.assertEqual(pet.state.gif, states_for("muuri", "blue", style)["lie"])
                pet.frame_animation.assert_called_once()

    def test_smooth_cycles_keep_real_alpha_and_original_canvas(self):
        root = ASSET.parent.parent.parent
        paths = states_for("muuri", "blue", "smooth")
        self.assertEqual(set(paths), set(PETS_DATA["muuri"]["states"]["blue"]))
        for state, path in paths.items():
            with self.subTest(state=state), Image.open(root / path) as animation:
                self.assertEqual(animation.format, "PNG")
                self.assertEqual(animation.size, (160, 128))
                self.assertEqual(animation.n_frames, 8)
                self.assertEqual(animation.info["loop"], 0)
                frames = []
                for index in range(animation.n_frames):
                    animation.seek(index)
                    frame = animation.convert("RGBA")
                    frames.append(frame.tobytes())
                    alpha = frame.getchannel("A")
                    left, top, right, bottom = alpha.getbbox()
                    self.assertTrue(0 < left < right < 160 and 0 < top < bottom < 128)
                    self.assertGreater(sum(alpha.histogram()[1:255]), 100)
                    self.assertEqual(animation.info["duration"], 125)
                    raw = frame.tobytes()
                    green = sum(a >= 250 and g > r * 1.4 and g > b * 1.2
                                for r, g, b, a in zip(raw[0::4], raw[1::4], raw[2::4], raw[3::4]))
                    self.assertGreater(green, 25, f"Missing opaque tail in {state}/{index}")
                self.assertGreater(len(set(frames)), 1, "Animation must move")

    def test_smooth_apng_loads_upright_and_mirrored_on_both_backends(self):
        root = ASSET.parent.parent.parent
        for platform in ("win32", "darwin"):
            for state, path in states_for("muuri", "blue", "smooth").items():
                with self.subTest(platform=platform, state=state):
                    with patch("deskpets.remove_alpha.sys", SimpleNamespace(platform=platform)):
                        actual = GifHelper.load_resized_gif_frames(path)
                    with Image.open(root / path) as source:
                        self.assertEqual(len(actual), source.n_frames)
                        for index, frame in enumerate(actual):
                            source.seek(index)
                            expected = source.convert("RGBA")
                            if platform == "win32":
                                expected = expected.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                            self.assertEqual(frame.tobytes(), expected.tobytes())
                            mirrored = frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                            self.assertEqual(mirrored.getchannel("A").histogram(),
                                             expected.getchannel("A").histogram())


class DragAssetTests(unittest.TestCase):
    def test_green_tail_is_opaque_in_every_frame(self):
        with Image.open(ASSET) as gif:
            for index in range(gif.n_frames):
                gif.seek(index)
                frame = gif.convert("RGBA")
                green = 0
                # The 2x canvas moves the same tail pixels into the first 48 columns.
                for y in range(frame.height):
                    for x in range(48):
                        red, value, blue, alpha = frame.getpixel((x, y))
                        if alpha == 255 and value >= 80 and value > red * 1.4 and value > blue * 1.2:
                            green += 1
                # The broken chroma-key conversion left only a thin green outline.
                self.assertGreaterEqual(green, 25, f"Transparent tail in frame {index}")

    def test_canvas_transparent_margins_and_timing(self):
        with Image.open(ASSET) as gif:
            self.assertEqual(gif.n_frames, 8)
            self.assertEqual(gif.size, (160, 128))
            self.assertEqual(gif.info["loop"], 0)
            for index in range(8):
                gif.seek(index)
                self.assertEqual(gif.info["duration"], 120 if index % 2 == 0 else 130)
                self.assertEqual(gif.disposal_method, 2)
                frame = gif.convert("RGBA")
                left, top, right, bottom = frame.getbbox()
                self.assertTrue(0 < left < right < 160 and 0 < top < bottom < 128)
                self.assertEqual(frame.getpixel((0, 0))[3], 0)


if __name__ == "__main__":
    unittest.main()
