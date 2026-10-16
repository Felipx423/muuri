import ctypes
import os
import time
import traceback

from PyQt6 import QtWidgets, QtGui, QtCore

from .petworker import PetWorker, load_pets
from .panel import SettingsPanel
from .desktop import Desktop, IS_WINDOWS
from . import config_io
from .update_controller import UpdateController
from .tray_pets import TrayPets

BASE_DIR = os.path.dirname(__file__)
LOGO_DIR = os.path.join(BASE_DIR, "media", "muuri", "muuri.ico")

def draw_pet_frame(pet, frame_image):
    try:
        Desktop.draw_pet_frame(pet, frame_image)
    except Exception as e:
        print(e)
        traceback.print_exc()


def close(pet):
    Desktop.close(pet)


class MainWindow(QtWidgets.QMainWindow):
    show_pet_settings = QtCore.pyqtSignal(str)

    def __init__(self, app):
        try:
            super().__init__()
            config_io.initialize_configs()
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
            self.setWindowTitle("Muuri")
            self.resize(800, 600)
            self.setWindowIcon(QtGui.QIcon(LOGO_DIR))
            app.setWindowIcon(QtGui.QIcon(LOGO_DIR))
            if IS_WINDOWS:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u"Muuri")

            self.panel = SettingsPanel(self)
            self.updater = UpdateController(self)
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
            self.update_action = QtGui.QAction("Verificar atualizações", self)
            self.update_action.triggered.connect(self.updater.check_manually)
            quit_action.setMenuRole(QtGui.QAction.MenuRole.QuitRole)
            quit_action.triggered.connect(self.request_quit)
            self.quit_action = quit_action
            if not IS_WINDOWS:
                quit_action.setShortcut(QtGui.QKeySequence.StandardKey.Quit)
                menu = self.menuBar().addMenu("Muuri")
                menu.addAction(show_action)
                menu.addAction(quit_action)
            tray_menu = QtWidgets.QMenu(self)
            tray_menu.addAction(show_action)
            tray_menu.addAction(refresh_action)
            self.tray_pets = TrayPets(self)
            tray_menu.addAction(self.tray_pets.remove_all_action)
            tray_menu.addMenu(self.tray_pets.favorites_menu)
            tray_menu.aboutToShow.connect(self.tray_pets.update_actions)
            tray_menu.addSeparator()
            tray_menu.addAction(self.update_action)
            tray_menu.addSeparator()
            tray_menu.addAction(quit_action)
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.setToolTip("Muuri")
            self.tray_icon.activated.connect(self.tray_activated)
            self.tray_icon.messageClicked.connect(self.updater.offer_install)
            self.tray_icon.show()

            # Pets
            self.pets = []
            self.worker = None
            self.refreshing = False
            self.drag_timer = QtCore.QTimer(self)
            self.last_physics_update = time.monotonic()
            self.drag_timer.timeout.connect(self.update_drag)
            self.drag_timer.start(16)
            if not IS_WINDOWS:
                self.desktop_screen = None
                app.primaryScreenChanged.connect(self.screen_changed)
                self.screen_changed(app.primaryScreen())
        except Exception as e:
            print(e)
            traceback.print_exc()
            raise

    def screen_changed(self, screen):
        if screen is None:
            return
        previous = self.desktop_screen
        if previous is not None:
            try:
                previous.availableGeometryChanged.disconnect(self.start_refresh)
            except (TypeError, RuntimeError):
                pass
        self.desktop_screen = screen
        screen.availableGeometryChanged.connect(self.start_refresh)
        if previous is not None:
            self.start_refresh()

    def update_drag(self):
        now = time.monotonic()
        elapsed = now - self.last_physics_update
        self.last_physics_update = now
        for pet in self.pets:
            if pet.draggable or pet.settings_clicks:
                Desktop.update_drag(pet)
            Desktop.update_physics(pet, elapsed)

    def start_refresh(self):
        if self.refreshing:
            return True
        self.refreshing = True
        try:
            if self.worker:
                self.worker.stop()
                if not self.worker.wait(3000):
                    raise RuntimeError("O processamento dos pets não encerrou a tempo.")
            positions = {(p.species, p.color, p.instance_index): (p.x, p.y, p.y_def, p.state.direction, p.free_roam,
                                                p.physics_enabled, p.motion.vx, p.motion.vy)
                         for p in self.pets}
            new_pets = load_pets()
            for pet in self.pets:
                close(pet)
            self.pets = new_pets
            for pet in self.pets:
                pet.main_window = self
                saved = positions.get((pet.species, pet.color, pet.instance_index))
                if saved:
                    x, y, y_def, direction, free_roam, physics_enabled, vx, vy = saved
                    pet.x = max(0, min(x, pet.screen_width-pet.width))
                    pet.y = max(0, min(y, pet.screen_height-pet.height))
                    pet.y_def = max(0, min(y_def, pet.screen_height-pet.height))
                    pet.state.direction = direction
                    pet.free_roam = free_roam
                    if physics_enabled and pet.physics_enabled:
                        pet.motion.vx, pet.motion.vy = vx, vy
            occupied = [(p.x, p.y, p.width, p.height) for p in self.pets
                        if (p.species, p.color, p.instance_index) in positions]
            for pet in self.pets:
                if (pet.species, pet.color, pet.instance_index) in positions:
                    continue
                for offset in range(0, pet.screen_width, pet.width + 16):
                    x = max(0, pet.screen_width - pet.width - offset)
                    if all(x + pet.width + 8 <= left or x >= left + width + 8
                           or pet.y + pet.height <= top or pet.y >= top + height
                           for left, top, width, height in occupied):
                        pet.x = x
                        break
                occupied.append((pet.x, pet.y, pet.width, pet.height))
            self.worker = PetWorker(self.pets)
            self.worker.frame_ready.connect(self.render_pet)
            self.worker.start()
            self.tray_pets.update_actions()
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
        if getattr(self, "update_quit", False):
            event.accept()
            return
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
        self.updater.shutdown()
        self.drag_timer.stop()
        self.panel.preview.timer.stop()
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        for pet in self.pets:
            close(pet)
        self.pets = []
        self.tray_icon.hide()
