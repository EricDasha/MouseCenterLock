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

import time
from ctypes import byref
from typing import Any, Callable, Dict, Iterable

from app_logging import log_message
from services import native_input
from services.input_backends import (
    BACKEND_AUTO,
    BACKEND_NATIVE_SENDINPUT,
    BACKEND_PYTHON_SENDINPUT,
    BACKEND_WINDOW_MESSAGE,
    normalize_backend,
    normalize_fallback_policy,
    get_backend_status,
    all_backend_statuses,
)
from win_api import (
    WM_KEYDOWN,
    WM_KEYUP,
    WM_LBUTTONDOWN,
    WM_LBUTTONUP,
    WM_MBUTTONDOWN,
    WM_MBUTTONUP,
    WM_MOUSEHWHEEL,
    WM_MOUSEWHEEL,
    WM_RBUTTONDOWN,
    WM_RBUTTONUP,
    POINT,
    click_mouse as sendinput_click_mouse,
    get_active_window_info,
    mouse_move_relative as sendinput_mouse_move_relative,
    mouse_scroll as sendinput_mouse_scroll,
    mouse_down as sendinput_mouse_down,
    mouse_up as sendinput_mouse_up,
    key_down_vk,
    key_to_vk,
    key_up_vk,
    press_vk as sendinput_press_vk,
    set_cursor_to,
    user32,
)

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

# A down/up pair submitted in the same SendInput batch can be invisible to
# frame-polled input systems (notably some Unreal Engine games). Zero remains
# a valid config value, but means "automatic compatibility hold".
DEFAULT_MOUSE_CLICK_HOLD_MS = 20


def _lparam_from_point(x: int, y: int) -> int:
    return (int(y) & 0xFFFF) << 16 | (int(x) & 0xFFFF)


