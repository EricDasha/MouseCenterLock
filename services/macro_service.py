"""
Mouse macro runtime service.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Set

from PySide6 import QtCore

from win_api import GlobalInputListener, click_mouse, key_to_vk, user32


MODIFIER_VKS = {
    "modCtrl": 0x11,
    "modAlt": 0x12,
    "modShift": 0x10,
    "modWin": 0x5B,
}


class MouseMacroService(QtCore.QObject):
    """Execute configured mouse-combo macro rules from global input events."""

    inputEvent = QtCore.Signal(str, str, bool)

    def __init__(
        self,
        *,
        get_config: Callable[[], Dict[str, Any]],
        input_listener_factory: Callable[..., GlobalInputListener] = GlobalInputListener,
        parent=None,
    ):
        super().__init__(parent)
        self._get_config = get_config
        self._pressed_mouse_buttons: Set[str] = set()
        self._active_rule_keys: Set[str] = set()
        self._executing = False
        self._input_listener = input_listener_factory(on_mouse_event=self._emit_mouse_event)
        self.inputEvent.connect(self._on_global_input_event)
        self._hook_mode_active = self._input_listener.start()

    def stop(self) -> None:
        """Remove global hooks."""
        self._input_listener.stop()

    def sync_runtime(self) -> None:
        """Drop transient state when macros are disabled or source changes."""
        config = self._get_config()
        if not config.get("enabled", False):
            self._pressed_mouse_buttons.clear()
            self._active_rule_keys.clear()

    def _emit_mouse_event(self, button_name: str, is_pressed: bool) -> None:
        """Bridge low-level input into the Qt thread."""
        self.inputEvent.emit("mouse", button_name, is_pressed)

    def _on_global_input_event(self, event_type: str, name: str, is_pressed: bool) -> None:
        """Track mouse state and fire matching rules."""
        if event_type != "mouse" or self._executing:
            return
        button = str(name or "").lower().strip()
        if not button:
            return

        if is_pressed:
            self._pressed_mouse_buttons.add(button)
            self._fire_matching_rules(button)
        else:
            self._pressed_mouse_buttons.discard(button)
            self._active_rule_keys = {
                key for key in self._active_rule_keys if not key.endswith(f":{button}")
            }

    def _load_rules(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Load macro rules from builder config or an external JSON file."""
        if not config.get("enabled", False):
            return []
        if config.get("source") != "file":
            rules = config.get("rules", [])
            return rules if isinstance(rules, list) else []

        file_path = str(config.get("configFile", "") or "").strip()
        if not file_path:
            return []
        try:
            payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
        except Exception:
            return []
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            rules = payload.get("rules", [])
            return rules if isinstance(rules, list) else []
        return []

    def _fire_matching_rules(self, pressed_button: str) -> None:
        config = self._get_config()
        for index, rule in enumerate(self._load_rules(config)):
            if not isinstance(rule, dict) or not rule.get("enabled", False):
                continue
            hold = str(rule.get("holdMouseButton", "") or "").lower()
            press = str(rule.get("pressMouseButton", "") or "").lower()
            if press != pressed_button or hold not in self._pressed_mouse_buttons:
                continue
            rule_key = f"{rule.get('id') or index}:{press}"
            if rule_key in self._active_rule_keys:
                continue
            self._active_rule_keys.add(rule_key)
            self._execute_actions(rule.get("actions", []))

    def _execute_actions(self, actions: Any) -> None:
        """Execute a bounded sequence of macro actions."""
        if not isinstance(actions, list):
            return
        self._executing = True
        try:
            for action in actions[:32]:
                if isinstance(action, dict):
                    self._execute_action(action)
        finally:
            self._executing = False

    def _execute_action(self, action: Dict[str, Any]) -> None:
        action_type = str(action.get("type", "") or "")
        if action_type == "mouseClick":
            click_mouse(str(action.get("button", "left") or "left"))
        elif action_type == "key":
            self._send_key(str(action.get("key", "") or ""))
        elif action_type == "hotkey":
            self._send_hotkey(action)
        elif action_type == "text":
            self._send_text(str(action.get("text", "") or ""))
        elif action_type == "delay":
            time.sleep(max(0, min(60000, int(action.get("ms", 0)))) / 1000.0)

    def _send_key(self, key: str) -> None:
        vk = key_to_vk(key)
        if not vk:
            return
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, 0x0002, 0)

    def _send_hotkey(self, action: Dict[str, Any]) -> None:
        pressed_mods = [vk for flag, vk in MODIFIER_VKS.items() if action.get(flag)]
        key = str(action.get("key", "") or "")
        vk = key_to_vk(key)
        if not vk:
            return
        for mod_vk in pressed_mods:
            user32.keybd_event(mod_vk, 0, 0, 0)
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, 0x0002, 0)
        for mod_vk in reversed(pressed_mods):
            user32.keybd_event(mod_vk, 0, 0x0002, 0)

    def _send_text(self, text: str) -> None:
        for char in text[:1024]:
            vk_combo = user32.VkKeyScanW(ord(char))
            if vk_combo == -1:
                continue
            vk = vk_combo & 0xFF
            shift_state = (vk_combo >> 8) & 0xFF
            mods = []
            if shift_state & 1:
                mods.append(0x10)
            if shift_state & 2:
                mods.append(0x11)
            if shift_state & 4:
                mods.append(0x12)
            for mod_vk in mods:
                user32.keybd_event(mod_vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 0x0002, 0)
            for mod_vk in reversed(mods):
                user32.keybd_event(mod_vk, 0, 0x0002, 0)
