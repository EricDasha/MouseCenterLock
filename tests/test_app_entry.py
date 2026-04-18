import os
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

import mouse_center_lock_gui


class AppEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_extract_runtime_flags_keeps_qt_args_and_enables_log(self):
        argv, log_enabled = mouse_center_lock_gui._extract_runtime_flags(
            ["mouse_center_lock_gui.py", "-log", "--style", "fusion"]
        )

        self.assertEqual(argv, ["mouse_center_lock_gui.py", "--style", "fusion"])
        self.assertTrue(log_enabled)

    def test_register_startup_hotkeys_warns_on_conflict(self):
        i18n = types.SimpleNamespace(t=lambda _key, fallback="": fallback or _key)
        settings = types.SimpleNamespace(data={"hotkeys": {}})

        with mock.patch("mouse_center_lock_gui.unregister_hotkeys") as unregister_hotkeys, \
             mock.patch("mouse_center_lock_gui.register_hotkeys", return_value=(False, ["F1 conflict"])), \
             mock.patch("mouse_center_lock_gui.log_message") as log_message, \
             mock.patch("mouse_center_lock_gui.QtWidgets.QMessageBox.warning") as warning:
            mouse_center_lock_gui._register_startup_hotkeys(settings, i18n)

        unregister_hotkeys.assert_called_once()
        log_message.assert_called_once()
        warning.assert_called_once()

    def test_wire_hotkeys_routes_actions_to_window(self):
        app = self.app
        window = types.SimpleNamespace(
            lock=mock.Mock(),
            unlock=mock.Mock(),
            toggle_lock=mock.Mock(),
            toggle_clicker=mock.Mock(),
        )

        with mock.patch.object(app, "installNativeEventFilter") as install_native_event_filter:
            mouse_center_lock_gui._wire_hotkeys(app, window)
        install_native_event_filter.assert_called_once()

        emitter = app._hotkey_emitter
        emitter.hotkeyPressed.emit(mouse_center_lock_gui.HOTKEY_ID_LOCK)
        emitter.hotkeyPressed.emit(mouse_center_lock_gui.HOTKEY_ID_UNLOCK)
        emitter.hotkeyPressed.emit(mouse_center_lock_gui.HOTKEY_ID_TOGGLE)
        emitter.hotkeyPressed.emit(mouse_center_lock_gui.HOTKEY_ID_CLICKER_TOGGLE)

        window.lock.assert_called_once_with(manual=True)
        window.unlock.assert_called_once_with(manual=True)
        window.toggle_lock.assert_called_once_with()
        window.toggle_clicker.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