class InputService:
    """Send mouse and keyboard actions through a selected backend."""

    def __init__(
        self,
        get_backend: Callable[[], str] | None = None,
        get_fallback_backend: Callable[[], str] | None = None,
        get_fallback_policy: Callable[[], str] | None = None,
    ):
        self._get_backend = get_backend or (lambda: BACKEND_AUTO)
        self._get_fallback_backend = get_fallback_backend or (lambda: BACKEND_NATIVE_SENDINPUT)
        self._get_fallback_policy = get_fallback_policy or (lambda: "auto")
        log_message(f"InputService initialized: rust_backend={native_input.status()}")
        log_message(f"InputService backend statuses: {all_backend_statuses()}")

    def backend(self) -> str:
        return normalize_backend(self._get_backend())

    def fallback_backend(self) -> str:
        backend = normalize_backend(self._get_fallback_backend())
        return BACKEND_NATIVE_SENDINPUT if backend == BACKEND_AUTO else backend

    def fallback_policy(self) -> str:
        return normalize_fallback_policy(self._get_fallback_policy())

    def _resolve_backend(self, requested: str) -> tuple[str, str | None]:
        if requested == BACKEND_AUTO:
            return BACKEND_NATIVE_SENDINPUT, None
        status = get_backend_status(requested)
        if status.available:
            return requested, None
        policy = self.fallback_policy()
        if policy in ("error", "disabled"):
            return requested, status.reason or status.state
        fallback = self.fallback_backend()
        fallback_status = get_backend_status(fallback)
        log_message(
            "InputService backend fallback: "
            f"requested={requested} actual={fallback} reason={status.reason or status.state} "
            f"fallbackPolicy={policy} fallbackAvailable={fallback_status.available}"
        )
        return fallback, status.reason or status.state

    def _native_enabled(self, backend: str) -> bool:
        return backend in {
            BACKEND_AUTO,
            BACKEND_NATIVE_SENDINPUT,
        }

    def _log_route(self, action: str, backend: str, route: str, detail: str = "", requested: str | None = None, reason: str | None = None) -> None:
        suffix = f" {detail}" if detail else ""
        requested_text = f" requested={requested}" if requested and requested != backend else ""
        reason_text = f" fallbackReason={reason}" if reason else ""
        log_message(f"InputService action={action}{requested_text} backend={backend} route={route}{reason_text}{suffix}")

    def click_mouse(self, button: str = "left") -> None:
        self.mouse_click(button)

    def mouse_click(self, button: str = "left", hold_ms: int = 0) -> None:
        button_name = (button or "left").lower()
        try:
            hold_ms = max(0, min(5000, int(hold_ms or 0)))
        except Exception:
            hold_ms = 0
        effective_hold_ms = hold_ms or DEFAULT_MOUSE_CLICK_HOLD_MS
        try:
            self.mouse_down(button_name)
            time.sleep(effective_hold_ms / 1000.0)
        finally:
            self.mouse_up(button_name)
        self._log_route(
            "mouseClick",
            self.backend(),
            "down-hold-up",
            f"button={button_name} holdMs={effective_hold_ms} configuredHoldMs={hold_ms}",
        )

    def mouse_down(self, button: str = "left") -> None:
        self._mouse_button(button, down=True, up=False, action="mouseDown")

    def mouse_up(self, button: str = "left") -> None:
        self._mouse_button(button, down=False, up=True, action="mouseUp")

    def _mouse_button(self, button: str, *, down: bool, up: bool, action: str) -> None:
        button_name = (button or "left").lower()
        requested = self.backend()
        backend, fallback_reason = self._resolve_backend(requested)
        if fallback_reason and backend == requested:
            self._log_route(action, backend, "unavailable", f"button={button_name}", requested=requested, reason=fallback_reason)
            return
        if backend == BACKEND_WINDOW_MESSAGE:
            if self._mouse_button_window_message(button_name, down=down, up=up):
                self._log_route(action, backend, "window-message", f"button={button_name}", requested=requested, reason=fallback_reason)
                return
            log_message(f"InputService window-message {action} failed: button={button_name}")
            return
        if down and not up:
            if self._native_enabled(backend) and native_input.mouse_down(button_name):
                self._log_route(action, backend, "native-sendinput", f"button={button_name}", requested=requested, reason=fallback_reason)
                return
        elif up and not down:
            if self._native_enabled(backend) and native_input.mouse_up(button_name):
                self._log_route(action, backend, "native-sendinput", f"button={button_name}", requested=requested, reason=fallback_reason)
                return
        elif self._native_enabled(backend) and native_input.click_mouse(button_name):
            self._log_route(action, backend, "native-sendinput", f"button={button_name}", requested=requested, reason=fallback_reason)
            return
        if down and not up:
            sendinput_mouse_down(button_name)
        elif up and not down:
            sendinput_mouse_up(button_name)
        else:
            sendinput_click_mouse(button_name)
        self._log_route(action, backend, "python-sendinput", f"button={button_name}", requested=requested, reason=fallback_reason)

    def mouse_move(self, x: int, y: int) -> None:
        """Move cursor to an absolute screen coordinate."""
        try:
            move_x = int(x)
            move_y = int(y)
        except Exception:
            self._log_route("mouseMove", self.backend(), "invalid", f"x={x} y={y}")
            return
        set_cursor_to(move_x, move_y)
        self._log_route("mouseMove", self.backend(), "set-cursor-pos", f"x={move_x} y={move_y}")

    def mouse_move_relative(self, dx: int, dy: int) -> None:
        """Move cursor by a relative offset."""
        try:
            move_x = int(dx)
            move_y = int(dy)
        except Exception:
            self._log_route("mouseMoveRelative", self.backend(), "invalid", f"dx={dx} dy={dy}")
            return
        sendinput_mouse_move_relative(move_x, move_y)
        self._log_route("mouseMoveRelative", self.backend(), "python-sendinput", f"dx={move_x} dy={move_y}")

    def mouse_scroll(self, *, dx: int = 0, dy: int = 0) -> None:
        """Scroll the mouse wheel vertically and/or horizontally."""
        try:
            scroll_x = int(dx or 0)
            scroll_y = int(dy or 0)
        except Exception:
            self._log_route("mouseScroll", self.backend(), "invalid", f"dx={dx} dy={dy}")
            return
        requested = self.backend()
        backend, fallback_reason = self._resolve_backend(requested)
        if fallback_reason and backend == requested:
            self._log_route("mouseScroll", backend, "unavailable", f"dx={scroll_x} dy={scroll_y}", requested=requested, reason=fallback_reason)
            return
        if backend == BACKEND_WINDOW_MESSAGE:
            if self._mouse_wheel_window_message(scroll_y, horizontal=False) and self._mouse_wheel_window_message(scroll_x, horizontal=True):
                self._log_route("mouseScroll", backend, "window-message", f"dx={scroll_x} dy={scroll_y}", requested=requested, reason=fallback_reason)
                return
            log_message(f"InputService window-message scroll failed: dx={scroll_x} dy={scroll_y}")
            return
        if scroll_y:
            sendinput_mouse_scroll(scroll_y, horizontal=False)
        if scroll_x:
            sendinput_mouse_scroll(scroll_x, horizontal=True)
        self._log_route("mouseScroll", backend, "python-sendinput", f"dx={scroll_x} dy={scroll_y}", requested=requested, reason=fallback_reason)

    def press_key(self, key: str) -> None:
        vk = key_to_vk(key)
        if not vk:
            log_message(f"InputService invalid key: {key}")
            return
        requested = self.backend()
        backend, fallback_reason = self._resolve_backend(requested)
        if fallback_reason and backend == requested:
            self._log_route("key", backend, "unavailable", f"key={key}", requested=requested, reason=fallback_reason)
            return
        if backend == BACKEND_WINDOW_MESSAGE:
            if self._press_vk_window_message(vk):
                self._log_route("key", backend, "window-message", f"key={key}", requested=requested, reason=fallback_reason)
                return
            log_message(f"InputService window-message key failed: key={key}")
            return
        if self._native_enabled(backend) and native_input.press_vk(vk):
            self._log_route("key", backend, "native-scancode", f"key={key}", requested=requested, reason=fallback_reason)
            return
        sendinput_press_vk(vk)
        self._log_route("key", backend, "python-sendinput", f"key={key}", requested=requested, reason=fallback_reason)

    def key_down(self, key: str) -> None:
        vk = key_to_vk(key)
        if not vk:
            log_message(f"InputService invalid keyDown key: {key}")
            return
        requested = self.backend()
        backend, fallback_reason = self._resolve_backend(requested)
        if fallback_reason and backend == requested:
            self._log_route("keyDown", backend, "unavailable", f"key={key}", requested=requested, reason=fallback_reason)
            return
        if backend == BACKEND_WINDOW_MESSAGE:
            hwnd = self._foreground_hwnd()
            if self._post_message(hwnd, WM_KEYDOWN, vk, 0):
                self._log_route("keyDown", backend, "window-message", f"key={key}", requested=requested, reason=fallback_reason)
                return
            log_message(f"InputService window-message keyDown failed: key={key}")
            return
        if self._native_enabled(backend) and native_input.key_down_vk(vk):
            self._log_route("keyDown", backend, "native-scancode", f"key={key}", requested=requested, reason=fallback_reason)
            return
        key_down_vk(vk)
        self._log_route("keyDown", backend, "python-sendinput", f"key={key}", requested=requested, reason=fallback_reason)

    def key_up(self, key: str) -> None:
        vk = key_to_vk(key)
        if not vk:
            log_message(f"InputService invalid keyUp key: {key}")
            return
        requested = self.backend()
        backend, fallback_reason = self._resolve_backend(requested)
        if fallback_reason and backend == requested:
            self._log_route("keyUp", backend, "unavailable", f"key={key}", requested=requested, reason=fallback_reason)
            return
        if backend == BACKEND_WINDOW_MESSAGE:
            hwnd = self._foreground_hwnd()
            if self._post_message(hwnd, WM_KEYUP, vk, 0):
                self._log_route("keyUp", backend, "window-message", f"key={key}", requested=requested, reason=fallback_reason)
                return
            log_message(f"InputService window-message keyUp failed: key={key}")
            return
        if self._native_enabled(backend) and native_input.key_up_vk(vk):
            self._log_route("keyUp", backend, "native-scancode", f"key={key}", requested=requested, reason=fallback_reason)
            return
        key_up_vk(vk)
        self._log_route("keyUp", backend, "python-sendinput", f"key={key}", requested=requested, reason=fallback_reason)

    def press_hotkey(self, action: Dict[str, Any]) -> None:
        key = str(action.get("key", "") or "")
        vk = key_to_vk(key)
        if not vk:
            log_message(f"InputService invalid hotkey key: {key}")
            return
        mods = [vk_value for flag, vk_value in _MODIFIER_VKS.items() if action.get(flag)]
        requested = self.backend()
        backend, fallback_reason = self._resolve_backend(requested)
        if fallback_reason and backend == requested:
            self._log_route("hotkey", backend, "unavailable", f"key={key} mods={len(mods)}", requested=requested, reason=fallback_reason)
            return
        if backend == BACKEND_WINDOW_MESSAGE:
            if self._press_hotkey_window_message(mods, vk):
                self._log_route("hotkey", backend, "window-message", f"key={key} mods={len(mods)}", requested=requested, reason=fallback_reason)
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
        self._log_route("hotkey", backend, route, f"key={key} mods={len(mods)}", requested=requested, reason=fallback_reason)

    def type_text(self, text: str) -> None:
        text = str(text or "")[:1024]
        requested = self.backend()
        backend, fallback_reason = self._resolve_backend(requested)
        if fallback_reason and backend == requested:
            self._log_route("text", backend, "unavailable", f"chars={len(text)}", requested=requested, reason=fallback_reason)
            return
        if backend != BACKEND_WINDOW_MESSAGE and self._native_enabled(backend) and native_input.type_text(text):
            self._log_route("text", backend, "native-unicode", f"chars={len(text)}", requested=requested, reason=fallback_reason)
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
        self._log_route("text", backend, route, f"chars={len(text)}", requested=requested, reason=fallback_reason)

    def _foreground_hwnd(self) -> int:
        hwnd, _title = get_active_window_info()
        return int(hwnd or 0)

    def _post_message(self, hwnd: int, msg: int, wparam: int, lparam: int) -> bool:
        return bool(hwnd and user32.PostMessageW(hwnd, msg, int(wparam), int(lparam)))

    def _mouse_button_window_message(self, button: str, *, down: bool, up: bool) -> bool:
        if button not in _MOUSE_MESSAGES:
            return False
        hwnd = self._foreground_hwnd()
        if not hwnd:
            return False
        try:
            pt = POINT()
            user32.GetCursorPos(byref(pt))
            user32.ScreenToClient(hwnd, byref(pt))
            lparam = _lparam_from_point(pt.x, pt.y)
        except Exception:
            lparam = 0
        down_msg, up_msg, wparam = _MOUSE_MESSAGES[button]
        ok = True
        if down:
            ok = self._post_message(hwnd, down_msg, wparam, lparam) and ok
        if up:
            ok = self._post_message(hwnd, up_msg, 0, lparam) and ok
        return ok

    def _mouse_wheel_window_message(self, delta: int, *, horizontal: bool = False) -> bool:
        if not delta:
            return True
        hwnd = self._foreground_hwnd()
        if not hwnd:
            return False
        try:
            pt = POINT()
            user32.GetCursorPos(byref(pt))
            lparam = _lparam_from_point(pt.x, pt.y)
        except Exception:
            lparam = 0
        msg = WM_MOUSEHWHEEL if horizontal else WM_MOUSEWHEEL
        wparam = (int(delta) & 0xFFFF) << 16
        return self._post_message(hwnd, msg, wparam, lparam)

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
