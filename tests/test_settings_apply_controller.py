import os
import types
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from services.settings_apply_controller import SettingsApplyController


class SettingsApplyControllerTests(unittest.TestCase):
    def test_apply_runs_save_and_runtime_refresh_flow(self):
        calls = []
        settings = types.SimpleNamespace(
            data={},
            upsert_clicker_profile=lambda profile: calls.append(("upsert", profile)),
        )
        controller = SettingsApplyController(
            settings=settings,
            collect_general_form_data=lambda: {"startup": {"launchOnBoot": True}},
            collect_clicker_profile_data=lambda: {"id": "p1"},
            apply_general_form_data=lambda s, data: calls.append(("apply_general", data)),
            set_startup=lambda enabled: calls.append(("set_startup", enabled)) or True,
            get_startup_enabled=lambda: True,
            save_settings=lambda context: calls.append(("save_settings", context)) or True,
            sync_lock_runtime=lambda: calls.append("sync_lock"),
            get_active_clicker_profile=lambda: {"enabled": True},
            stop_clicker=lambda **kwargs: calls.append(("stop_clicker", kwargs)),
            sync_clicker_runtime=lambda: calls.append("sync_clicker"),
            unregister_hotkeys=lambda: calls.append("unregister_hotkeys"),
            register_hotkeys=lambda data: (calls.append(("register_hotkeys", data)) or True, []),
            on_hotkey_conflict=lambda errors: calls.append(("hotkey_conflict", errors)),
            apply_theme=lambda: calls.append("apply_theme"),
            refresh_ui=lambda: calls.append("refresh_ui"),
            refresh_profiles=lambda: calls.append("refresh_profiles"),
            show_saved_feedback=lambda: calls.append("show_saved_feedback"),
        )

        result = controller.apply(show_feedback=True)

        self.assertTrue(result)
        self.assertEqual(settings.data["startup"]["launchOnBoot"], True)
        self.assertEqual(
            calls,
            [
                ("apply_general", {"startup": {"launchOnBoot": True}}),
                ("upsert", {"id": "p1"}),
                ("set_startup", True),
                ("save_settings", "Applying settings from the advanced page"),
                "sync_lock",
                "sync_clicker",
                "unregister_hotkeys",
                ("register_hotkeys", settings.data),
                "apply_theme",
                "refresh_ui",
                "refresh_profiles",
                "show_saved_feedback",
            ],
        )

    def test_apply_stops_clicker_when_profile_disabled(self):
        calls = []
        settings = types.SimpleNamespace(
            data={},
            upsert_clicker_profile=lambda profile: calls.append(("upsert", profile)),
        )
        controller = SettingsApplyController(
            settings=settings,
            collect_general_form_data=lambda: {"startup": {"launchOnBoot": False}},
            collect_clicker_profile_data=lambda: {"id": "p2"},
            apply_general_form_data=lambda s, data: None,
            set_startup=lambda enabled: True,
            get_startup_enabled=lambda: False,
            save_settings=lambda context: True,
            sync_lock_runtime=lambda: calls.append("sync_lock"),
            get_active_clicker_profile=lambda: {"enabled": False},
            stop_clicker=lambda **kwargs: calls.append(("stop_clicker", kwargs)),
            sync_clicker_runtime=lambda: calls.append("sync_clicker"),
            unregister_hotkeys=lambda: calls.append("unregister_hotkeys"),
            register_hotkeys=lambda data: (True, []),
            on_hotkey_conflict=lambda errors: calls.append(("hotkey_conflict", errors)),
            apply_theme=lambda: calls.append("apply_theme"),
            refresh_ui=lambda: calls.append("refresh_ui"),
            refresh_profiles=lambda: calls.append("refresh_profiles"),
            show_saved_feedback=lambda: calls.append("show_saved_feedback"),
        )

        controller.apply(show_feedback=False)

        self.assertIn(("stop_clicker", {"show_message": False}), calls)
        self.assertNotIn("sync_clicker", calls)
        self.assertNotIn("show_saved_feedback", calls)


if __name__ == "__main__":
    unittest.main()
