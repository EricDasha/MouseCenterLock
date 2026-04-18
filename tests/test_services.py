import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from services.clicker_service import ClickerService
from services.lock_service import LockService
from services.tray_service import TrayService


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_clicker_service_start_stop_and_sync(self):
        profile = {
            "enabled": True,
            "button": "left",
            "intervalMs": 25,
            "sound": {"enabled": False, "preset": "systemAsterisk", "customFile": ""},
            "triggers": {"mode": "toggle", "toggleHotkey": {"key": "F6"}},
        }
        state_changes = []
        started = []
        stopped = []

        service = ClickerService(
            get_profile=lambda: profile,
            on_state_changed=lambda: state_changes.append("changed"),
            on_notify_started=lambda p: started.append(p["button"]),
            on_notify_stopped=lambda p: stopped.append(p["button"]),
            sound_presets={"systemAsterisk": 0x40},
        )

        with mock.patch("services.clicker_service.click_mouse"):
            service.start(show_message=True, immediate_click=False)
            self.assertTrue(service.is_running)
            self.assertEqual(started, ["left"])

            profile["enabled"] = False
            service.sync_runtime()
            self.assertFalse(service.is_running)
            self.assertGreaterEqual(len(state_changes), 2)

        service.hold_state_timer.stop()
        service.clicker_timer.stop()

    def test_lock_service_window_matching_and_target_position(self):
        settings = {
            "windowSpecific": {
                "enabled": False,
                "autoLockOnWindowFocus": False,
                "targetWindows": [],
                "resumeAfterWindowSwitch": False,
            },
            "position": {"mode": "custom", "customX": 321, "customY": 654},
            "recenter": {"enabled": True, "intervalMs": 250},
        }
        changes = []
        service = LockService(
            get_settings=lambda: settings,
            on_state_changed=lambda: changes.append("changed"),
            on_notify_locked=lambda: changes.append("locked"),
            on_notify_unlocked=lambda: changes.append("unlocked"),
            on_error=lambda op, exc: changes.append(f"error:{op}"),
        )

        self.assertEqual(service._get_target_position(), (321, 654))
        self.assertTrue(service._check_match("QQ Chat", "qq.exe", ["qq.exe"]))
        self.assertTrue(service._check_match("Minecraft 1.20", "javaw.exe", ["minecraft"]))
        self.assertFalse(service._check_match("Notepad", "notepad.exe", ["qq.exe"]))

        service.window_focus_timer.stop()
        service.recenter_timer.stop()

    def test_tray_service_refreshes_state_and_clicker_text(self):
        profile = {
            "name": "默认方案",
            "enabled": True,
            "triggers": {"toggleHotkey": {"modCtrl": False, "modAlt": False, "modShift": False, "modWin": False, "key": "F6"}},
        }
        service = TrayService(
            parent=None,
            base_icon=self.app.windowIcon(),
            dynamic_icon_factory=lambda locked: self.app.windowIcon(),
            i18n=type("I18nStub", (), {"t": staticmethod(lambda _key, fallback="": fallback or _key)})(),
            get_locked=lambda: True,
            get_clicker_running=lambda: False,
            get_clicker_profile=lambda: profile,
            get_hotkeys=lambda: {"toggle": {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "K"}},
            on_toggle_lock=lambda: None,
            on_lock=lambda: None,
            on_unlock=lambda: None,
            on_toggle_clicker=lambda: None,
            on_show_window=lambda: None,
            on_quit=lambda: None,
        )
        try:
            service.refresh()
            self.assertIn("Locked", service.state_action.text())
            self.assertIn("默认方案", service.state_action.text())
            self.assertIn("Ctrl+Alt+K", service.hk_info_action.text())
            self.assertIn("Start Auto Clicker", service.clicker_action.text())
        finally:
            service.tray.hide()


if __name__ == "__main__":
    unittest.main()
