import unittest

from ui.presenters.main_window_presenter import (
    build_clicker_button_presentation,
    build_simple_info_text,
    build_status_badge_presentation,
    build_toggle_button_text,
    resolve_clicker_preset,
)


class _I18nStub:
    def t(self, _key, fallback=""):
        return fallback or _key


class MainWindowPresenterTests(unittest.TestCase):
    def setUp(self):
        self.i18n = _I18nStub()

    def test_build_status_badge_for_waiting_state(self):
        text, style = build_status_badge_presentation(
            self.i18n,
            locked=False,
            is_force_lock=False,
            auto_lock_suspended=False,
            window_specific={"enabled": True, "autoLockOnWindowFocus": True},
        )
        self.assertIn("WAITING", text)
        self.assertIn("#c9a961", style)

    def test_build_simple_info_text_includes_clicker_trigger_summary(self):
        config_text, hotkeys_text = build_simple_info_text(
            self.i18n,
            settings_data={
                "recenter": {"enabled": True, "intervalMs": 250},
                "position": {"mode": "custom", "customX": 1, "customY": 2},
                "windowSpecific": {"enabled": False, "targetWindows": []},
                "hotkeys": {
                    "lock": {"modCtrl": True, "modAlt": False, "modShift": False, "modWin": False, "key": "F9"},
                    "unlock": {"modCtrl": True, "modAlt": False, "modShift": False, "modWin": False, "key": "F10"},
                    "toggle": {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "K"},
                },
            },
            clicker={
                "enabled": True,
                "button": "middle",
                "intervalMs": 100,
                "preset": "efficient",
                "triggers": {
                    "mode": "holdMouseButton",
                    "holdMouseButton": "x1",
                },
            },
            clicker_running=True,
            clicker_presets={"custom": None, "efficient": 100, "extreme": 10},
            clicker_trigger_modes={
                "toggle": "clicker.trigger.toggle",
                "holdKey": "clicker.trigger.holdKey",
                "holdMouseButton": "clicker.trigger.holdMouseButton",
            },
        )
        self.assertIn("Custom (1, 2)", config_text)
        self.assertIn("100ms", config_text)
        self.assertIn("Running: On", config_text)
        self.assertIn("x1", hotkeys_text)

    def test_build_toggle_and_clicker_button_text(self):
        toggle_text = build_toggle_button_text(
            self.i18n,
            locked=False,
            hotkeys={
                "lock": {"modCtrl": True, "modAlt": False, "modShift": False, "modWin": False, "key": "F9"},
                "unlock": {"modCtrl": True, "modAlt": False, "modShift": False, "modWin": False, "key": "F10"},
                "toggle": {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "K"},
            },
        )
        clicker_text, enabled = build_clicker_button_presentation(
            self.i18n,
            clicker={
                "enabled": True,
                "triggers": {"mode": "holdKey", "holdKey": {"modCtrl": False, "modAlt": False, "modShift": False, "modWin": False, "key": "F7"}},
            },
            clicker_running=False,
        )
        self.assertIn("Lock to center", toggle_text)
        self.assertIn("Ctrl+Alt+K", toggle_text)
        self.assertIn("Start Auto Clicker", clicker_text)
        self.assertIn("F7", clicker_text)
        self.assertTrue(enabled)

    def test_resolve_clicker_preset_falls_back_to_custom(self):
        self.assertEqual(resolve_clicker_preset(77, {"custom": None, "efficient": 100, "extreme": 10}), "custom")


if __name__ == "__main__":
    unittest.main()
