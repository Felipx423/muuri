"""Qt pet windows and mouse events; native Cocoa policy is isolated here."""
import sys
from ctypes import c_void_p

from PyQt6 import QtCore, QtGui, QtWidgets

from . import config_io


def screen_rect():
    return QtWidgets.QApplication.primaryScreen().availableGeometry()


class PetWindow(QtWidgets.QWidget):
    def __init__(self, x, y, width, height, interactive):
        flags = (QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.FramelessWindowHint
                 | QtCore.Qt.WindowType.WindowDoesNotAcceptFocus)
        config = config_io.read_json(config_io.CONFIG_FILE)
        self.layer = config.get("layer", "front")
        flags |= (QtCore.Qt.WindowType.WindowStaysOnTopHint if self.layer == "front"
                  else QtCore.Qt.WindowType.WindowStaysOnBottomHint)
        if not interactive:
            flags |= QtCore.Qt.WindowType.WindowTransparentForInput
        super().__init__(None, flags)
        self.pet = None
        self.frame = None
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, not interactive)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.resize(width, height)
        self.place(x, y)
        self.show()
        try:
            self.configure_cocoa()
        except Exception:
            self.hide()
            self.deleteLater()
            raise

    def configure_cocoa(self):
        if sys.platform != "darwin":
            return
        import AppKit
        import objc
        view = objc.objc_object(c_void_p=c_void_p(int(self.winId())))
        window = view.window()
        level = AppKit.NSFloatingWindowLevel if self.layer == "front" else AppKit.NSNormalWindowLevel - 1
        window.setLevel_(level)
        window.setHidesOnDeactivate_(False)
        # Join ordinary desktops; do not request the full-screen auxiliary role.
        window.setCollectionBehavior_(AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
                                      | AppKit.NSWindowCollectionBehaviorStationary
                                      | AppKit.NSWindowCollectionBehaviorIgnoresCycle)

    def place(self, x, y):
        origin = screen_rect().topLeft()
        self.move(round(x) + origin.x(), round(y) + origin.y())

    def paintEvent(self, event):
        if self.frame is not None:
            painter = QtGui.QPainter(self)
            painter.drawImage(self.rect(), self.frame)

    def point(self, event):
        point = event.globalPosition().toPoint() - screen_rect().topLeft()
        return point.x(), point.y()

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.MouseButton.LeftButton or self.pet is None:
            return
        pet = self.pet
        if pet.mouse_pressed:
            return
        point = event.position().toPoint()
        pet.drag_offset = point.x(), point.y()
        pet.mouse_pressed = True
        pet.motion.begin(pet.x, pet.y)
        pet.click_sequence.press(self.point(event))
        pet.dragging = pet.draggable
        pet.drag_direction = pet.state.direction
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.pet is not None and self.pet.mouse_pressed:
            MacOS.move_drag(self.pet, *self.point(event))
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self.pet is not None and self.pet.mouse_pressed:
            point = self.point(event)
            MacOS.move_drag(self.pet, *point)
            MacOS.finish_press(self.pet, point)
            event.accept()

    def event(self, event):
        pet = getattr(self, "pet", None)
        if (event.type() in (QtCore.QEvent.Type.UngrabMouse, QtCore.QEvent.Type.Hide)
                and pet is not None and pet.mouse_pressed):
            MacOS.end_drag(self.pet)
        return super().event(event)


class MacOS:
    @staticmethod
    def screen_size():
        rect = screen_rect()
        return rect.width(), rect.height()

    @staticmethod
    def cursor_position():
        point = QtGui.QCursor.pos() - screen_rect().topLeft()
        return point.x(), point.y()

    @staticmethod
    def taskbar_settings():
        # availableGeometry already excludes the Dock and menu bar.
        return 0, True, 3

    @staticmethod
    def hwnd(x, y, width, height, draggable=False):
        return PetWindow(x, y, width, height, draggable)

    @staticmethod
    def enable_drag(pet):
        pet.hwnd.pet = pet

    @staticmethod
    def draw_pet_frame(pet, frame):
        if pet.hwnd is None:
            return
        raw = frame.tobytes()
        image = QtGui.QImage(raw, frame.width, frame.height, frame.width * 4,
                             QtGui.QImage.Format.Format_RGBA8888).copy()
        pet.hwnd.frame = image
        pet.hwnd.setMask(QtGui.QRegion(QtGui.QBitmap.fromImage(image.createAlphaMask())))
        pet.hwnd.place(pet.x, pet.y)
        pet.hwnd.update()

    @staticmethod
    def close(pet):
        if pet.hwnd is not None:
            MacOS.end_drag(pet)
            pet.hwnd.pet = None
            pet.hwnd.hide()
            pet.hwnd.deleteLater()
            pet.hwnd = None
        pet.current_frame = 0

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
        pet.hwnd.place(pet.x, pet.y)

    @staticmethod
    def finish_press(pet, point):
        was_dragged = pet.draggable and pet.click_sequence.moved
        open_settings = pet.click_sequence.release(point)
        if pet.physics_enabled and was_dragged:
            pet.motion.launch()
        else:
            pet.motion.stop()
        MacOS.end_drag(pet, cancel_clicks=False)
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

    @staticmethod
    def update_drag(pet):
        if not pet.mouse_pressed:
            return
        point = MacOS.cursor_position()
        if not QtWidgets.QApplication.mouseButtons() & QtCore.Qt.MouseButton.LeftButton:
            MacOS.finish_press(pet, point)
        else:
            MacOS.move_drag(pet, *point)

    @staticmethod
    def update_physics(pet, elapsed):
        if pet.motion.advance(pet, elapsed):
            pet.hwnd.place(pet.x, pet.y)
