import os
import types
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from services.clicker_profile_controller import ClickerProfileController
from services.theme_service import ThemeService


class ThemeAndProfileControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_theme_service_applies_stylesheet(self):
        widget = QtWidgets.QWidget()
        service = ThemeService()
        service.apply(widget, "light")
        self.assertIn("QMainWindow", widget.styleSheet())
        service.apply(widget, "dark")
        self.assertIn("#1c1c1e", widget.styleSheet())

    def test_profile_controller_save_profile_runs_refresh_flow(self):
        calls = []
        saved_profile = {"id": "p1", "name": "Profile 1"}
        settings = types.SimpleNamespace(upsert_clicker_profile=lambda profile: saved_profile)
        controller = ClickerProfileController(
            settings=settings,
            save_settings=lambda _context: calls.append("save_settings") or True,
            notify=lambda _message: calls.append("notify"),
            stop_clicker=lambda **_kwargs: calls.append("stop_clicker"),
            sync_clicker_runtime=lambda: calls.append("sync_clicker"),
            refresh_form=lambda _profile: calls.append("refresh_form"),
            refresh_profile_list=lambda: calls.append("refresh_profile_list"),
            refresh_ui=lambda: calls.append("refresh_ui"),
            tooltip_saved=lambda: calls.append("tooltip_saved"),
            i18n=types.SimpleNamespace(t=lambda _key, fallback="": fallback or _key),
        )

        result = controller.save_profile({"id": "p1"})

        self.assertEqual(result, saved_profile)
        self.assertEqual(calls, ["refresh_profile_list", "save_settings", "sync_clicker", "refresh_ui", "tooltip_saved"])


if __name__ == "__main__":
    unittest.main()
