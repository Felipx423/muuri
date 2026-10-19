import ctypes
import json
import os
import traceback
from ctypes import windll
from ctypes import wintypes

from PyQt6 import QtCore
from .remove_alpha import GifHelper

import win32gui
import win32con

BASE_DIR = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

WS_EX_LAYERED = 0x80000
WS_EX_TOPMOST = 0x0008
WS_EX_TRANSPARENT = 0x20
WS_EX_NOACTIVATE = 0x08000000
WS_POPUP = 0x80000000
ULW_ALPHA = 0x2

user32FS = windll.user32


def is_full_screen():
    try:
        hWnd = user32FS.GetForegroundWindow()
        rect = win32gui.GetWindowRect(hWnd)
        full_screen_rect = (0, 0, user32FS.GetSystemMetrics(0), user32FS.GetSystemMetrics(1))
        return rect == full_screen_rect
    except:
        return False


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_byte),
        ("BlendFlags", ctypes.c_byte),
        ("SourceConstantAlpha", ctypes.c_byte),
        ("AlphaFormat", ctypes.c_byte)
    ]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]


class APPBARDATA(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint),
                ("hWnd", wintypes.HWND),
                ("uCallbackMessage", ctypes.c_uint),
                ("uEdge", ctypes.c_uint),
                ("rc", RECT),
                ("lParam", ctypes.c_int)]


def load_config():
    try:
        if not os.path.exists(CONFIG_FILE):
            return {"layer": "front"}
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"layer": "front"}


STATE_FULLSCREEN = False


