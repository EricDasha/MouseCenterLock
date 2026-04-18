import json
import os
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import settings_manager


class SettingsManagerTests(unittest.TestCase):
    def _workspace_temp_dir(self, name: str) -> Path:
        temp_dir = Path("tests_tmp") / name
        temp_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: __import__("shutil").rmtree(temp_dir, ignore_errors=True))
        return temp_dir

    def test_migrates_legacy_clicker_config_into_profiles(self):
        temp_dir = self._workspace_temp_dir("settings_migrate")
        config_path = temp_dir / "Mconfig.json"
        legacy_path = temp_dir / "config.json"
        default_path = temp_dir / "default.json"
        legacy_path.write_text(json.dumps({
            "clicker": {
                "enabled": True,
                "button": "right",
                "intervalMs": 75,
                "hotkeyToggle": {
                    "modCtrl": False,
                    "modAlt": False,
                    "modShift": False,
                    "modWin": False,
                    "key": "F8",
                },
            }
        }, ensure_ascii=False), encoding="utf-8")

        with mock.patch.object(settings_manager, "CONFIG_PATH", str(config_path)), \
             mock.patch.object(settings_manager, "LEGACY_CONFIG_PATH", str(legacy_path)), \
             mock.patch.object(settings_manager, "CONFIG_DEFAULT_PATH", str(default_path)):
            settings = settings_manager.SettingsManager()

        profiles = settings.data["clickerProfiles"]
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["id"], "default")
        self.assertEqual(profiles[0]["button"], "right")
        self.assertTrue(profiles[0]["enabled"])
        self.assertEqual(profiles[0]["triggers"]["toggleHotkey"]["key"], "F8")
        self.assertEqual(settings.data["activeClickerProfileId"], "default")

    def test_save_prunes_runtime_clicker_mirrors(self):
        temp_dir = self._workspace_temp_dir("settings_save")
        config_path = temp_dir / "Mconfig.json"
        legacy_path = temp_dir / "config.json"
        default_path = temp_dir / "default.json"

        with mock.patch.object(settings_manager, "CONFIG_PATH", str(config_path)), \
             mock.patch.object(settings_manager, "LEGACY_CONFIG_PATH", str(legacy_path)), \
             mock.patch.object(settings_manager, "CONFIG_DEFAULT_PATH", str(default_path)):
            settings = settings_manager.SettingsManager()
            settings.data["clicker"] = {"legacy": True}
            settings.data["clickerActiveProfile"] = {"legacy": True}
            self.assertTrue(settings.save(), msg=settings.last_error)

        payload = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertNotIn("clicker", payload)
        self.assertNotIn("clickerActiveProfile", payload)

    def test_clicker_profile_crud_keeps_valid_active_profile(self):
        settings = settings_manager.SettingsManager.__new__(settings_manager.SettingsManager)
        settings.loaded_from_path = ""
        settings.last_error = ""
        settings.data = {}
        settings._set_defaults()

        self.assertNotIn("clicker", settings.data)
        self.assertNotIn("clickerActiveProfile", settings.data)

        created = settings.create_clicker_profile("测试方案")
        self.assertEqual(len(settings.data["clickerProfiles"]), 2)
        self.assertEqual(settings.data["activeClickerProfileId"], created["id"])
        self.assertNotIn("clicker", settings.data)
        self.assertNotIn("clickerActiveProfile", settings.data)

        remaining = settings.delete_clicker_profile(created["id"])
        self.assertEqual(len(settings.data["clickerProfiles"]), 1)
        self.assertEqual(remaining["id"], "default")
        self.assertEqual(settings.data["activeClickerProfileId"], "default")
        self.assertNotIn("clicker", settings.data)
        self.assertNotIn("clickerActiveProfile", settings.data)

    def test_profile_default_names_follow_language(self):
        settings = settings_manager.SettingsManager.__new__(settings_manager.SettingsManager)
        settings.loaded_from_path = ""
        settings.last_error = ""
        settings.data = {"language": "en"}
        settings._set_defaults()

        self.assertEqual(settings.get_active_clicker_profile()["name"], "Default Profile")
        created = settings.create_clicker_profile("")
        self.assertTrue(created["name"].startswith("New Profile "))


if __name__ == "__main__":
    unittest.main()
