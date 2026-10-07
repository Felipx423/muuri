import ctypes
import os
import time
import traceback

from PyQt6 import QtWidgets, QtGui, QtCore

from .petworker import PetWorker, load_pets
from .remove_alpha import GifHelper
from .panel import SettingsPanel
from .windows_API import POINT, SIZE, BLENDFUNCTION, Windows, is_full_screen

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

BASE_DIR = os.path.dirname(__file__)
LOGO_DIR = os.path.join(BASE_DIR, "media", "muuri", "muuri.ico")

ULW_ALPHA = 0x2

STATE_FULLSCREEN = False


def draw_pet_frame(pet, frame_image):
    try:
        if getattr(pet, "hwnd", None):
            hbitmap = GifHelper.pil_to_hbitmap(frame_image)
            draw_frame(pet, hbitmap)
            gdi32.DeleteObject(hbitmap)
    except Exception as e:
        print(e)
        traceback.print_exc()


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


class MainWindow(QtWidgets.QMainWindow):
    show_pet_settings = QtCore.pyqtSignal(str)

    def __init__(self, app):
        try:
            super().__init__()
            app.setStyle("Fusion")
            palette = QtGui.QPalette()
            for role, color in ((QtGui.QPalette.ColorRole.Window, "#f4f8fd"),
                                (QtGui.QPalette.ColorRole.WindowText, "#223957"),
                                (QtGui.QPalette.ColorRole.Base, "#ffffff"),
                                (QtGui.QPalette.ColorRole.Text, "#223957"),
                                (QtGui.QPalette.ColorRole.Button, "#ffffff"),
                                (QtGui.QPalette.ColorRole.ButtonText, "#223957"),
                                (QtGui.QPalette.ColorRole.Link, "#1769c8"),
                                (QtGui.QPalette.ColorRole.LinkVisited, "#1257a6"),
                                (QtGui.QPalette.ColorRole.Highlight, "#dcecff"),
                                (QtGui.QPalette.ColorRole.HighlightedText, "#1257a6")):
                palette.setColor(role, QtGui.QColor(color))
            app.setPalette(palette)
            self.setWindowTitle("Muuri · DeskPets")
            self.resize(800, 600)
            self.setWindowIcon(QtGui.QIcon(LOGO_DIR))
            app.setWindowIcon(QtGui.QIcon(LOGO_DIR))
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u"DeskPets")

            self.panel = SettingsPanel(self)
            self.setCentralWidget(self.panel)
            self.panel.preview.timer.stop()
            self.setMinimumSize(900, 620)
            available = app.primaryScreen().availableGeometry()
            self.resize(min(1080, available.width()-40), min(760, available.height()-60))
            self.show_pet_settings.connect(self.show_settings_for_pet, QtCore.Qt.ConnectionType.QueuedConnection)
            app.setQuitOnLastWindowClosed(False)
            app.aboutToQuit.connect(self.shutdown)

            # Tray
            self.tray_icon = QtWidgets.QSystemTrayIcon(self)
            self.tray_icon.setIcon(QtGui.QIcon(LOGO_DIR))
            show_action = QtGui.QAction("Abrir configurações", self)
            refresh_action = QtGui.QAction("Atualizar pets", self)
            quit_action = QtGui.QAction("Sair", self)
            show_action.triggered.connect(self.show_window)
            refresh_action.triggered.connect(self.start_refresh)
            quit_action.triggered.connect(self.request_quit)
            tray_menu = QtWidgets.QMenu()
            tray_menu.addAction(show_action)
            tray_menu.addAction(refresh_action)
            tray_menu.addSeparator()
            tray_menu.addAction(quit_action)
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.setToolTip("Muuri · DeskPets")
            self.tray_icon.activated.connect(self.tray_activated)
            self.tray_icon.show()

            # Pets
            self.pets = []
            self.worker = None
            self.refreshing = False
            self.drag_timer = QtCore.QTimer(self)
            self.last_physics_update = time.monotonic()
            self.drag_timer.timeout.connect(self.update_drag)
            self.drag_timer.start(16)
        except Exception as e:
            print(e)
            traceback.print_exc()
            raise

    def update_drag(self):
        now = time.monotonic()
        elapsed = now - self.last_physics_update
        self.last_physics_update = now
        for pet in self.pets:
            if pet.draggable or pet.settings_clicks:
                Windows.update_drag(pet)
            Windows.update_physics(pet, elapsed)

    def start_refresh(self):
        if self.refreshing:
            return True
        self.refreshing = True
        try:
            if self.worker:
                self.worker.stop()
                if not self.worker.wait(3000):
                    raise RuntimeError("O processamento dos pets não encerrou a tempo.")
            positions = {(p.species, p.color): (p.x, p.y, p.y_def, p.state.direction, p.free_roam,
                                                p.physics_enabled, p.motion.vx, p.motion.vy)
                         for p in self.pets}
            new_pets = load_pets()
            for pet in self.pets:
                close(pet)
            self.pets = new_pets
            for pet in self.pets:
                pet.main_window = self
                saved = positions.get((pet.species, pet.color))
                if saved:
                    x, y, y_def, direction, free_roam, physics_enabled, vx, vy = saved
                    pet.x = max(0, min(x, pet.screen_width-pet.width))
                    pet.y = max(0, min(y, pet.screen_height-pet.height))
                    pet.y_def = max(0, min(y_def, pet.screen_height-pet.height))
                    pet.state.direction = direction
                    pet.free_roam = free_roam
                    if physics_enabled and pet.physics_enabled:
                        pet.motion.vx, pet.motion.vy = vx, vy
            self.worker = PetWorker(self.pets)
            self.worker.frame_ready.connect(self.render_pet)
            self.worker.start()
            return True
        except Exception as error:
            print(error)
            traceback.print_exc()
            return False
        finally:
            self.refreshing = False

    @QtCore.pyqtSlot(object, object)
    def render_pet(self, pet, frame):
        if pet in self.pets:
            draw_pet_frame(pet, frame)

    def closeEvent(self, event):
        event.ignore()
        if self.panel.allow_close():
            self.hide()

    def hideEvent(self, event):
        self.panel.preview.timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        import time
        self.panel.preview.last_tick = time.monotonic()
        self.panel.preview.timer.start()
        super().showEvent(event)

    def show_settings_for_pet(self, species):
        self.panel.select(species)
        self.panel.tabs.setCurrentIndex(0)
        self.show_window()

    def tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def request_quit(self):
        if self.panel.allow_close():
            QtWidgets.QApplication.instance().quit()

    def shutdown(self):
        self.drag_timer.stop()
        self.panel.preview.timer.stop()
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        for pet in self.pets:
            close(pet)
        self.pets = []
        self.tray_icon.hide()
