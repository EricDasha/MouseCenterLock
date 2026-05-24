"""
Input backend service shared by clicker and macro runtimes.

Backends:
- native-sendinput: Rust DLL SendInput path. Keyboard actions use scan-code
  SendInput and text uses Unicode SendInput, then fall back to Python.
- python-sendinput: force the original Python ctypes SendInput path.
- window-message: PostMessage to the foreground window handle.
- virtual-hid/hardware-hid: reserved future backends; currently log and fall
  back to the user-mode native/Python path.
- auto: current safe default, same as native-sendinput. Legacy sendinput and
  native-scancode config values are accepted as aliases.
"""
from __future__ import annotations

from ctypes import byref
from typing import Any, Callable, Dict, Iterable

from app_logging import log_message
from services import native_input
from win_api import (
    WM_KEYDOWN,
    WM_KEYUP,
    WM_LBUTTONDOWN,
    WM_LBUTTONUP,
    WM_MBUTTONDOWN,
    WM_MBUTTONUP,
    WM_RBUTTONDOWN,
    WM_RBUTTONUP,
    POINT,
    click_mouse as sendinput_click_mouse,
    get_active_window_info,
    key_down_vk,
    key_to_vk,
    key_up_vk,
    press_vk as sendinput_press_vk,
    user32,
)

BACKEND_AUTO = "auto"
BACKEND_NATIVE_SENDINPUT = "native-sendinput"
BACKEND_PYTHON_SENDINPUT = "python-sendinput"
BACKEND_WINDOW_MESSAGE = "window-message"
BACKEND_VIRTUAL_HID = "virtual-hid"
BACKEND_HARDWARE_HID = "hardware-hid"
BACKEND_SENDINPUT = "sendinput"  # legacy alias
BACKEND_NATIVE_SCANCODE = "native-scancode"  # legacy alias
BACKEND_PYTHON_FALLBACK = "python-fallback"  # legacy alias
_BACKEND_ALIASES = {
    BACKEND_SENDINPUT: BACKEND_NATIVE_SENDINPUT,
    BACKEND_NATIVE_SCANCODE: BACKEND_NATIVE_SENDINPUT,
    BACKEND_PYTHON_FALLBACK: BACKEND_PYTHON_SENDINPUT,
}
VALID_BACKENDS = {
    BACKEND_AUTO,
    BACKEND_NATIVE_SENDINPUT,
    BACKEND_PYTHON_SENDINPUT,
    BACKEND_WINDOW_MESSAGE,
    BACKEND_VIRTUAL_HID,
    BACKEND_HARDWARE_HID,
    *_BACKEND_ALIASES.keys(),
}
_RESERVED_BACKENDS = {BACKEND_VIRTUAL_HID, BACKEND_HARDWARE_HID}

_MOUSE_MESSAGES = {
    "left": (WM_LBUTTONDOWN, WM_LBUTTONUP, 0x0001),
    "right": (WM_RBUTTONDOWN, WM_RBUTTONUP, 0x0002),
    "middle": (WM_MBUTTONDOWN, WM_MBUTTONUP, 0x0010),
}

_MODIFIER_VKS = {
    "modCtrl": 0x11,
    "modAlt": 0x12,
    "modShift": 0x10,
    "modWin": 0x5B,
}


def _lparam_from_point(x: int, y: int) -> int:
    return (int(y) & 0xFFFF) << 16 | (int(x) & 0xFFFF)


