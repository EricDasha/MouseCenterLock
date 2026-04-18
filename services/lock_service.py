"""
Lock runtime service for MouseCenterLock.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6 import QtCore

from win_api import (
    clip_cursor_to_point,
    get_active_window_info,
    get_primary_screen_center,
    get_virtual_screen_center,
    get_window_center,
    get_window_process_name,
    set_cursor_to,
    unclip_cursor,
)


class LockService(QtCore.QObject):
    """Own lock state, recenter timer, and window-focus auto-lock logic."""

    def __init__(
        self,
        *,
        get_settings: Callable[[], Dict[str, Any]],
        on_state_changed: Callable[[], None],
        on_notify_locked: Callable[[], None],
        on_notify_unlocked: Callable[[], None],
        on_error: Callable[[str, BaseException], None],
        parent=None,
    ):
        super().__init__(parent)
        self._get_settings = get_settings
        self._on_state_changed = on_state_changed
        self._on_notify_locked = on_notify_locked
        self._on_notify_unlocked = on_notify_unlocked
        self._on_error = on_error

        self._locked = False
        self._auto_lock_suspended = False
        self._force_lock = False
        self._last_active_window = ""

        self.recenter_timer = QtCore.QTimer(self)
        self.recenter_timer.timeout.connect(self._on_recenter_tick)

        self.window_focus_timer = QtCore.QTimer(self)
        self.window_focus_timer.timeout.connect(self._check_window_focus)
        self.window_focus_timer.start(500)

    @property
    def is_locked(self) -> bool:
        """Return whether the cursor is currently locked."""
        return self._locked

    @property
    def is_force_lock(self) -> bool:
        """Return whether the current lock state was triggered manually."""
        return self._force_lock

    @property
    def auto_lock_suspended(self) -> bool:
        """Return whether auto-lock is currently suspended after a manual unlock."""
        return self._auto_lock_suspended

    def sync_runtime(self) -> None:
        """Re-apply timers after settings changes."""
        settings = self._get_settings()
        window_specific = settings.get("windowSpecific", {})
        if window_specific.get("enabled") and window_specific.get("autoLockOnWindowFocus"):
            if not self.window_focus_timer.isActive():
                self.window_focus_timer.start(500)
        else:
            self.window_focus_timer.stop()
        self._apply_recenter_timer()

    def lock(self, manual: bool = False) -> None:
        """Lock the cursor to the configured target position."""
        if self._locked:
            return
        if not manual and not self._should_lock_for_window():
            return

        if manual:
            self._auto_lock_suspended = False
            self._force_lock = True
        else:
            self._force_lock = False

        try:
            cx, cy = self._get_target_position()
            set_cursor_to(cx, cy)
            clip_cursor_to_point(cx, cy)
            self._locked = True
            self._apply_recenter_timer()
            self._on_state_changed()
            self._on_notify_locked()
        except Exception as exc:
            self._on_error("lock", exc)

    def unlock(self, manual: bool = False) -> None:
        """Unlock the cursor."""
        if not self._locked:
            return

        settings = self._get_settings()
        if manual and settings.get("windowSpecific", {}).get("autoLockOnWindowFocus", False):
            self._auto_lock_suspended = True
        if manual:
            self._force_lock = False

        try:
            unclip_cursor()
            self._locked = False
            self._apply_recenter_timer()
            self._on_state_changed()
            self._on_notify_unlocked()
        except Exception as exc:
            self._on_error("unlock", exc)

    def toggle(self) -> None:
        """Toggle lock state."""
        if self._locked:
            self.unlock(manual=True)
        else:
            self.lock(manual=True)

    def release_cursor(self) -> None:
        """Best-effort cursor release during shutdown."""
        if not self._locked:
            return
        try:
            unclip_cursor()
        except Exception:
            pass
        self._locked = False
        self._apply_recenter_timer()
        self._on_state_changed()

    def _check_match(self, title: str, process: str, targets: List[str]) -> bool:
        """Check if current window matches any target by title or process name."""
        title_lower = (title or "").lower()
        process_lower = (process or "").lower()
        for target in targets:
            target_lower = str(target or "").lower()
            if not target_lower:
                continue
            if target_lower == process_lower:
                return True
            if target_lower in title_lower:
                return True
        return False

    def _should_lock_for_window(self) -> bool:
        """Check if locking should proceed based on window-specific settings."""
        settings = self._get_settings()
        ws = settings.get("windowSpecific", {})
        if ws.get("enabled", False):
            hwnd, title = get_active_window_info()
            proc_name = get_window_process_name(hwnd) if hwnd else ""
            targets = ws.get("targetWindows", [])
            return self._check_match(title, proc_name, targets)
        return True

    def _get_target_position(self) -> Tuple[int, int]:
        """Get the target position for the cursor lock."""
        settings = self._get_settings()
        ws = settings.get("windowSpecific", {})
        if ws.get("enabled", False):
            hwnd, title = get_active_window_info()
            if hwnd:
                proc_name = get_window_process_name(hwnd) or ""
                targets = ws.get("targetWindows", [])
                if self._check_match(title, proc_name, targets):
                    center = get_window_center(hwnd)
                    if center:
                        return center

        pos = settings.get("position", {})
        mode = pos.get("mode", "virtualCenter")
        if mode == "primaryCenter":
            return get_primary_screen_center()
        if mode == "custom":
            return (pos.get("customX", 0), pos.get("customY", 0))
        return get_virtual_screen_center()

    def _apply_recenter_timer(self) -> None:
        """Start or stop the recenter timer based on state and settings."""
        settings = self._get_settings()
        recenter = settings.get("recenter", {})
        if self._locked and recenter.get("enabled", True):
            interval = max(16, recenter.get("intervalMs", 250))
            if self.recenter_timer.interval() != interval or not self.recenter_timer.isActive():
                self.recenter_timer.start(interval)
        else:
            self.recenter_timer.stop()

    def _on_recenter_tick(self) -> None:
        """Recenter and re-clip the cursor while locked."""
        if not self._locked:
            return
        if not self._force_lock and not self._should_lock_for_window():
            self.unlock(manual=False)
            return
        cx, cy = self._get_target_position()
        set_cursor_to(cx, cy)
        try:
            clip_cursor_to_point(cx, cy)
        except Exception:
            pass

    def _check_window_focus(self) -> None:
        """Auto lock/unlock based on configured target windows."""
        settings = self._get_settings()
        ws = settings.get("windowSpecific", {})
        if not ws.get("enabled") or not ws.get("autoLockOnWindowFocus"):
            return

        hwnd, title = get_active_window_info()
        proc_name = get_window_process_name(hwnd) if hwnd else ""
        targets = ws.get("targetWindows", [])
        is_target = self._check_match(title, proc_name, targets)

        if title != self._last_active_window:
            self._last_active_window = title

            if ws.get("resumeAfterWindowSwitch", False) and not is_target and self._auto_lock_suspended:
                self._auto_lock_suspended = False

            if self._locked and not is_target:
                self.unlock(manual=False)
            elif not self._locked and is_target and not self._auto_lock_suspended:
                self.lock(manual=False)
            return

        if self._locked:
            if self._force_lock:
                return
            if not is_target:
                self.unlock(manual=False)
        else:
            is_auto_enabled = ws.get("autoLockOnWindowFocus", False)
            if is_target:
                if is_auto_enabled and not self._auto_lock_suspended:
                    self.lock(manual=False)
            elif self._auto_lock_suspended:
                return
