import unittest
from unittest import mock

import win_api


class WinApiTests(unittest.TestCase):
    def test_detect_duplicate_hotkeys_reports_internal_duplicates(self):
        spec = {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "K"}
        errors = win_api._detect_duplicate_hotkeys([
            (1, spec),
            (2, {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "K"}),
        ])
        self.assertEqual(len(errors), 1)
        self.assertIn("Duplicates another app hotkey setting", errors[0])

    def test_get_startup_command_points_to_gui_entry_when_not_frozen(self):
        with mock.patch.object(win_api.sys, "frozen", False, create=True):
            command = win_api.get_startup_command()
        self.assertIn("python", command.lower())
        self.assertIn("mouse_center_lock_gui.py", command)


if __name__ == "__main__":
    unittest.main()
