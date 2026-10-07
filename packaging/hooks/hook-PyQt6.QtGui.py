from pathlib import Path
from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
# Qt's PDF image plugin otherwise pulls a complete PDF renderer into the bundle.
hiddenimports = [name for name in hiddenimports if name not in ('PyQt6.QtPdf', 'PyQt6.QtPdfWidgets')]
binaries = [entry for entry in binaries if Path(entry[0]).name.lower() not in
            ('qpdf.dll', 'qt6pdf.dll', 'qt6pdfwidgets.dll')]