class Windows:
    @staticmethod
    def hwnd(x, y, width, height, draggable=False):
        try:
            cfg = load_config()
            layer = cfg.get("layer", "front")

            ex_style = WS_EX_LAYERED | WS_EX_NOACTIVATE
            if not draggable:
                ex_style |= WS_EX_TRANSPARENT

            if layer == "front" and not is_full_screen():
                ex_style |= WS_EX_TOPMOST

            h = user32.CreateWindowExW(
                ex_style,
                "Static",
                None,
                WS_POPUP,
                x, y, width, height,
                None, None, None, None
            )
            user32.ShowWindow(h, 5)
            return h

        except Exception as e:
            print(e)
            traceback.print_exc()

    @staticmethod
    def enable_drag(pet):
        def window_proc(hwnd, message, wparam, lparam):
            if message == win32con.WM_NCHITTEST:
                return win32con.HTCLIENT
            if message == win32con.WM_MOUSEACTIVATE:
                return win32con.MA_NOACTIVATE
            if message in (win32con.WM_LBUTTONDOWN, win32con.WM_LBUTTONDBLCLK):
                if pet.mouse_pressed:
                    return 0
                pet.drag_offset = (ctypes.c_short(lparam & 0xffff).value,
                                   ctypes.c_short((lparam >> 16) & 0xffff).value)
                pet.mouse_pressed = True
                pet.motion.begin(pet.x, pet.y)
                pet.click_sequence.press(win32gui.ClientToScreen(hwnd, pet.drag_offset))
                pet.dragging = pet.draggable
                pet.drag_direction = pet.state.direction
                win32gui.SetCapture(hwnd)
                return 0
            if message == win32con.WM_MOUSEMOVE and pet.mouse_pressed:
                point = (ctypes.c_short(lparam & 0xffff).value,
                         ctypes.c_short((lparam >> 16) & 0xffff).value)
                Windows.move_drag(pet, *win32gui.ClientToScreen(hwnd, point))
                return 0
            if message == win32con.WM_LBUTTONUP and pet.mouse_pressed:
                point = (ctypes.c_short(lparam & 0xffff).value,
                         ctypes.c_short((lparam >> 16) & 0xffff).value)
                screen_point = win32gui.ClientToScreen(hwnd, point)
                Windows.move_drag(pet, *screen_point)
                Windows.finish_press(pet, screen_point)
                return 0
            if (message in (win32con.WM_CAPTURECHANGED, win32con.WM_CANCELMODE)
                    and pet.mouse_pressed):
                Windows.end_drag(pet)
            return win32gui.CallWindowProc(pet.old_window_proc, hwnd, message, wparam, lparam)

        pet.drag_window_proc = window_proc
        pet.old_window_proc = win32gui.SetWindowLong(pet.hwnd, win32con.GWL_WNDPROC, window_proc)

    @staticmethod
    def move_drag(pet, mouse_x, mouse_y):
        pet.click_sequence.move((mouse_x, mouse_y))
        if not pet.draggable or not pet.click_sequence.moved:
            return
        pet.free_roam = True
        previous_x = pet.x
        pet.x = max(0, min(mouse_x - pet.drag_offset[0], pet.screen_width - pet.width))
        if pet.x != previous_x:
            pet.drag_direction = 1 if pet.x > previous_x else -1
        pet.y = max(0, min(mouse_y - pet.drag_offset[1], pet.screen_height - pet.height))
        pet.y_def = pet.y
        pet.motion.track(pet.x, pet.y)
        win32gui.SetWindowPos(pet.hwnd, 0, int(pet.x), int(pet.y), 0, 0,
                             win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE)

    @staticmethod
    def finish_press(pet, point):
        was_dragged = pet.draggable and pet.click_sequence.moved
        open_settings = pet.click_sequence.release(point)
        if pet.physics_enabled and was_dragged:
            pet.motion.launch()
        else:
            pet.motion.stop()
        Windows.end_drag(pet, cancel_clicks=False)
        owner = getattr(pet, "main_window", None)
        if open_settings and pet.settings_clicks and owner is not None:
            owner.show_pet_settings.emit(pet.species)

    @staticmethod
    def end_drag(pet, cancel_clicks=True):
        pet.dragging = False
        pet.mouse_pressed = False
        if cancel_clicks:
            pet.click_sequence.reset()
            pet.motion.stop()
        if pet.hwnd and win32gui.GetCapture() == pet.hwnd:
            win32gui.ReleaseCapture()

    @staticmethod
    def update_drag(pet):
        # Poll while captured so a fast mouse move outside a non-activating
        # pet window still follows the pointer and release cannot get stuck.
        if not pet.mouse_pressed and not pet.dragging:
            return
        if not user32.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000:
            if pet.mouse_pressed:
                Windows.finish_press(pet, win32gui.GetCursorPos())
            else:
                Windows.end_drag(pet)
            return
        Windows.move_drag(pet, *win32gui.GetCursorPos())

    @staticmethod
    def update_physics(pet, elapsed):
        if pet.motion.advance(pet, elapsed):
            win32gui.SetWindowPos(pet.hwnd, 0, int(pet.x), int(pet.y), 0, 0,
                                 win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE)

    @staticmethod
    def taskbar_settings():
        try:
            ABS_AUTOHIDE = 0x1
            ABM_GETSTATE = 4
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            state = ctypes.windll.shell32.SHAppBarMessage(ABM_GETSTATE, ctypes.byref(abd))

            ABM_GETTASKBARPOS = 5
            shappbar = ctypes.windll.shell32.SHAppBarMessage
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            result = shappbar(ABM_GETTASKBARPOS, ctypes.byref(abd))

            if result:
                tb_rect = abd.rc
                tb_width = tb_rect.right - tb_rect.left
                tb_height = tb_rect.bottom - tb_rect.top
                tb_edge = abd.uEdge  # 0=left,1=top,2=right,3=bottom
                return tb_height, bool(state & ABS_AUTOHIDE), tb_edge
            else:
                return 60, bool(state & ABS_AUTOHIDE), 3
        except Exception as e:
            print(e)
            traceback.print_exc()


    @staticmethod
    def draw_pet_frame(pet, frame_image):
        try:
            if getattr(pet, "hwnd", None):
                hbitmap = GifHelper.pil_to_hbitmap(frame_image)
                Windows.draw_frame(pet, hbitmap)
                gdi32.DeleteObject(hbitmap)
        except Exception as e:
            print(e)
            traceback.print_exc()

    @staticmethod
    def draw_frame(self, hbitmap):
        global STATE_FULLSCREEN
        try:
            full_screen_now = is_full_screen()
            if full_screen_now != STATE_FULLSCREEN:
                STATE_FULLSCREEN = full_screen_now
                if getattr(self, "main_window", None):
                    QtCore.QTimer.singleShot(0, self.main_window.start_refresh)
                    return

            hdc_screen = user32.GetDC(None)
            hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
            gdi32.SelectObject(hdc_mem, hbitmap)

            blend = BLENDFUNCTION()
            blend.BlendOp = 0
            blend.BlendFlags = 0
            blend.SourceConstantAlpha = 255
            blend.AlphaFormat = 1

            pt_pos = POINT(int(self.x), int(self.y))
            size = SIZE(self.width, self.height)
            pt_src = POINT(0, 0)

            user32.UpdateLayeredWindow(self.hwnd, hdc_screen, ctypes.byref(pt_pos),
                                       ctypes.byref(size), hdc_mem, ctypes.byref(pt_src),
                                       0, ctypes.byref(blend), ULW_ALPHA)

            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(None, hdc_screen)

        except Exception as e:
            print(e)
            traceback.print_exc()

    @staticmethod
    def close(pet):
        try:
            if getattr(pet, "hbitmaps", None):
                for hb in pet.hbitmaps:
                    try:
                        gdi32.DeleteObject(hb)
                    except Exception:
                        pass
            pet.hbitmaps = []

            if getattr(pet, "hwnd", None):
                if pet.draggable or pet.settings_clicks:
                    Windows.end_drag(pet)
                # Keep the mouse callback alive until native destruction finishes.
                ctypes.windll.user32.DestroyWindow(pet.hwnd)
                pet.hwnd = None
                if pet.draggable or pet.settings_clicks:
                    pet.drag_window_proc = None

            pet.current_frame = 0
        except Exception as e:
            print(e)
            traceback.print_exc()

    @staticmethod
    def screen_size():
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    @staticmethod
    def cursor_position():
        point = POINT()
        user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y
