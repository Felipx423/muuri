import platform
import sys
import traceback

from PyQt6 import QtWidgets

from .window import MainWindow
from .single_instance import SingleInstance


def main():
    if platform.system() != "Windows":
        print("Muuri funciona apenas no Windows.")
        sys.exit(1)

    instance = SingleInstance()
    try:
        if not instance.acquire():
            return
        app = QtWidgets.QApplication(sys.argv)
        app.setApplicationName("Muuri")
        app.setApplicationDisplayName("Muuri")
        window = MainWindow(app)
        window.hide()
        window.start_refresh()
        sys.exit(app.exec())
    except Exception as e:
        print(e)
        traceback.print_exc()
    finally:
        instance.close()
