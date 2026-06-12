import os
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from ui.main_window import MainWindow


class MainWindowSizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_default_window_size_is_600x800_without_screen(self):
        dummy = types.SimpleNamespace(
            _BASE_WINDOW_SIZE=MainWindow._BASE_WINDOW_SIZE,
            _BASE_SCREEN_SIZE=MainWindow._BASE_SCREEN_SIZE,
            _MIN_WINDOW_SIZE=MainWindow._MIN_WINDOW_SIZE,
        )

        with mock.patch.object(QtWidgets.QApplication, "primaryScreen", return_value=None):
            size = MainWindow._resolve_default_window_size(dummy)

        self.assertEqual((size.width(), size.height()), (600, 800))

    def test_default_window_size_does_not_upscale_on_large_screens(self):
        dummy = types.SimpleNamespace(
            _BASE_WINDOW_SIZE=MainWindow._BASE_WINDOW_SIZE,
            _BASE_SCREEN_SIZE=MainWindow._BASE_SCREEN_SIZE,
            _MIN_WINDOW_SIZE=MainWindow._MIN_WINDOW_SIZE,
        )
        screen = mock.Mock()
        screen.availableGeometry.return_value = QtCore.QRect(0, 0, 3840, 2160)
        screen.devicePixelRatio.return_value = 1.0

        with mock.patch.object(QtWidgets.QApplication, "primaryScreen", return_value=screen):
            size = MainWindow._resolve_default_window_size(dummy)

        self.assertEqual((size.width(), size.height()), (600, 800))


if __name__ == "__main__":
    unittest.main()
