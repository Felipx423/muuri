import ctypes
import os
import traceback
import sys
from collections import OrderedDict

from PIL import Image

if sys.platform == "win32":
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32


class GifHelper:
    FRAME_CACHE_LIMIT_BYTES = 64 * 1024 * 1024
    _frame_cache = OrderedDict()
    _frame_cache_bytes = 0

    @classmethod
    def load_resized_gif_frames(cls, path, target_height=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.realpath(os.path.join(base_dir, path))
        key = (absolute_path, target_height, sys.platform == "win32")
        cached = cls._frame_cache.get(key)
        if cached is not None:
            cls._frame_cache.move_to_end(key)
            return list(cached)

        frames = cls.load_gif_frames(path)
        if not frames:
            return frames

        resized_frames = []
        for frame in frames:
            height = target_height if target_height is not None else frame.height
            width = int(frame.width * height / frame.height)
            resized_frames.append(frame.resize((width, height), Image.Resampling.LANCZOS))

        cache_entry = tuple(resized_frames)
        entry_bytes = sum(frame.width * frame.height * 4 for frame in cache_entry)
        if entry_bytes <= cls.FRAME_CACHE_LIMIT_BYTES:
            while (cls._frame_cache and
                   cls._frame_cache_bytes + entry_bytes > cls.FRAME_CACHE_LIMIT_BYTES):
                _, evicted = cls._frame_cache.popitem(last=False)
                cls._frame_cache_bytes -= sum(frame.width * frame.height * 4 for frame in evicted)
            cls._frame_cache[key] = cache_entry
            cls._frame_cache_bytes += entry_bytes

        return list(cache_entry)

    @staticmethod
    def _premultiplied_bgra(frame: Image.Image) -> bytes:
        """Return top-down premultiplied BGRA bytes for a Windows DIB."""
        rgba = frame.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        return rgba.convert("RGBa").tobytes("raw", "BGRa")

    @staticmethod
    def load_gif_frames(path):
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            abs_path = os.path.join(base_dir, path)
            frames = []
            with Image.open(abs_path) as img:
                try:
                    while True:
                        frame = img.convert("RGBA")
                        if sys.platform == "win32":
                            frame = frame.transpose(Image.FLIP_TOP_BOTTOM)
                        frames.append(frame)
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass
            return frames
        except Exception as e:
            print(e)
            traceback.print_exc()

    @staticmethod
    def pil_to_hbitmap(frame: Image.Image):
        try:
            raw_data = GifHelper._premultiplied_bgra(frame)
            width, height = frame.size
            raw_buffer = (ctypes.c_ubyte * len(raw_data)).from_buffer_copy(raw_data)

            hdc = user32.GetDC(None)
            hdc_mem = gdi32.CreateCompatibleDC(hdc)

            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", ctypes.c_uint32),
                    ("biWidth", ctypes.c_int32),
                    ("biHeight", ctypes.c_int32),
                    ("biPlanes", ctypes.c_uint16),
                    ("biBitCount", ctypes.c_uint16),
                    ("biCompression", ctypes.c_uint32),
                    ("biSizeImage", ctypes.c_uint32),
                    ("biXPelsPerMeter", ctypes.c_int32),
                    ("biYPelsPerMeter", ctypes.c_int32),
                    ("biClrUsed", ctypes.c_uint32),
                    ("biClrImportant", ctypes.c_uint32),
                ]

            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0

            ppvBits = ctypes.c_void_p()
            hbitmap = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(ppvBits), None, 0)
            ctypes.memmove(ppvBits, raw_buffer, len(raw_buffer))

            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(None, hdc)
            return hbitmap
        except Exception as e:
            print(e)
            traceback.print_exc()
