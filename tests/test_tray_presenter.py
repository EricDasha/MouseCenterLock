import unittest

from ui.presenters.tray_presenter import (
    build_tray_clicker_action,
    build_tray_hotkey_text,
    build_tray_state_text,
)


class _I18nStub:
    def t(self, _key, fallback=""):
        return fallback or _key


class TrayPresenterTests(unittest.TestCase):
    def setUp(self):
        self.i18n = _I18nStub()

    def test_build_tray_state_text(self):
        text = build_tray_state_text(
            self.i18n,
            locked=True,
            clicker_running=False,
            clicker_profile={"name": "Default Profile"},
        )
        self.assertIn("Locked", text)
        self.assertIn("Auto Clicker: Off", text)
        self.assertIn("Default Profile", text)

    def test_build_tray_hotkey_text(self):
        text = build_tray_hotkey_text(
            self.i18n,
            hotkeys={
                "toggle": {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "K"},
            },
            clicker_profile={
                "triggers": {
                    "toggleHotkey": {"modCtrl": False, "modAlt": False, "modShift": False, "modWin": False, "key": "F6"},
                }
            },
        )
        self.assertIn("Ctrl+Alt+K", text)
        self.assertIn("F6", text)

    def test_build_tray_clicker_action(self):
        text, enabled = build_tray_clicker_action(
            self.i18n,
            clicker_running=True,
            clicker_profile={"enabled": True},
        )
        self.assertIn("Stop Auto Clicker", text)
        self.assertTrue(enabled)


if __name__ == "__main__":
    unittest.main()
