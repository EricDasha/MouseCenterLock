"""
Shared mouse macro schema constants and helpers.
"""
from __future__ import annotations

MOUSE_BUTTONS = ("left", "right", "middle", "x1", "x2")

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

MOUSE_MACRO_ACTION_TYPES = (
    "hotkey",
    "key",
    "keyDown",
    "keyUp",
    "mouseDown",
    "mouseUp",
    "mouseClick",
    "mouseMove",
    "mouseMoveRelative",
    "mouseScroll",
    "text",
    "delay",
    "repeat",
)

MOUSE_MACRO_TRIGGER_MODES = ("hold", "toggle", "holdLoop", "toggleLoop")

_MOUSE_MACRO_TRIGGER_MODE_ALIASES = {
    "hold": "hold",
    "toggle": "toggle",
    "holdloop": "holdLoop",
    "hold_loop": "holdLoop",
    "hold-loop": "holdLoop",
    "toggleloop": "toggleLoop",
    "toggle_loop": "toggleLoop",
    "toggle-loop": "toggleLoop",
}


def normalize_mouse_button(value: str | None, fallback: str = "left") -> str:
    raw = str(value or "").strip().lower()
    return MOUSE_BUTTON_ALIASES.get(raw, fallback if fallback in MOUSE_BUTTONS else "left")


def normalize_macro_trigger_mode(value: str | None, fallback: str = "hold") -> str:
    raw = str(value or fallback or "hold").strip().lower()
    fallback_mode = _MOUSE_MACRO_TRIGGER_MODE_ALIASES.get(
        str(fallback or "hold").strip().lower(),
        "hold",
    )
    return _MOUSE_MACRO_TRIGGER_MODE_ALIASES.get(raw, fallback_mode)
