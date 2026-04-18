"""
Theme application service for MouseCenterLock.
"""
from __future__ import annotations

from PySide6 import QtGui, QtWidgets


class ThemeService:
    """Build and apply the application's light and dark themes."""

    def apply(self, window, theme: str) -> None:
        """Apply the requested theme to the QApplication and the main window."""
        QtWidgets.QApplication.setStyle("Fusion")
        if theme == "light":
            palette = self._create_light_palette()
            stylesheet = self._light_stylesheet()
        else:
            palette = self._create_dark_palette()
            stylesheet = self._dark_stylesheet()

        QtWidgets.QApplication.setPalette(palette)
        window.setStyleSheet(stylesheet)

    def _create_dark_palette(self) -> QtGui.QPalette:
        """Create the dark theme palette."""
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(28, 28, 30))
        palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(235, 235, 245))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(44, 44, 46))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(28, 28, 30))
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor(235, 235, 245))
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(44, 44, 46))
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(235, 235, 245))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(10, 132, 255))
        palette.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor(142, 142, 147))
        return palette

    def _create_light_palette(self) -> QtGui.QPalette:
        """Create the light theme palette."""
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(242, 242, 247))
        palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(20, 20, 25))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(242, 242, 247))
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor(20, 20, 25))
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(20, 20, 25))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(10, 132, 255))
        palette.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor(142, 142, 147))
        return palette

    def _dark_stylesheet(self) -> str:
        return """
            QMainWindow { background: #1c1c1e; }
            QWidget { color: #ebebf5; font-size: 14px; }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0a84ff, stop:1 #0671dd);
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                color: white;
                font-weight: 500;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2b95ff, stop:1 #1982ee);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0671dd, stop:1 #0558bb);
            }
            QComboBox, QSpinBox, QLineEdit {
                background: #2c2c2e;
                border: 1px solid #48484a;
                border-radius: 6px;
                padding: 6px;
            }
            QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
                border: 1px solid #0a84ff;
            }
            QCheckBox { spacing: 8px; }
            QScrollArea { border: none; }
        """

    def _light_stylesheet(self) -> str:
        return """
            QMainWindow { background: #f2f2f7; }
            QWidget { color: #141419; font-size: 14px; }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0a84ff, stop:1 #0671dd);
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                color: white;
                font-weight: 500;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2b95ff, stop:1 #1982ee);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0671dd, stop:1 #0558bb);
            }
            QComboBox, QSpinBox, QLineEdit {
                background: #ffffff;
                border: 1px solid #d1d1d6;
                border-radius: 6px;
                padding: 6px;
            }
            QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
                border: 1px solid #0a84ff;
            }
            QCheckBox { spacing: 8px; }
            QScrollArea { border: none; }
        """
