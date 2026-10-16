"""Shared appearance of the settings panel; independent of desktop pet rendering."""

STYLE = """
QWidget { color: #233253; font-family: 'Segoe UI'; font-size: 12px; }
QWidget#panel, QWidget#petsContent, QWidget#body { background: #f8f9fe; }
QFrame#sidebar { background: white; border-right: 1px solid #e7eaf3; }
QLabel#brand { font-size: 25px; font-weight: 700; color: #233253; }
QLabel#eyebrow { color: #66718b; font-size: 10px; font-weight: 600; }
QLabel#pageTitle { font-size: 27px; font-weight: 700; }
QLabel#title { font-size: 25px; font-weight: 700; }
QLabel#sectionTitle { font-size: 17px; font-weight: 600; }
QLabel#muted, QLabel#statusDetail { color: #66718b; font-size: 11px; }
QLabel#statusTitle { font-weight: 600; }
QLabel#badge { background: #edf1ff; color: #4265dd; padding: 4px 9px; border-radius: 10px; font-size: 11px; }
QFrame#card { background: white; border: 1px solid #e7eaf3; border-radius: 16px; }
QFrame#footer { background: white; border-top: 1px solid #e7eaf3; }
QFrame#hero { background: #eef1fc; border-radius: 12px; }
QTabWidget::pane { border: 0; background: transparent; }
QTabBar::tab { color: #66718b; padding: 9px 6px; margin-right: 14px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #4265dd; border-bottom-color: #4265dd; }
QTabBar::tab:hover { color: #4265dd; }
QScrollArea { border: 0; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QListWidget#collection { background: transparent; border: 0; padding: 0; }
QComboBox, QLineEdit { background: #f8f9fe; border: 1px solid #e0e5f1; border-radius: 8px; padding: 6px 9px; min-height: 18px; }
QLineEdit#search { background: white; padding: 8px 12px; }
QLineEdit#quantity { background: white; padding: 4px 0; border-radius: 0; }
QComboBox:hover, QLineEdit:hover { border-color: #a6b7ed; }
QComboBox:focus, QLineEdit:focus { border: 2px solid #4265dd; }
QComboBox QAbstractItemView { background: white; selection-background-color: #edf1ff; selection-color: #233253; }
QPushButton { background: white; border: 1px solid #e0e5f1; border-radius: 8px; padding: 8px 12px; font-weight: 600; }
QPushButton:hover { background: #edf1ff; border-color: #a6b7ed; }
QPushButton:focus { border: 2px solid #4265dd; }
QPushButton#primary { background: #4265dd; color: white; border: 1px solid #4265dd; padding: 9px 18px; }
QPushButton#primary:hover { background: #3454c3; }
QPushButton#add { background: #edf1ff; color: #4265dd; border-color: #dce4fc; }
QPushButton#navigation { background: transparent; border: 0; text-align: left; color: #66718b; padding: 11px 10px; }
QPushButton#navigation:checked { background: #edf1ff; color: #4265dd; }
QPushButton#navigation:hover { background: #f1f4fc; }
QPushButton#navigation:focus { border: 2px solid #4265dd; }
QPushButton#view { border: 0; border-bottom: 2px solid transparent; border-radius: 0; padding: 8px 5px; background: transparent; color: #66718b; }
QPushButton#view:checked { border-bottom-color: #4265dd; color: #4265dd; }
QPushButton#view:focus { border: 2px solid #4265dd; }
QPushButton#textAction { background: transparent; border: 0; color: #66718b; padding: 5px 0; font-size: 11px; }
QPushButton#removeAll { background: transparent; border: 0; color: #a44859; padding: 5px 0; font-size: 11px; }
QPushButton#textAction:hover, QPushButton#removeAll:hover { text-decoration: underline; }
QPushButton#textAction:focus, QPushButton#removeAll:focus { border: 2px solid #4265dd; }
QPushButton#step { background: #f4f6ff; color: #4265dd; padding: 3px; font-size: 17px; }
QPushButton#previewAction { background: white; padding: 4px 9px; font-size: 11px; }
QPushButton:disabled { background: #f0f2f7; color: #737e96; border-color: #e7eaf3; }
QPushButton#primary:disabled { background: #a2b2ef; color: white; border-color: #a2b2ef; }
QPushButton#removeAll:disabled, QPushButton#textAction:disabled { background: transparent; color: #8a92a4; }
QCheckBox { spacing: 8px; padding: 3px 0; }
QCheckBox::indicator { width: 17px; height: 17px; }
QSlider::groove:horizontal { background: #e7eaf3; height: 5px; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #4265dd; border-radius: 2px; }
QSlider::handle:horizontal { background: #4265dd; width: 15px; margin: -5px 0; border-radius: 7px; }
QSlider::handle:horizontal:hover { background: #3454c3; }
QSlider:focus { background: #edf1ff; }
QScrollBar:horizontal { height: 8px; background: #f0f2f8; border-radius: 4px; }
QScrollBar:vertical { width: 8px; background: #f0f2f8; border-radius: 4px; }
QScrollBar::handle { background: #bac4dd; border-radius: 4px; min-width: 24px; min-height: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QTextBrowser { background: white; border: 1px solid #e7eaf3; border-radius: 12px; padding: 18px; }
"""
