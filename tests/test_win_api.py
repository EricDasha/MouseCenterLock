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
             mock.patch.object(win_api, "_restore_window_for_resize"), \
             mock.patch.object(win_api.user32, "GetMenu", return_value=0), \
             mock.patch.object(win_api.user32, "AdjustWindowRectEx", side_effect=lambda rect, *_args: setattr(rect._obj, "right", 210) or setattr(rect._obj, "bottom", 120) or 1), \
             mock.patch.object(win_api, "get_window_rect", return_value=(10, 20, 310, 220)), \
             mock.patch.object(win_api.user32, "SetWindowPos", return_value=1) as set_window_pos:
            self.assertTrue(win_api.resize_window(123, 200, 100))
        _, _, x, y, width, height, _ = set_window_pos.call_args[0]
        self.assertEqual((x, y, width, height), (10, 20, 210, 120))

    def test_get_centered_window_position_uses_adjusted_window_size(self):
        monitor_info = win_api.MONITORINFO()
        monitor_info.cbSize = 0
        monitor_info.rcWork.left = 0
        monitor_info.rcWork.top = 0
        monitor_info.rcWork.right = 1920
        monitor_info.rcWork.bottom = 1080

        def fill_monitor_info(_hmon, info_ptr):
            info_ptr._obj.cbSize = monitor_info.cbSize
            info_ptr._obj.rcWork.left = monitor_info.rcWork.left
            info_ptr._obj.rcWork.top = monitor_info.rcWork.top
            info_ptr._obj.rcWork.right = monitor_info.rcWork.right
            info_ptr._obj.rcWork.bottom = monitor_info.rcWork.bottom
            return 1

        with mock.patch.object(win_api.user32, "MonitorFromWindow", return_value=1), \
             mock.patch.object(win_api.user32, "GetMonitorInfoW", side_effect=fill_monitor_info), \
             mock.patch.object(win_api, "_get_adjusted_window_size", return_value=(210, 120)):
            self.assertEqual(
                win_api.get_centered_window_position(123, 200, 100, client_size=True),
                ((1920 - 210) // 2, (1080 - 120) // 2),
            )


if __name__ == "__main__":
    unittest.main()
