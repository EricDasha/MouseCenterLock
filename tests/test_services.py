import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from services.clicker_service import ClickerService
from services.input_backends import get_backend_status, all_backend_statuses
from services.input_service import InputService
from services.lock_service import LockService
from services.macro_schema import normalize_macro_trigger_mode, normalize_mouse_button
from services.macro_service import MouseMacroService
from services.tray_service import TrayService


class _FakeInputListener:
    def __init__(self, **_kwargs):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True
        return True

    def stop(self):
        self.stopped = True


class _FakeInputService:
    def __init__(self):
        self.clicks = []
        self.keys = []
        self.hotkeys = []
        self.texts = []
        self.key_downs = []
        self.key_ups = []

    def click_mouse(self, button="left"):
        self.clicks.append(button)

    def mouse_down(self, button="left"):
        self.clicks.append(f"{button}:down")

    def mouse_up(self, button="left"):
        self.clicks.append(f"{button}:up")

    def press_key(self, key):
        self.keys.append(key)

    def key_down(self, key):
        self.key_downs.append(key)

    def key_up(self, key):
        self.key_ups.append(key)

    def press_hotkey(self, action):
        self.hotkeys.append(action)

    def type_text(self, text):
        self.texts.append(text)


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


    def test_input_service_prefers_rust_backend_for_sendinput_clicks(self):
        service = InputService(get_backend=lambda: "sendinput")

        with mock.patch("services.input_service.native_input.click_mouse", return_value=True) as native_click, \
             mock.patch("services.input_service.sendinput_click_mouse") as python_click:
            service.click_mouse("right")

        native_click.assert_called_once_with("right")
        python_click.assert_not_called()

    def test_input_service_falls_back_when_rust_backend_unavailable(self):
        service = InputService(get_backend=lambda: "native-sendinput")

        with mock.patch("services.input_service.native_input.press_vk", return_value=False) as native_press, \
             mock.patch("services.input_service.key_to_vk", return_value=0x41), \
             mock.patch("services.input_service.sendinput_press_vk") as python_press:
            service.press_key("A")

        native_press.assert_called_once_with(0x41)
        python_press.assert_called_once_with(0x41)

    def test_input_service_key_down_up_use_native_then_python_fallback(self):
        service = InputService(get_backend=lambda: "native-sendinput")

        with mock.patch("services.input_service.key_to_vk", return_value=0x32), \
             mock.patch("services.input_service.native_input.key_down_vk", return_value=True) as native_down, \
             mock.patch("services.input_service.native_input.key_up_vk", return_value=False) as native_up, \
             mock.patch("services.input_service.key_down_vk") as python_down, \
             mock.patch("services.input_service.key_up_vk") as python_up:
            service.key_down("2")
            service.key_up("2")

        native_down.assert_called_once_with(0x32)
        native_up.assert_called_once_with(0x32)
        python_down.assert_not_called()
        python_up.assert_called_once_with(0x32)

    def test_input_service_mouse_down_up_use_native_then_python_fallback(self):
        service = InputService(get_backend=lambda: "native-sendinput")

        with mock.patch("services.input_service.native_input.mouse_down", return_value=True) as native_down, \
             mock.patch("services.input_service.native_input.mouse_up", return_value=False) as native_up, \
             mock.patch("services.input_service.sendinput_mouse_down") as python_down, \
             mock.patch("services.input_service.sendinput_mouse_up") as python_up:
            service.mouse_down("left")
            service.mouse_up("left")

        native_down.assert_called_once_with("left")
        native_up.assert_called_once_with("left")
        python_down.assert_not_called()
        python_up.assert_called_once_with("left")

    def test_macro_schema_normalizes_buttons_and_trigger_modes(self):
        self.assertEqual(normalize_mouse_button("Back"), "x1")
        self.assertEqual(normalize_mouse_button("button5"), "x2")
        self.assertEqual(normalize_mouse_button("unknown", "middle"), "middle")

        self.assertEqual(normalize_macro_trigger_mode("holdLoop"), "holdLoop")
        self.assertEqual(normalize_macro_trigger_mode("holdloop"), "holdLoop")
        self.assertEqual(normalize_macro_trigger_mode("toggle-loop"), "toggleLoop")
        self.assertEqual(normalize_macro_trigger_mode("bad", "toggle"), "toggle")

    def test_input_service_python_sendinput_skips_rust_backend(self):
        service = InputService(get_backend=lambda: "python-sendinput")

        with mock.patch("services.input_service.native_input.click_mouse", return_value=True) as native_click, \
             mock.patch("services.input_service.sendinput_click_mouse") as python_click:
            service.click_mouse("left")

        native_click.assert_not_called()
        python_click.assert_called_once_with("left")

    def test_input_service_virtual_hid_reserved_falls_back_to_native_path(self):
        service = InputService(
            get_backend=lambda: "virtual-hid",
            get_fallback_backend=lambda: "native-sendinput",
            get_fallback_policy=lambda: "auto",
        )

        with mock.patch("services.input_service.native_input.click_mouse", return_value=True) as native_click:
            service.click_mouse("left")

        native_click.assert_called_once_with("left")

    def test_input_service_virtual_hid_error_policy_does_not_silent_fallback(self):
        service = InputService(
            get_backend=lambda: "virtual-hid",
            get_fallback_backend=lambda: "native-sendinput",
            get_fallback_policy=lambda: "error",
        )

        with mock.patch("services.input_service.native_input.click_mouse", return_value=True) as native_click, \
             mock.patch("services.input_service.sendinput_click_mouse") as python_click:
            service.click_mouse("left")

        native_click.assert_not_called()
        python_click.assert_not_called()

    def test_input_backend_registry_reports_virtual_hid_unavailable(self):
        status = get_backend_status("virtual-hid")
        self.assertEqual(status.name, "virtual-hid")
        self.assertFalse(status.available)
        self.assertIn(status.reason, {"driver_not_installed", "unsupported_os"})
        self.assertTrue(status.capabilities.supportsKeyboard)
        self.assertIn("virtual-hid", all_backend_statuses())

    def test_input_service_prefers_rust_unicode_text(self):
        service = InputService(get_backend=lambda: "sendinput")

        with mock.patch("services.input_service.native_input.type_text", return_value=True) as native_type, \
             mock.patch("services.input_service.user32.VkKeyScanW") as vk_scan:
            service.type_text("Hello 玄")

        native_type.assert_called_once_with("Hello 玄")
        vk_scan.assert_not_called()

    def test_input_service_falls_back_text_per_character(self):
        service = InputService(get_backend=lambda: "sendinput")

        with mock.patch("services.input_service.native_input.type_text", return_value=False), \
             mock.patch("services.input_service.user32.VkKeyScanW", return_value=0x41), \
             mock.patch("services.input_service.native_input.press_vk", return_value=False), \
             mock.patch("services.input_service.sendinput_press_vk") as python_press:
            service.type_text("A")

        python_press.assert_called_once_with(0x41)


    def test_mouse_macro_service_alias_and_repeated_press_edges(self):
        config = {
            "enabled": True,
            "source": "builder",
            "rules": [
                {
                    "id": "back-left",
                    "enabled": True,
                    "holdMouseButton": "back",
                    "pressMouseButton": "left",
                    "actions": [{"type": "mouseClick", "button": "right"}],
                }
            ],
        }
        input_service = _FakeInputService()
        service = MouseMacroService(
            get_config=lambda: config,
            input_listener_factory=_FakeInputListener,
            input_service=input_service,
        )
        service._poll_timer.stop()

        service._on_global_input_event("mouse", "x1", True)
        service._on_global_input_event("mouse", "left", True)
        service._on_global_input_event("mouse", "left", True)
        self.assertEqual(input_service.clicks, ["right"])

        service._on_global_input_event("mouse", "left", False)
        service._on_global_input_event("mouse", "left", True)
        self.assertEqual(input_service.clicks, ["right", "right"])

        service.stop()

    def test_mouse_macro_cancel_on_hold_release_ignores_press_release_by_default(self):
        config = {
            "enabled": True,
            "source": "builder",
            "rules": [
                {
                    "id": "hold-left",
                    "enabled": True,
                    "holdMouseButton": "x1",
                    "pressMouseButton": "left",
                    "cancelOnHoldRelease": True,
                    "actions": [{"type": "key", "key": "2"}],
                }
            ],
        }
        service = MouseMacroService(
            get_config=lambda: config,
            input_listener_factory=_FakeInputListener,
            input_service=_FakeInputService(),
        )
        service._poll_timer.stop()

        try:
            rule = config["rules"][0]
            service._current_rule = rule
            self.assertFalse(service._current_rule_cancel_matches("mouse", "left"))
            self.assertTrue(service._current_rule_cancel_matches("mouse", "x1"))
            rule["cancelOnPressRelease"] = True
            self.assertTrue(service._current_rule_cancel_matches("mouse", "left"))
        finally:
            service.stop()

    def test_mouse_macro_service_honors_cooldown_between_triggers(self):
        config = {
            "enabled": True,
            "source": "builder",
            "rules": [
                {
                    "id": "x1-switch",
                    "enabled": True,
                    "pressMouseButton": "x1",
                    "cooldownMs": 300,
                    "actions": [{"type": "key", "key": "2"}],
                }
            ],
        }
        input_service = _FakeInputService()
        service = MouseMacroService(
            get_config=lambda: config,
            input_listener_factory=_FakeInputListener,
            input_service=input_service,
        )
        service._poll_timer.stop()

        try:
            with mock.patch('services.macro_service.time.monotonic', side_effect=[1.0, 1.05, 1.10, 1.40, 1.41]):
                service._on_global_input_event('mouse', 'x1', True)
                service._on_global_input_event('mouse', 'x1', False)
                service._on_global_input_event('mouse', 'x1', True)
                service._on_global_input_event('mouse', 'x1', False)
                service._on_global_input_event('mouse', 'x1', True)

            self.assertEqual(input_service.keys, ["2", "2"])
        finally:
            service.stop()

    def test_mouse_macro_service_supports_press_only_mouse_rule(self):
        config = {
            "enabled": True,
            "source": "builder",
            "rules": [
                {
                    "id": "x1-switch",
                    "enabled": True,
                    "pressMouseButton": "x1",
                    "actions": [
                        {"type": "keyDown", "key": "2"},
                        {"type": "keyUp", "key": "2"},
                    ],
                }
            ],
        }
        input_service = _FakeInputService()
        service = MouseMacroService(
            get_config=lambda: config,
            input_listener_factory=_FakeInputListener,
            input_service=input_service,
        )
        service._poll_timer.stop()

        try:
            service._on_global_input_event("mouse", "x1", True)
            self.assertEqual(input_service.key_downs, ["2"])
            self.assertEqual(input_service.key_ups, ["2"])
        finally:
            service.stop()

    def test_mouse_macro_service_supports_key_down_up_actions(self):
        input_service = _FakeInputService()
        service = MouseMacroService(
            get_config=lambda: {"enabled": True, "source": "builder", "rules": []},
            input_listener_factory=_FakeInputListener,
            input_service=input_service,
        )
        service._poll_timer.stop()

        try:
            service._execute_actions([
                {"type": "keyDown", "key": "2"},
                {"type": "delay", "ms": 0},
                {"type": "keyDown", "key": "1"},
                {"type": "keyUp", "key": "2"},
                {"type": "keyUp", "key": "1"},
            ], rule={"interruptible": True}, rule_key="test:mouse:left")

            self.assertEqual(input_service.key_downs, ["2", "1"])
            self.assertEqual(input_service.key_ups, ["2", "1"])
            self.assertEqual(service._held_output_keys, [])
        finally:
            service.stop()

    def test_mouse_macro_service_supports_toggle_arm_and_fire(self):
        config = {
            "enabled": True,
            "source": "builder",
            "rules": [
                {
                    "id": "toggle-left",
                    "enabled": True,
                    "triggerMode": "toggle",
                    "holdMouseButton": "x1",
                    "pressMouseButton": "left",
                    "actions": [{"type": "key", "key": "2"}],
                }
            ],
        }
        input_service = _FakeInputService()
        service = MouseMacroService(
            get_config=lambda: config,
            input_listener_factory=_FakeInputListener,
            input_service=input_service,
        )
        service._poll_timer.stop()

        try:
            service._on_global_input_event("mouse", "x1", True)
            service._on_global_input_event("mouse", "x1", False)
            service._on_global_input_event("mouse", "left", True)
            self.assertEqual(input_service.keys, ["2"])

            service._on_global_input_event("mouse", "x1", True)
            service._on_global_input_event("mouse", "x1", False)
            service._on_global_input_event("mouse", "left", True)
            self.assertEqual(input_service.keys, ["2"])
        finally:
            service.stop()

    def test_mouse_macro_service_supports_hold_loop_until_release(self):
        config = {
            "enabled": True,
            "source": "builder",
            "rules": [
                {
                    "id": "hold-loop",
                    "enabled": True,
                    "triggerMode": "holdLoop",
                    "holdMouseButton": "x1",
                    "actions": [{"type": "key", "key": "2"}],
                }
            ],
        }
        input_service = _FakeInputService()
        service = MouseMacroService(
            get_config=lambda: config,
            input_listener_factory=_FakeInputListener,
            input_service=input_service,
        )
        service._poll_timer.stop()
        service._loop_timer.stop()

        try:
            service._on_global_input_event("mouse", "x1", True)
            service._run_loop_tick()
            service._run_loop_tick()
            self.assertEqual(input_service.keys, ["2", "2"])

            service._on_global_input_event("mouse", "x1", False)
            service._run_loop_tick()
            self.assertEqual(input_service.keys, ["2", "2"])
        finally:
            service.stop()

    def test_mouse_macro_service_supports_toggle_loop_until_second_press(self):
        config = {
            "enabled": True,
            "source": "builder",
            "rules": [
                {
                    "id": "toggle-loop",
                    "enabled": True,
                    "triggerMode": "toggleLoop",
                    "holdMouseButton": "x1",
                    "actions": [{"type": "key", "key": "1"}],
                }
            ],
        }
        input_service = _FakeInputService()
        service = MouseMacroService(
            get_config=lambda: config,
            input_listener_factory=_FakeInputListener,
            input_service=input_service,
        )
        service._poll_timer.stop()
        service._loop_timer.stop()

        try:
            service._on_global_input_event("mouse", "x1", True)
            service._run_loop_tick()
            service._run_loop_tick()
            self.assertEqual(input_service.keys, ["1", "1"])

            service._on_global_input_event("mouse", "x1", False)
            service._on_global_input_event("mouse", "x1", True)
            service._run_loop_tick()
            self.assertEqual(input_service.keys, ["1", "1"])
        finally:
            service.stop()

    def test_mouse_macro_service_supports_mouse_down_up_actions(self):
        input_service = _FakeInputService()
        service = MouseMacroService(
            get_config=lambda: {"enabled": True, "source": "builder", "rules": []},
            input_listener_factory=_FakeInputListener,
            input_service=input_service,
        )
        service._poll_timer.stop()

        try:
            service._execute_actions([
                {"type": "mouseDown", "button": "left"},
                {"type": "delay", "ms": 10},
                {"type": "mouseUp", "button": "left"},
            ], rule={"interruptible": True}, rule_key="test:mouse:left")

            self.assertEqual(input_service.clicks, ["left:down", "left:up"])
        finally:
            service.stop()

    def test_mouse_macro_service_releases_key_down_on_cleanup(self):
        input_service = _FakeInputService()
        service = MouseMacroService(
            get_config=lambda: {"enabled": True, "source": "builder", "rules": []},
            input_listener_factory=_FakeInputListener,
            input_service=input_service,
        )
        service._poll_timer.stop()

        try:
            service._execute_actions([
                {"type": "keyDown", "key": "2"},
            ], rule={"interruptible": True}, rule_key="test:mouse:left")

            self.assertEqual(input_service.key_downs, ["2"])
            self.assertEqual(input_service.key_ups, ["2"])
            self.assertEqual(service._held_output_keys, [])
        finally:
            service.stop()



    def test_mouse_macro_service_loads_external_json_rules(self):
        import json
        import tempfile
        import os

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as file:
            json.dump({
                "rules": [{
                    "id": "external-middle-left",
                    "enabled": True,
                    "holdMouseButton": "middle",
                    "pressMouseButton": "left",
                    "actions": [{"type": "key", "key": "2"}],
                }]
            }, file)
            path = file.name

        config = {"enabled": True, "source": "file", "configFile": path, "rules": []}
        service = MouseMacroService(get_config=lambda: config, input_listener_factory=_FakeInputListener)
        service._poll_timer.stop()

        try:
            with mock.patch.object(service, "_send_key") as send_key:
                service._on_global_input_event("mouse", "middle", True)
                service._on_global_input_event("mouse", "left", True)
                send_key.assert_called_once_with("2")
        finally:
            service.stop()
            os.unlink(path)

    def test_mouse_macro_service_supports_hold_key_press_mouse(self):
        config = {
            "enabled": True,
            "source": "builder",
            "rules": [
                {
                    "id": "alt-left",
                    "enabled": True,
                    "holdKey": "Alt",
                    "pressMouseButton": "left",
                    "actions": [{"type": "key", "key": "1"}],
                }
            ],
        }
        service = MouseMacroService(get_config=lambda: config, input_listener_factory=_FakeInputListener)
        service._poll_timer.stop()

        with mock.patch.object(service, "_send_key") as send_key:
            service._on_global_input_event("key", "Alt", True)
            service._on_global_input_event("mouse", "left", True)
            send_key.assert_called_once_with("1")

            service._on_global_input_event("mouse", "left", False)
            service._on_global_input_event("mouse", "left", True)
            self.assertEqual(send_key.call_count, 2)

        service.stop()

    def test_mouse_macro_service_supports_hold_key_press_key_repeat(self):
        config = {
            "enabled": True,
            "source": "builder",
            "rules": [
                {
                    "id": "a-b",
                    "enabled": True,
                    "holdKey": "A",
                    "pressKey": "B",
                    "actions": [{"type": "key", "key": "1"}],
                }
            ],
        }
        service = MouseMacroService(get_config=lambda: config, input_listener_factory=_FakeInputListener)
        service._poll_timer.stop()

        with mock.patch.object(service, "_send_key") as send_key:
            service._on_global_input_event("key", "A", True)
            service._on_global_input_event("key", "B", True)
            service._on_global_input_event("key", "B", True)
            send_key.assert_called_once_with("1")

            service._on_global_input_event("key", "B", False)
            service._on_global_input_event("key", "B", True)
            self.assertEqual(send_key.call_count, 2)

        service.stop()

    def test_mouse_macro_service_executes_delay_between_actions(self):
        config = {"enabled": True, "source": "builder", "rules": []}
        service = MouseMacroService(get_config=lambda: config, input_listener_factory=_FakeInputListener)
        service._poll_timer.stop()

        with mock.patch.object(service, "_send_key") as send_key, \
             mock.patch("services.macro_service.time.sleep") as sleep:
            service._execute_actions([
                {"type": "key", "key": "A"},
                {"type": "delay", "ms": 50},
                {"type": "key", "key": "B"},
            ])

        self.assertEqual(send_key.mock_calls, [mock.call("A"), mock.call("B")])
        self.assertEqual(sleep.mock_calls, [mock.call(0.025), mock.call(0.025)])
        service.stop()

    def test_mouse_macro_service_interruptible_rule_can_cancel_scheduler(self):
        config = {"enabled": True, "source": "builder", "rules": []}
        service = MouseMacroService(get_config=lambda: config, input_listener_factory=_FakeInputListener)
        service._poll_timer.stop()
        with mock.patch.object(service, "_send_key") as send_key, \
             mock.patch.object(service, "_should_cancel_actions", return_value=True):
            service._execute_actions(
                [{"type": "key", "key": "A"}],
                rule={"interruptible": True, "cancelOnHoldRelease": True},
                rule_key="cancel:key:a",
            )

        send_key.assert_not_called()
        service.stop()

    def test_mouse_macro_service_runs_combo_rule_once_until_release(self):
        config = {
            "enabled": True,
            "source": "builder",
            "rules": [
                {
                    "id": "copy",
                    "enabled": True,
                    "holdMouseButton": "x2",
                    "pressMouseButton": "left",
                    "actions": [{"type": "mouseClick", "button": "right"}],
                }
            ],
        }
        input_service = _FakeInputService()
        service = MouseMacroService(
            get_config=lambda: config,
            input_listener_factory=_FakeInputListener,
            input_service=input_service,
        )

        service._on_global_input_event("mouse", "x2", True)
        service._on_global_input_event("mouse", "left", True)
        service._on_global_input_event("mouse", "left", True)
        self.assertEqual(input_service.clicks, ["right"])

        service._on_global_input_event("mouse", "left", False)
        service._on_global_input_event("mouse", "left", True)
        self.assertEqual(input_service.clicks, ["right", "right"])

        service.stop()

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
            input_listener_factory=_FakeInputListener,
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

    def test_clicker_service_hold_key_starts_and_stops_immediately(self):
        profile = {
            "enabled": True,
            "button": "left",
            "intervalMs": 25,
            "sound": {"enabled": False, "preset": "systemAsterisk", "customFile": ""},
            "triggers": {
                "mode": "holdKey",
                "holdKey": {
                    "modCtrl": True,
                    "modAlt": False,
                    "modShift": False,
                    "modWin": False,
                    "key": "F7",
                },
            },
        }
        click_mouse = mock.Mock()
        service = ClickerService(
            get_profile=lambda: profile,
            on_state_changed=lambda: None,
            on_notify_started=lambda _profile: None,
            on_notify_stopped=lambda _profile: None,
            sound_presets={"systemAsterisk": 0x40},
            click_mouse_func=click_mouse,
            input_listener_factory=_FakeInputListener,
        )

        service._on_global_input_event("key", "ctrl", True)
        service._on_global_input_event("key", "f7", True)
        self.assertTrue(service.is_running)
        click_mouse.assert_called_once_with("left")

        service._on_global_input_event("key", "f7", False)
        self.assertFalse(service.is_running)

        service.hold_state_timer.stop()
        service.clicker_timer.stop()

    def test_clicker_service_hold_mouse_button_starts_and_stops(self):
        profile = {
            "enabled": True,
            "button": "middle",
            "intervalMs": 25,
            "sound": {"enabled": False, "preset": "systemAsterisk", "customFile": ""},
            "triggers": {
                "mode": "holdMouseButton",
                "holdMouseButton": "x1",
            },
        }
        click_mouse = mock.Mock()
        service = ClickerService(
            get_profile=lambda: profile,
            on_state_changed=lambda: None,
            on_notify_started=lambda _profile: None,
            on_notify_stopped=lambda _profile: None,
            sound_presets={"systemAsterisk": 0x40},
            click_mouse_func=click_mouse,
            input_listener_factory=_FakeInputListener,
        )

        service._on_global_input_event("mouse", "x1", True)
        self.assertTrue(service.is_running)
        click_mouse.assert_called_once_with("middle")

        service._on_global_input_event("mouse", "x1", False)
        self.assertFalse(service.is_running)

        service.hold_state_timer.stop()
        service.clicker_timer.stop()

    def test_clicker_service_process_blacklist_blocks_side_button_trigger(self):
        profile = {
            "enabled": True,
            "button": "left",
            "intervalMs": 25,
            "processBlacklist": ["steam.exe"],
            "sound": {"enabled": False, "preset": "systemAsterisk", "customFile": ""},
            "triggers": {
                "mode": "holdMouseButton",
                "holdMouseButton": "x1",
            },
        }
        click_mouse = mock.Mock()
        service = ClickerService(
            get_profile=lambda: profile,
            on_state_changed=lambda: None,
            on_notify_started=lambda _profile: None,
            on_notify_stopped=lambda _profile: None,
            sound_presets={"systemAsterisk": 0x40},
            click_mouse_func=click_mouse,
            input_listener_factory=_FakeInputListener,
        )

        try:
            with mock.patch("services.clicker_service.get_active_window_info", return_value=(123, "Steam")), \
                 mock.patch("services.clicker_service.get_window_process_name", return_value="steam.exe"):
                service._on_global_input_event("mouse", "x1", True)
                self.assertFalse(service.is_running)
                click_mouse.assert_not_called()
        finally:
            service.hold_state_timer.stop()
            service.clicker_timer.stop()

    def test_clicker_service_falls_back_to_polling_when_hook_unavailable(self):
        class _FailedInputListener(_FakeInputListener):
            def start(self):
                self.started = True
                return False

        profile = {
            "enabled": True,
            "button": "left",
            "intervalMs": 25,
            "sound": {"enabled": False, "preset": "systemAsterisk", "customFile": ""},
            "triggers": {
                "mode": "holdKey",
                "holdKey": {
                    "modCtrl": False,
                    "modAlt": False,
                    "modShift": False,
                    "modWin": False,
                    "key": "F7",
                },
            },
        }
        click_mouse = mock.Mock()
        service = ClickerService(
            get_profile=lambda: profile,
            on_state_changed=lambda: None,
            on_notify_started=lambda _profile: None,
            on_notify_stopped=lambda _profile: None,
            sound_presets={"systemAsterisk": 0x40},
            click_mouse_func=click_mouse,
            input_listener_factory=_FailedInputListener,
        )

        self.assertTrue(service.hold_state_timer.isActive())
        with mock.patch.object(service, "_modifier_pressed", side_effect=lambda vk: vk == 0x76):
            service._poll_hold_trigger_state()
            self.assertTrue(service.is_running)
            click_mouse.assert_called_once_with("left")

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
        self.assertTrue(service._check_match("Minecraft 1.20", "javaw.exe", ["javaw"]))
        self.assertTrue(service._check_match("Minecraft 1.20", "javaw.exe", ["minecraft"]))
        self.assertFalse(service._check_match("Notepad", "notepad.exe", ["qq.exe"]))

        service.window_focus_timer.stop()
        service.recenter_timer.stop()

    def test_lock_service_manual_lock_respects_window_specific_gate(self):
        settings = {
            "windowSpecific": {
                "enabled": True,
                "autoLockOnWindowFocus": False,
                "targetWindows": ["game.exe"],
                "resumeAfterWindowSwitch": False,
            },
            "position": {"mode": "custom", "customX": 111, "customY": 222},
            "recenter": {"enabled": True, "intervalMs": 250},
        }
        service = LockService(
            get_settings=lambda: settings,
            on_state_changed=lambda: None,
            on_notify_locked=lambda: None,
            on_notify_unlocked=lambda: None,
            on_error=lambda op, exc: None,
        )
        try:
            with mock.patch.object(service, "_should_lock_for_window", return_value=False), \
                 mock.patch("services.lock_service.set_cursor_to") as set_cursor, \
                 mock.patch("services.lock_service.clip_cursor_to_point") as clip_cursor:
                service.lock(manual=True)
                self.assertFalse(service.is_locked)
                set_cursor.assert_not_called()
                clip_cursor.assert_not_called()
        finally:
            service.window_focus_timer.stop()
            service.recenter_timer.stop()

    def test_lock_service_manual_lock_in_target_is_released_outside_target(self):
        settings = {
            "windowSpecific": {
                "enabled": True,
                "autoLockOnWindowFocus": False,
                "targetWindows": ["game.exe"],
                "resumeAfterWindowSwitch": False,
            },
            "position": {"mode": "custom", "customX": 111, "customY": 222},
            "recenter": {"enabled": False, "intervalMs": 250},
        }
        service = LockService(
            get_settings=lambda: settings,
            on_state_changed=lambda: None,
            on_notify_locked=lambda: None,
            on_notify_unlocked=lambda: None,
            on_error=lambda op, exc: None,
        )
        try:
            with mock.patch.object(service, "_should_lock_for_window", return_value=True), \
                 mock.patch("services.lock_service.set_cursor_to"), \
                 mock.patch("services.lock_service.clip_cursor_to_point"):
                service.lock(manual=True)
                self.assertTrue(service.is_locked)
                self.assertFalse(service.is_force_lock)

            with mock.patch("services.lock_service.get_active_window_info", return_value=(303, "Notepad")), \
                 mock.patch("services.lock_service.get_window_process_name", return_value="notepad.exe"), \
                 mock.patch("services.lock_service.unclip_cursor") as unclip_cursor:
                service._check_window_focus()
                self.assertFalse(service.is_locked)
                unclip_cursor.assert_called_once()
        finally:
            service.window_focus_timer.stop()
            service.recenter_timer.stop()

    def test_lock_service_suspends_recenter_while_target_window_moves(self):
        settings = {
            "windowSpecific": {
                "enabled": True,
                "autoLockOnWindowFocus": False,
                "targetWindows": ["game.exe"],
                "resumeAfterWindowSwitch": False,
            },
            "position": {"mode": "custom", "customX": 111, "customY": 222},
            "recenter": {"enabled": True, "intervalMs": 250},
        }
        service = LockService(
            get_settings=lambda: settings,
            on_state_changed=lambda: None,
            on_notify_locked=lambda: None,
            on_notify_unlocked=lambda: None,
            on_error=lambda op, exc: None,
        )
        try:
            service._locked = True
            service._last_target_position = (100, 100)
            with mock.patch.object(service, "_should_lock_for_window", return_value=True), \
                 mock.patch.object(service, "_get_target_position", return_value=(200, 200)), \
                 mock.patch("services.lock_service.is_primary_mouse_button_pressed", return_value=True), \
                 mock.patch("services.lock_service.unclip_cursor") as unclip_cursor, \
                 mock.patch("services.lock_service.set_cursor_to") as set_cursor, \
                 mock.patch("services.lock_service.clip_cursor_to_point") as clip_cursor:
                service._on_recenter_tick()
                unclip_cursor.assert_called_once()
                set_cursor.assert_not_called()
                clip_cursor.assert_not_called()
                self.assertEqual(service._last_target_position, (200, 200))
        finally:
            service.window_focus_timer.stop()
            service.recenter_timer.stop()

    def test_lock_service_auto_lock_tracks_window_changes_by_hwnd_and_process(self):
        settings = {
            "windowSpecific": {
                "enabled": True,
                "autoLockOnWindowFocus": True,
                "targetWindows": ["Minecraft"],
                "resumeAfterWindowSwitch": False,
            },
            "position": {"mode": "custom", "customX": 111, "customY": 222},
            "recenter": {"enabled": False, "intervalMs": 250},
        }
        service = LockService(
            get_settings=lambda: settings,
            on_state_changed=lambda: None,
            on_notify_locked=lambda: None,
            on_notify_unlocked=lambda: None,
            on_error=lambda op, exc: None,
        )
        try:
            with mock.patch.object(
                service,
                "lock",
                side_effect=lambda manual=False: setattr(service, "_locked", True),
            ) as lock_mock, mock.patch.object(
                service,
                "unlock",
                side_effect=lambda manual=False: setattr(service, "_locked", False),
            ) as unlock_mock, mock.patch(
                "services.lock_service.get_active_window_info",
                side_effect=[
                    (101, "Notepad"),
                    (202, "Minecraft"),
                    (303, "Notepad"),
                ],
            ), mock.patch(
                "services.lock_service.get_window_process_name",
                side_effect=["notepad.exe", "javaw.exe", "notepad.exe"],
            ):
                service._check_window_focus()
                service._check_window_focus()
                service._check_window_focus()

            lock_mock.assert_called_once_with(manual=False)
            unlock_mock.assert_called_once_with(manual=False)
        finally:
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
