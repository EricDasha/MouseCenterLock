import unittest
from pathlib import Path
from unittest import mock

import app_logging


class AppLoggingTests(unittest.TestCase):
    def setUp(self):
        self.log_path = Path(__file__).resolve().parent / f"_tmp_app_logging_{self._testMethodName}.log"
        if self.log_path.exists():
            try:
                self.log_path.unlink()
            except PermissionError:
                pass

    def tearDown(self):
        app_logging.configure_logging(False)
        if self.log_path.exists():
            try:
                self.log_path.unlink()
            except PermissionError:
                pass

    def test_log_message_does_not_create_file_when_disabled(self):
        with mock.patch("app_logging.get_log_path", return_value=self.log_path):
            app_logging.configure_logging(False)
            app_logging.log_message("disabled log")

        self.assertFalse(self.log_path.exists())

    def test_log_message_writes_file_when_enabled(self):
        with mock.patch("app_logging.get_log_path", return_value=self.log_path):
            app_logging.configure_logging(True)
            app_logging.log_message("enabled log")

        self.assertTrue(self.log_path.exists())
        self.assertIn("enabled log", self.log_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
