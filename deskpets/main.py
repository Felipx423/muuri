import platform
import sys
import traceback

from PyQt6 import QtWidgets

from .window import MainWindow
from .single_instance import SingleInstance


def main():
    if platform.system() != "Windows":
        print("DeskPets can only run on Windows.")
        sys.exit(1)

    instance = SingleInstance()
    try:
        if not instance.acquire():
            return
        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow(app)
        window.hide()
        window.start_refresh()
        sys.exit(app.exec())
    except Exception as e:
        print(e)
        traceback.print_exc()
    finally:
        instance.close()
