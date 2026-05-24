"""
Mouse macro runtime service.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Set

from PySide6 import QtCore

from app_logging import log_exception, log_message
from services.action_scheduler import ActionScheduler
from services.input_service import InputService
from win_api import GlobalInputListener, key_to_vk, user32


MODIFIER_VKS = {
    "modCtrl": 0x11,
    "modAlt": 0x12,
    "modShift": 0x10,
    "modWin": 0x5B,
}

MOUSE_BUTTON_ALIASES = {
    "left": "left",
    "right": "right",
    "middle": "middle",
    "x1": "x1",
    "xbutton1": "x1",
    "button4": "x1",
    "back": "x1",
    "x2": "x2",
    "xbutton2": "x2",
    "button5": "x2",
    "forward": "x2",
}

MOUSE_BUTTON_VKS = {
    "left": 0x01,
    "right": 0x02,
    "middle": 0x04,
    "x1": 0x05,
    "x2": 0x06,
}


class MouseMacroService(QtCore.QObject):
    """Execute configured mouse/key combo macro rules from global input events.

    Rules primarily use ``holdMouseButton`` + ``pressMouseButton``. For advanced
    JSON files, ``holdKey`` + ``pressKey`` is also accepted. ``triggerMode`` can
    be ``hold`` or ``toggle``. Press/release edges are tracked so holding A and
    repeatedly pressing B repeatedly fires the rule.
    """

    inputEvent = QtCore.Signal(str, str, bool)

    def __init__(
        self,
        *,
        get_config: Callable[[], Dict[str, Any]],
        input_listener_factory: Callable[..., GlobalInputListener] = GlobalInputListener,
        input_service: InputService | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._get_config = get_config
        self._input_service = input_service or InputService()
        self._pressed_mouse_buttons: Set[str] = set()
        self._pressed_keys: Set[str] = set()
        self._active_rule_keys: Set[str] = set()
        self._executing = False
        self._cancel_requested = False
        self._current_rule: Dict[str, Any] | None = None
        self._current_rule_key = ""
        self._held_output_keys: list[str] = []
        self._last_rule_fire_at: dict[str, float] = {}
        self._toggled_rule_ids: Set[str] = set()
        self._rules_cache_key = None
        self._rules_cache: List[Dict[str, Any]] = []
        self._input_listener = input_listener_factory(
            on_key_event=self._emit_key_event,
            on_mouse_event=self._emit_mouse_event,
        )
        self.inputEvent.connect(self._on_global_input_event)
        self._hook_mode_active = self._input_listener.start()
        log_message(f"MouseMacroService started: hook_mode={self._hook_mode_active}")

        self._poll_timer = QtCore.QTimer(self)
        self._poll_timer.timeout.connect(self._poll_input_state)
        self.sync_runtime()

    def stop(self) -> None:
        """Remove global hooks and stop polling."""
        log_message("MouseMacroService stopping")
        self._poll_timer.stop()
        self._input_listener.stop()

    def sync_runtime(self) -> None:
        """Apply current runtime state and keep polling as a hook fallback."""
        config = self._get_config()
        log_message(
            f"MouseMacroService sync: enabled={bool(config.get('enabled', False))} "
            f"source={config.get('source')} configFile={config.get('configFile', '')}"
        )
        if not config.get("enabled", False):
            self._poll_timer.stop()
            self._pressed_mouse_buttons.clear()
            self._pressed_keys.clear()
            self._active_rule_keys.clear()
            self._toggled_rule_ids.clear()
            return
        if not self._poll_timer.isActive():
            self._poll_timer.start(12)
            log_message("MouseMacroService polling fallback active: interval=12ms")

    def _emit_key_event(self, key_name: str, is_pressed: bool) -> None:
        """Bridge low-level keyboard input into the Qt thread."""
        self.inputEvent.emit("key", key_name, is_pressed)

    def _emit_mouse_event(self, button_name: str, is_pressed: bool) -> None:
        """Bridge low-level mouse input into the Qt thread."""
        self.inputEvent.emit("mouse", button_name, is_pressed)

    def _on_global_input_event(self, event_type: str, name: str, is_pressed: bool) -> None:
        """Track input state and fire matching rules on press edges."""
        normalized = self._normalize_input_name(event_type, name)
        if not normalized:
            return
        if self._executing:
            if (
                not is_pressed
                and self._current_rule
                and self._current_rule.get("cancelOnHoldRelease")
                and self._current_rule_cancel_matches(event_type, normalized)
            ):
                self._cancel_requested = True
                log_message(f"MouseMacro cancellation requested during execution: {self._current_rule_key}")
            return

        target_set = self._pressed_mouse_buttons if event_type == "mouse" else self._pressed_keys
        if is_pressed:
            was_pressed = normalized in target_set
            target_set.add(normalized)
            if not was_pressed:
                log_message(f"MouseMacro input down: type={event_type} name={normalized}")
                self._handle_toggle_rules(event_type, normalized)
                self._fire_matching_rules(event_type, normalized)
        else:
            target_set.discard(normalized)
            log_message(f"MouseMacro input up: type={event_type} name={normalized}")
            suffix = f":{event_type}:{normalized}"
            self._active_rule_keys = {key for key in self._active_rule_keys if not key.endswith(suffix)}

    def _normalize_input_name(self, event_type: str, name: str) -> str:
        """Normalize mouse aliases and key names used by hooks/config files."""
        raw = str(name or "").strip().lower()
        if not raw:
            return ""
        if event_type == "mouse":
            return MOUSE_BUTTON_ALIASES.get(raw, raw)
        if event_type == "key":
            return raw
        return ""

    def _load_rules(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Load macro rules from builder config or an external JSON file."""
        if not config.get("enabled", False):
            return []
        if config.get("source") != "file":
            rules = config.get("rules", [])
            return rules if isinstance(rules, list) else []

        file_path = str(config.get("configFile", "") or "").strip()
        if not file_path:
            cache_key = ("file", "")
            if self._rules_cache_key != cache_key:
                log_message("MouseMacro external file source selected but configFile is empty")
                self._rules_cache_key = cache_key
                self._rules_cache = []
            return []

        path = Path(file_path)
        try:
            stat = path.stat()
            cache_key = ("file", str(path), stat.st_mtime_ns, stat.st_size)
        except Exception as exc:
            cache_key = ("file-error", str(path), str(exc))
            if self._rules_cache_key != cache_key:
                log_exception(f"MouseMacro external JSON is not accessible: {file_path}", exc)
                self._rules_cache_key = cache_key
                self._rules_cache = []
            return []

        if self._rules_cache_key == cache_key:
            return self._rules_cache

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            self._rules_cache_key = cache_key
            self._rules_cache = []
            log_exception(f"MouseMacro failed to load external JSON: {file_path}", exc)
            return []

        if isinstance(payload, list):
            rules = payload
        elif isinstance(payload, dict):
            rules = payload.get("rules", [])
        else:
            rules = []

        if not isinstance(rules, list):
            rules = []
        self._rules_cache_key = cache_key
        self._rules_cache = rules
        log_message(f"MouseMacro loaded external JSON rules: file={file_path} count={len(rules)}")
        return self._rules_cache

    def _rule_press_target(self, rule: Dict[str, Any]) -> tuple[str, str]:
        """Return (event_type, normalized_name) for a rule trigger press."""
        if "pressKey" in rule:
            return "key", self._normalize_input_name("key", str(rule.get("pressKey", "")))
        return "mouse", self._normalize_input_name("mouse", str(rule.get("pressMouseButton", "")))

    def _rule_hold_target(self, rule: Dict[str, Any]) -> tuple[str, str]:
        """Return (event_type, normalized_name) for a rule hold input."""
        if "holdKey" in rule:
            return "key", self._normalize_input_name("key", str(rule.get("holdKey", "")))
        if "holdMouseButton" in rule:
            return "mouse", self._normalize_input_name("mouse", str(rule.get("holdMouseButton", "")))
        return "", ""

    def _rule_hold_is_pressed(self, rule: Dict[str, Any], rule_id: str, _event_type: str) -> bool:
        """Return whether the hold side of a rule is currently pressed.

        Hold and press may be different input types, e.g. holdKey=Alt +
        pressMouseButton=left. Prefer explicit holdKey when present; otherwise
        use holdMouseButton.
        """
        if str(rule.get("triggerMode", "hold") or "hold").lower() == "toggle":
            return rule_id in self._toggled_rule_ids
        hold_type, hold_name = self._rule_hold_target(rule)
        if not hold_type or not hold_name:
            return True
        if hold_type == "key":
            return bool(hold_name and hold_name in self._pressed_keys)
        return bool(hold_name and hold_name in self._pressed_mouse_buttons)

    def _current_rule_cancel_matches(self, event_type: str, normalized: str) -> bool:
        """Return whether an input release should cancel the current interruptible rule."""
        if not self._current_rule:
            return False
        press_type, press_name = self._rule_press_target(self._current_rule)
        hold_type, hold_name = self._rule_hold_target(self._current_rule)
        if hold_type and hold_name and (event_type, normalized) == (hold_type, hold_name):
            return True
        if self._current_rule.get("cancelOnPressRelease"):
            return (event_type, normalized) == (press_type, press_name)
        return False

    def _handle_toggle_rules(self, event_type: str, normalized: str) -> None:
        """Flip toggle-mode rules on the trigger edge."""
        config = self._get_config()
        for index, rule in enumerate(self._load_rules(config)):
            if not isinstance(rule, dict) or not rule.get("enabled", False):
                continue
            if str(rule.get("triggerMode", "hold") or "hold").lower() != "toggle":
                continue
            toggle_type, toggle_name = self._rule_hold_target(rule)
            if (event_type, normalized) != (toggle_type, toggle_name):
                continue
            rule_id = str(rule.get("id") or index)
            if rule_id in self._toggled_rule_ids:
                self._toggled_rule_ids.discard(rule_id)
                log_message(f"MouseMacro toggle off: id={rule_id} trigger={event_type}:{normalized}")
                if self._executing and self._current_rule and str(self._current_rule.get("id") or "") == rule_id:
                    self._cancel_requested = True
                    log_message(f"MouseMacro toggle-off cancellation requested: {self._current_rule_key}")
            else:
                self._toggled_rule_ids.add(rule_id)
                log_message(f"MouseMacro toggle on: id={rule_id} trigger={event_type}:{normalized}")

    def _rule_is_armed(self, rule: Dict[str, Any], rule_id: str) -> bool:
        return str(rule.get("triggerMode", "hold") or "hold").lower() != "toggle" or rule_id in self._toggled_rule_ids

    def _fire_matching_rules(self, event_type: str, pressed_name: str) -> None:
        config = self._get_config()
        for index, rule in enumerate(self._load_rules(config)):
            if not isinstance(rule, dict) or not rule.get("enabled", False):
                continue
            press_type, press_name = self._rule_press_target(rule)
            if press_type != event_type or press_name != pressed_name:
                continue
            rule_id = str(rule.get("id") or index)
            if not self._rule_hold_is_pressed(rule, rule_id, event_type):
                log_message(
                    f"MouseMacro rule press matched but hold missing: id={rule_id} "
                    f"press={event_type}:{pressed_name}"
                )
                continue
            if not self._rule_is_armed(rule, rule_id):
                log_message(f"MouseMacro rule ignored until armed: id={rule_id} press={event_type}:{pressed_name}")
                continue
            rule_key = f"{rule_id}:{event_type}:{pressed_name}"
            rule_id = str(rule.get("id") or index)
            cooldown_ms = max(0, int(rule.get("cooldownMs", 0) or 0))
            if cooldown_ms > 0:
                last_fire = self._last_rule_fire_at.get(rule_id, 0.0)
                elapsed_ms = (time.monotonic() - last_fire) * 1000.0
                if elapsed_ms < cooldown_ms:
                    log_message(f"MouseMacro rule cooldown active: id={rule_id} elapsedMs={elapsed_ms:.0f} cooldownMs={cooldown_ms}")
                    continue
            if rule_key in self._active_rule_keys:
                log_message(f"MouseMacro rule suppressed until release: {rule_key}")
                continue
            self._active_rule_keys.add(rule_key)
            self._last_rule_fire_at[rule_id] = time.monotonic()
            actions = rule.get("actions", [])
            log_message(f"MouseMacro firing rule: {rule_key} actions={len(actions) if isinstance(actions, list) else 'invalid'}")
            self._execute_actions(actions, rule=rule, rule_key=rule_key)

    def _iter_rule_inputs(self) -> tuple[Set[str], Set[str]]:
        """Return mouse/key names that polling should watch for active rules."""
        mouse_names: Set[str] = set()
        key_names: Set[str] = set()
        for rule in self._load_rules(self._get_config()):
            if not isinstance(rule, dict) or not rule.get("enabled", False):
                continue
            for field in ("holdMouseButton", "pressMouseButton"):
                value = self._normalize_input_name("mouse", str(rule.get(field, "")))
                if value:
                    mouse_names.add(value)
            for field in ("holdKey", "pressKey"):
                value = self._normalize_input_name("key", str(rule.get(field, "")))
                if value:
                    key_names.add(value)
        return mouse_names, key_names

    def _poll_input_state(self) -> None:
        """Poll input state so macros still work when hooks are unavailable/missed."""
        if not self._get_config().get("enabled", False):
            self.sync_runtime()
            return
        mouse_names, key_names = self._iter_rule_inputs()
        for button in mouse_names:
            is_pressed = self._mouse_button_pressed(button)
            if is_pressed != (button in self._pressed_mouse_buttons):
                self._on_global_input_event("mouse", button, is_pressed)
        for key in key_names:
            is_pressed = self._key_pressed(key)
            if is_pressed != (key in self._pressed_keys):
                self._on_global_input_event("key", key, is_pressed)

    def _mouse_button_pressed(self, button_name: str) -> bool:
        """Return whether a mouse button is currently pressed."""
        vk = MOUSE_BUTTON_VKS.get(self._normalize_input_name("mouse", button_name))
        return bool(vk and user32.GetAsyncKeyState(vk) & 0x8000)

    def _key_pressed(self, key_name: str) -> bool:
        """Return whether a key is currently pressed."""
        key = self._normalize_input_name("key", key_name)
        modifier_vks = {"ctrl": 0x11, "control": 0x11, "alt": 0x12, "shift": 0x10, "win": 0x5B, "meta": 0x5B}
        vk = modifier_vks.get(key) or key_to_vk(key)
        return bool(vk and user32.GetAsyncKeyState(vk) & 0x8000)

    def _execute_actions(
        self,
        actions: Any,
        *,
        rule: Dict[str, Any] | None = None,
        rule_key: str = "",
    ) -> None:
        """Execute a bounded sequence of macro actions."""
        if not isinstance(actions, list):
            return
        self._executing = True
        self._cancel_requested = False
        self._held_output_keys.clear()
        self._current_rule = rule or {}
        self._current_rule_key = rule_key
        cancelled = False
        try:
            scheduler = ActionScheduler(
                self._execute_logged_action,
                should_cancel=self._should_cancel_actions,
                sleep=time.sleep,
            )
            scheduler.run(actions)
            cancelled = self._should_cancel_actions()
        finally:
            cancelled = cancelled or self._should_cancel_actions()
            if cancelled:
                self._execute_cancel_actions(self._current_rule.get("onCancel", []) if self._current_rule else [])
            self._release_held_output_keys()
            self._executing = False
            self._cancel_requested = False
            self._current_rule = None
            self._current_rule_key = ""

    def _should_cancel_actions(self) -> bool:
        return bool(self._current_rule and self._current_rule.get("interruptible") and self._cancel_requested)

    def _execute_logged_action(self, action: Dict[str, Any]) -> None:
        log_message(f"MouseMacro action: {action}")
        self._execute_action(action)

    def _execute_action(self, action: Dict[str, Any]) -> None:
        action_type = str(action.get("type", "") or "")
        if action_type == "mouseClick":
            self._input_service.click_mouse(str(action.get("button", "left") or "left"))
        elif action_type == "mouseDown":
            self._input_service.mouse_down(str(action.get("button", "left") or "left"))
        elif action_type == "mouseUp":
            self._input_service.mouse_up(str(action.get("button", "left") or "left"))
        elif action_type == "key":
            self._send_key(str(action.get("key", "") or ""))
        elif action_type == "keyDown":
            self._send_key_down(str(action.get("key", "") or ""))
        elif action_type == "keyUp":
            self._send_key_up(str(action.get("key", "") or ""))
        elif action_type == "hotkey":
            self._send_hotkey(action)
        elif action_type == "text":
            self._send_text(str(action.get("text", "") or ""))

    def _send_key(self, key: str) -> None:
        vk = key_to_vk(key)
        if not vk:
            return
        self._input_service.press_key(key)

    def _send_key_down(self, key: str) -> None:
        vk = key_to_vk(key)
        if not vk:
            return
        key_name = str(key or "")
        self._input_service.key_down(key_name)
        normalized = key_name.strip().lower()
        if normalized and normalized not in self._held_output_keys:
            self._held_output_keys.append(normalized)

    def _send_key_up(self, key: str) -> None:
        vk = key_to_vk(key)
        if not vk:
            return
        key_name = str(key or "")
        self._input_service.key_up(key_name)
        normalized = key_name.strip().lower()
        self._held_output_keys = [held for held in self._held_output_keys if held != normalized]

    def _execute_cancel_actions(self, actions: Any) -> None:
        """Run bounded cleanup actions without delays when a macro is cancelled."""
        if not isinstance(actions, list):
            return
        for action in actions[:16]:
            if not isinstance(action, dict):
                continue
            action_type = str(action.get("type", "") or "")
            if action_type in {"keyUp", "mouseClick", "mouseDown", "mouseUp", "key", "hotkey", "text"}:
                log_message(f"MouseMacro cancel action: {action}")
                self._execute_action(action)

    def _release_held_output_keys(self) -> None:
        """Best-effort keyUp cleanup for any keyDown emitted by this macro run."""
        while self._held_output_keys:
            key = self._held_output_keys.pop()
            log_message(f"MouseMacro releasing held output key: {key}")
            self._input_service.key_up(key)

    def _send_hotkey(self, action: Dict[str, Any]) -> None:
        self._input_service.press_hotkey(action)

    def _send_text(self, text: str) -> None:
        self._input_service.type_text(text)
