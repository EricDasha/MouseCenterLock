"""
Shared macro action execution helpers.
"""
from __future__ import annotations

from typing import Any, Dict

from services.input_service import InputService


class MacroActionExecutor:
    """Execute common macro actions through a shared input service."""

    def __init__(
        self,
        *,
        input_service: InputService | None = None,
        click_mouse_func=None,
    ):
        self._input_service = input_service or InputService()
        self._click_mouse_func = click_mouse_func

    def execute(self, action: Dict[str, Any]) -> None:
        """Execute a single macro action."""
        action_type = str(action.get("type", "") or "")
        if action_type == "mouseClick":
            self.click_mouse(str(action.get("button", "left") or "left"))
        elif action_type == "mouseDown":
            self.mouse_down(str(action.get("button", "left") or "left"))
        elif action_type == "mouseUp":
            self.mouse_up(str(action.get("button", "left") or "left"))
        elif action_type == "key":
            self.press_key(str(action.get("key", "") or ""))
        elif action_type == "keyDown":
            self.key_down(str(action.get("key", "") or ""))
        elif action_type == "keyUp":
            self.key_up(str(action.get("key", "") or ""))
        elif action_type == "hotkey":
            self.press_hotkey(action)
        elif action_type == "text":
            self.type_text(str(action.get("text", "") or ""))

    def click_mouse(self, button: str = "left") -> None:
        if self._click_mouse_func is not None:
            self._click_mouse_func(button)
            return
        self._input_service.click_mouse(button)

    def mouse_down(self, button: str = "left") -> None:
        self._input_service.mouse_down(button)

    def mouse_up(self, button: str = "left") -> None:
        self._input_service.mouse_up(button)

    def press_key(self, key: str) -> None:
        self._input_service.press_key(key)

    def key_down(self, key: str) -> None:
        self._input_service.key_down(key)

    def key_up(self, key: str) -> None:
        self._input_service.key_up(key)

    def press_hotkey(self, action: Dict[str, Any]) -> None:
        self._input_service.press_hotkey(action)

    def type_text(self, text: str) -> None:
        self._input_service.type_text(text)
