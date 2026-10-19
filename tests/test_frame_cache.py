import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from deskpets.remove_alpha import GifHelper


class ResizedGifCacheTests(unittest.TestCase):
    def setUp(self):
        GifHelper._frame_cache.clear()
        GifHelper._frame_cache_bytes = 0

    def tearDown(self):
        GifHelper._frame_cache.clear()
        GifHelper._frame_cache_bytes = 0

    def test_cache_hit_preserves_pixels_alpha_and_mirroring(self):
        source = Image.new("RGBA", (2, 4))
        source.putdata([
            (255, 0, 0, 255), (0, 255, 0, 128),
            (0, 0, 255, 0), (255, 255, 0, 64),
            (10, 20, 30, 255), (40, 50, 60, 255),
            (70, 80, 90, 255), (100, 110, 120, 255),
        ])
        expected = source.resize((1, 2), Image.Resampling.LANCZOS)
        with patch.object(GifHelper, "load_gif_frames", return_value=[source]) as loader:
            first = GifHelper.load_resized_gif_frames("media/sample.gif", 2)
            mirrored = first[0].transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            second = GifHelper.load_resized_gif_frames("media/sample.gif", 2)

        loader.assert_called_once_with("media/sample.gif")
        self.assertEqual(first[0].tobytes(), expected.tobytes())
        self.assertEqual(first[0].getchannel("A").tobytes(), expected.getchannel("A").tobytes())
        self.assertEqual(mirrored.tobytes(), expected.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes())
        self.assertEqual(second[0].tobytes(), expected.tobytes())
        self.assertIsNot(first, second)

    def test_lru_evicts_oldest_entry_and_stays_within_pixel_budget(self):
        image = Image.new("RGBA", (2, 2), (20, 30, 40, 128))
        GifHelper.FRAME_CACHE_LIMIT_BYTES = 32
        try:
            with patch.object(GifHelper, "load_gif_frames", return_value=[image]):
                retained = GifHelper.load_resized_gif_frames("media/a.gif", 2)
                GifHelper.load_resized_gif_frames("media/b.gif", 2)
                GifHelper.load_resized_gif_frames("media/a.gif", 2)  # a becomes most recent
                GifHelper.load_resized_gif_frames("media/c.gif", 2)

            self.assertEqual(len(GifHelper._frame_cache), 2)
            self.assertEqual(GifHelper._frame_cache_bytes, 32)
            self.assertTrue(any(key[0].endswith("a.gif") for key in GifHelper._frame_cache))
            self.assertTrue(any(key[0].endswith("c.gif") for key in GifHelper._frame_cache))
            self.assertFalse(any(key[0].endswith("b.gif") for key in GifHelper._frame_cache))
            self.assertEqual(retained[0].getpixel((0, 0)), (20, 30, 40, 128))
        finally:
            GifHelper.FRAME_CACHE_LIMIT_BYTES = 64 * 1024 * 1024

    def test_oversized_animation_is_returned_but_not_cached(self):
        image = Image.new("RGBA", (2, 2), (1, 2, 3, 255))
        GifHelper.FRAME_CACHE_LIMIT_BYTES = 15
        try:
            with patch.object(GifHelper, "load_gif_frames", return_value=[image]):
                frames = GifHelper.load_resized_gif_frames("media/large.gif", 2)
            self.assertEqual(frames[0].size, (2, 2))
            self.assertEqual(frames[0].getpixel((1, 1)), (1, 2, 3, 255))
            self.assertEqual(GifHelper._frame_cache_bytes, 0)
            self.assertFalse(GifHelper._frame_cache)
        finally:
            GifHelper.FRAME_CACHE_LIMIT_BYTES = 64 * 1024 * 1024

    def test_platform_orientation_is_part_of_cache_key(self):
        image = Image.new("RGBA", (2, 2), (1, 2, 3, 255))
        with patch.object(GifHelper, "load_gif_frames", return_value=[image]) as loader:
            with patch("deskpets.remove_alpha.sys.platform", "win32"):
                GifHelper.load_resized_gif_frames("media/oriented.gif", 2)
            with patch("deskpets.remove_alpha.sys.platform", "darwin"):
                GifHelper.load_resized_gif_frames("media/oriented.gif", 2)
        self.assertEqual(loader.call_count, 2)
        self.assertEqual(len(GifHelper._frame_cache), 2)


class IdleTimerOptimizationTests(unittest.TestCase):
    def test_drag_and_physics_updates_skip_inactive_pets(self):
        from deskpets.window import MainWindow

        idle = SimpleNamespace(draggable=True, settings_clicks=4, mouse_pressed=False,
                               dragging=False, physics_enabled=False)
        dragged = SimpleNamespace(draggable=True, settings_clicks=4, mouse_pressed=True,
                                  dragging=True, physics_enabled=True)
        physics_only = SimpleNamespace(draggable=False, settings_clicks=0, mouse_pressed=False,
                                       dragging=False, physics_enabled=True)
        owner = SimpleNamespace(pets=[idle, dragged, physics_only], last_physics_update=10.0)
        with patch("deskpets.window.time.monotonic", return_value=10.016), \
             patch("deskpets.window.Desktop.update_drag") as update_drag, \
             patch("deskpets.window.Desktop.update_physics") as update_physics:
            MainWindow.update_drag(owner)

        update_drag.assert_called_once_with(dragged)
        self.assertEqual(update_physics.call_count, 2)
        update_physics.assert_any_call(dragged, 0.016000000000000014)
        update_physics.assert_any_call(physics_only, 0.016000000000000014)


if __name__ == "__main__":
    unittest.main()
