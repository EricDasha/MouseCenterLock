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

    def test_resize_window_adjusts_for_window_frame(self):
        with mock.patch.object(win_api.user32, "GetWindowLongW", side_effect=[0, 0]), \
             mock.patch.object(win_api.user32, "GetMenu", return_value=0), \
             mock.patch.object(win_api.user32, "AdjustWindowRectEx", side_effect=lambda rect, *_args: setattr(rect._obj, "right", 210) or setattr(rect._obj, "bottom", 120) or 1), \
             mock.patch.object(win_api, "get_window_rect", return_value=(10, 20, 310, 220)), \
             mock.patch.object(win_api.user32, "SetWindowPos", return_value=1) as set_window_pos:
            self.assertTrue(win_api.resize_window(123, 200, 100))
        _, _, x, y, width, height, _ = set_window_pos.call_args[0]
        self.assertEqual((x, y, width, height), (10, 20, 210, 120))


if __name__ == "__main__":
    unittest.main()