class InputService:
    """Send mouse and keyboard actions through a selected backend."""

    def __init__(self, get_backend: Callable[[], str] | None = None):
        self._get_backend = get_backend or (lambda: BACKEND_AUTO)
        log_message(f"InputService initialized: rust_backend={native_input.status()}")

    def backend(self) -> str:
        value = str(self._get_backend() or BACKEND_AUTO).strip().lower()
        if value not in VALID_BACKENDS:
            return BACKEND_AUTO
        return _BACKEND_ALIASES.get(value, value)

    def _effective_user_backend(self, backend: str) -> str:
        if backend in _RESERVED_BACKENDS:
            log_message(f"InputService backend reserved: requested={backend}; fallback={BACKEND_NATIVE_SENDINPUT}")
            return BACKEND_NATIVE_SENDINPUT
        return backend

    def _native_enabled(self, backend: str) -> bool:
        return self._effective_user_backend(backend) in {
            BACKEND_AUTO,
            BACKEND_NATIVE_SENDINPUT,
        }

    def _log_route(self, action: str, backend: str, route: str, detail: str = "") -> None:
        suffix = f" {detail}" if detail else ""
        log_message(f"InputService action={action} backend={backend} route={route}{suffix}")

    def click_mouse(self, button: str = "left") -> None:
        button_name = (button or "left").lower()
        backend = self.backend()
        if backend == BACKEND_WINDOW_MESSAGE:
            if self._click_mouse_window_message(button_name):
                self._log_route("mouseClick", backend, "window-message", f"button={button_name}")
                return
            log_message(f"InputService window-message click failed: button={button_name}")
            return
        if self._native_enabled(backend) and native_input.click_mouse(button_name):
            self._log_route("mouseClick", backend, "native-sendinput", f"button={button_name}")
            return
        sendinput_click_mouse(button_name)
        self._log_route("mouseClick", backend, "python-sendinput", f"button={button_name}")

    def press_key(self, key: str) -> None:
        vk = key_to_vk(key)
        if not vk:
            log_message(f"InputService invalid key: {key}")
            return
        backend = self.backend()
        if backend == BACKEND_WINDOW_MESSAGE:
            if self._press_vk_window_message(vk):
                self._log_route("key", backend, "window-message", f"key={key}")
                return
            log_message(f"InputService window-message key failed: key={key}")
            return
        if self._native_enabled(backend) and native_input.press_vk(vk):
            self._log_route("key", backend, "native-scancode", f"key={key}")
            return
        sendinput_press_vk(vk)
        self._log_route("key", backend, "python-sendinput", f"key={key}")

    def press_hotkey(self, action: Dict[str, Any]) -> None:
        key = str(action.get("key", "") or "")
        vk = key_to_vk(key)
        if not vk:
            log_message(f"InputService invalid hotkey key: {key}")
            return
        mods = [vk_value for flag, vk_value in _MODIFIER_VKS.items() if action.get(flag)]
        backend = self.backend()
        if backend == BACKEND_WINDOW_MESSAGE:
            if self._press_hotkey_window_message(mods, vk):
                self._log_route("hotkey", backend, "window-message", f"key={key} mods={len(mods)}")
                return
            log_message(f"InputService window-message hotkey failed: key={key}")
            return
        for mod_vk in mods:
            if not (self._native_enabled(backend) and native_input.key_down_vk(mod_vk)):
                key_down_vk(mod_vk)
        if not (self._native_enabled(backend) and native_input.press_vk(vk)):
            sendinput_press_vk(vk)
        for mod_vk in reversed(mods):
            if not (self._native_enabled(backend) and native_input.key_up_vk(mod_vk)):
                key_up_vk(mod_vk)
        route = "native-scancode" if self._native_enabled(backend) and native_input.AVAILABLE else "python-sendinput"
        self._log_route("hotkey", backend, route, f"key={key} mods={len(mods)}")

    def type_text(self, text: str) -> None:
        text = str(text or "")[:1024]
        backend = self.backend()
        if backend != BACKEND_WINDOW_MESSAGE and self._native_enabled(backend) and native_input.type_text(text):
            self._log_route("text", backend, "native-unicode", f"chars={len(text)}")
            return
        for char in text:
            vk_combo = user32.VkKeyScanW(ord(char))
            if vk_combo == -1:
                continue
            vk = vk_combo & 0xFF
            shift_state = (vk_combo >> 8) & 0xFF
            mods: list[int] = []
            if shift_state & 1:
                mods.append(0x10)
            if shift_state & 2:
                mods.append(0x11)
            if shift_state & 4:
                mods.append(0x12)
            if backend == BACKEND_WINDOW_MESSAGE:
                self._press_hotkey_window_message(mods, vk)
                continue
            for mod_vk in mods:
                if not (self._native_enabled(backend) and native_input.key_down_vk(mod_vk)):
                    key_down_vk(mod_vk)
            if not (self._native_enabled(backend) and native_input.press_vk(vk)):
                sendinput_press_vk(vk)
            for mod_vk in reversed(mods):
                if not (self._native_enabled(backend) and native_input.key_up_vk(mod_vk)):
                    key_up_vk(mod_vk)
        route = "window-message" if backend == BACKEND_WINDOW_MESSAGE else "python-sendinput"
        self._log_route("text", backend, route, f"chars={len(text)}")

    def _foreground_hwnd(self) -> int:
        hwnd, _title = get_active_window_info()
        return int(hwnd or 0)

    def _post_message(self, hwnd: int, msg: int, wparam: int, lparam: int) -> bool:
        return bool(hwnd and user32.PostMessageW(hwnd, msg, int(wparam), int(lparam)))

    def _click_mouse_window_message(self, button: str) -> bool:
        if button not in _MOUSE_MESSAGES:
            return False
        hwnd = self._foreground_hwnd()
        if not hwnd:
            return False
        # Convert the current cursor position to client coordinates.
        try:
            pt = POINT()
            user32.GetCursorPos(byref(pt))
            user32.ScreenToClient(hwnd, byref(pt))
            lparam = _lparam_from_point(pt.x, pt.y)
        except Exception:
            lparam = 0
        down_msg, up_msg, wparam = _MOUSE_MESSAGES[button]
        ok_down = self._post_message(hwnd, down_msg, wparam, lparam)
        ok_up = self._post_message(hwnd, up_msg, 0, lparam)
        return ok_down and ok_up

    def _press_vk_window_message(self, vk: int) -> bool:
        hwnd = self._foreground_hwnd()
        if not hwnd:
            return False
        ok_down = self._post_message(hwnd, WM_KEYDOWN, vk, 0)
        ok_up = self._post_message(hwnd, WM_KEYUP, vk, 0)
        return ok_down and ok_up

    def _press_hotkey_window_message(self, mods: Iterable[int], vk: int) -> bool:
        hwnd = self._foreground_hwnd()
        if not hwnd:
            return False
        ok = True
        mods = list(mods)
        for mod_vk in mods:
            ok = self._post_message(hwnd, WM_KEYDOWN, mod_vk, 0) and ok
        ok = self._post_message(hwnd, WM_KEYDOWN, vk, 0) and ok
        ok = self._post_message(hwnd, WM_KEYUP, vk, 0) and ok
        for mod_vk in reversed(mods):
            ok = self._post_message(hwnd, WM_KEYUP, mod_vk, 0) and ok
        return ok
