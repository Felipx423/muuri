import platform
import sys
import traceback

from PyQt6 import QtWidgets

from .window import MainWindow
from .single_instance import SingleInstance


def main():
    if platform.system() not in ("Windows", "Darwin"):
        print("Muuri funciona no Windows e no macOS.")
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
        if not window.start_refresh():
            raise RuntimeError("Não foi possível iniciar os pets.")
        window.updater.start()
        sys.exit(app.exec())
    except Exception as e:
        print(e)
        traceback.print_exc()
        sys.exit(1)
    finally:
        instance.close()
