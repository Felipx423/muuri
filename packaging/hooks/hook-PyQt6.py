from pathlib import Path
from PyInstaller.utils.hooks.qt import pyqt6_library_info, ensure_single_qt_bindings_package

ensure_single_qt_bindings_package('PyQt6')
if pyqt6_library_info.version is not None:
    hiddenimports = ['PyQt6.sip', 'pkgutil']
    # QWidget painting and the pet's native layered window use raster rendering.
    binaries = [entry for entry in pyqt6_library_info.collect_extra_binaries()
                if Path(entry[0]).name.lower() != 'opengl32sw.dll']
