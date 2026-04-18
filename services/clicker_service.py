"""
Clicker runtime service for MouseCenterLock.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional

from PySide6 import QtCore

try:
    from PySide6 import QtMultimedia
except Exception:
    QtMultimedia = None

from win_api import click_mouse, key_to_vk, user32


class ClickerSoundPlayer(QtCore.QObject):
    """Play clicker start sounds from system presets or local files."""

    def __init__(self, sound_presets: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._sound_presets = sound_presets
        self._media_player = None
        self._audio_output = None
        if QtMultimedia is not None:
            try:
                self._audio_output = QtMultimedia.QAudioOutput(self)
                self._media_player = QtMultimedia.QMediaPlayer(self)
                self._media_player.setAudioOutput(self._audio_output)
                self._audio_output.setVolume(0.8)
            except Exception:
                self._audio_output = None
                self._media_player = None

    def play_for_profile(self, profile: Dict[str, Any]) -> None:
        """Play the configured start sound for a clicker profile."""
        self.play_sound_config(profile.get("sound", {}))

    def play_sound_config(self, sound: Dict[str, Any]) -> None:
        """Play a sound from raw sound settings."""
        if not sound.get("enabled", False):
            return

        preset = sound.get("preset", "systemAsterisk")
        if preset == "custom":
            self._play_custom_file(sound.get("customFile", ""))
            return

        try:
            import winsound
            winsound.MessageBeep(self._sound_presets.get(preset, self._sound_presets["systemAsterisk"]))
        except Exception:
            pass

    def _play_custom_file(self, file_path: str) -> None:
        """Play a local audio file when supported."""
        if not file_path:
            return
        path = Path(file_path)
        if not path.exists():
            return
        if self._media_player is None:
            try:
                import winsound
                if path.suffix.lower() == ".wav":
                    winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass
            return
        try:
            self._media_player.stop()
            self._media_player.setSource(QtCore.QUrl.fromLocalFile(str(path)))
            self._media_player.play()
        except Exception:
            pass


class ClickerService(QtCore.QObject):
    """Own the auto-clicker runtime, timers, and hold-trigger polling."""

    def __init__(
        self,
        *,
        get_profile: Callable[[], Dict[str, Any]],
        on_state_changed: Callable[[], None],
        on_notify_started: Callable[[Dict[str, Any]], None],
        on_notify_stopped: Callable[[Dict[str, Any]], None],
        sound_presets: Dict[str, Any],
        parent=None,
    ):
        super().__init__(parent)
        self._get_profile = get_profile
        self._on_state_changed = on_state_changed
        self._on_notify_started = on_notify_started
        self._on_notify_stopped = on_notify_stopped
        self._running = False
        self._hold_trigger_pressed = False
        self._sound_player = ClickerSoundPlayer(sound_presets, self)

        self.clicker_timer = QtCore.QTimer(self)
        self.clicker_timer.timeout.connect(self._on_clicker_tick)

        self.hold_state_timer = QtCore.QTimer(self)
        self.hold_state_timer.timeout.connect(self._poll_hold_trigger_state)
        self.hold_state_timer.start(12)

    @property
    def is_running(self) -> bool:
        """Return whether the clicker is currently running."""
        return self._running

    def play_sound_preview(self, sound_config: Dict[str, Any]) -> None:
        """Preview a sound selection."""
        self._sound_player.play_sound_config(sound_config)

    def sync_runtime(self) -> None:
        """Apply the current settings to runtime timers."""
        profile = self._get_profile()
        if not profile.get("enabled", False):
            self.stop(show_message=False)
            return
        self._apply_clicker_timer()
        self._on_state_changed()

    def start(self, show_message: bool = True, immediate_click: bool = False) -> None:
        """Start the auto clicker."""
        profile = self._get_profile()
        if self._running or not profile.get("enabled", False):
            return

        self._running = True
        if immediate_click:
            click_mouse(profile.get("button", "left"))
        self._apply_clicker_timer()
        self._sound_player.play_for_profile(profile)
        self._on_state_changed()
        if show_message:
            self._on_notify_started(profile)

    def stop(self, show_message: bool = True) -> None:
        """Stop the auto clicker."""
        if not self._running:
            return

        self._running = False
        self._apply_clicker_timer()
        self._on_state_changed()
        if show_message:
            self._on_notify_stopped(self._get_profile())

    def toggle(self) -> None:
        """Toggle the auto clicker."""
        profile = self._get_profile()
        if profile.get("triggers", {}).get("mode") != "toggle":
            if not self._running:
                self.start(immediate_click=True)
            else:
                self.stop()
            return
        if self._running:
            self.stop()
        else:
            self.start()

    def _apply_clicker_timer(self) -> None:
        """Start or stop the clicker timer based on state and settings."""
        profile = self._get_profile()
        if self._running and profile.get("enabled", False):
            interval = max(1, int(profile.get("intervalMs", 100)))
            if self.clicker_timer.interval() != interval or not self.clicker_timer.isActive():
                self.clicker_timer.start(interval)
        else:
            self.clicker_timer.stop()

    def _modifier_pressed(self, vk: int) -> bool:
        """Return whether a modifier virtual key is currently pressed."""
        return bool(user32.GetAsyncKeyState(vk) & 0x8000)

    def _hold_hotkey_matches(self, hold_key: Dict[str, Any]) -> bool:
        """Check whether the configured hold hotkey is currently pressed."""
        vk = key_to_vk(hold_key.get("key", ""))
        if vk is None or not self._modifier_pressed(vk):
            return False

        modifier_map = [
            ("modCtrl", 0x11),
            ("modAlt", 0x12),
            ("modShift", 0x10),
            ("modWin", 0x5B),
        ]
        for flag_name, modifier_vk in modifier_map:
            expected = bool(hold_key.get(flag_name, False))
            pressed = self._modifier_pressed(modifier_vk)
            if expected != pressed:
                return False
        return True

    def _mouse_button_pressed(self, button_name: str) -> bool:
        """Return whether a mouse button is currently pressed."""
        vk_map = {
            "left": 0x01,
            "right": 0x02,
            "middle": 0x04,
            "x1": 0x05,
            "x2": 0x06,
        }
        vk = vk_map.get((button_name or "").lower())
        return bool(vk and self._modifier_pressed(vk))

    def _poll_hold_trigger_state(self) -> None:
        """Poll keyboard/mouse hold state so hold triggers work without low-level hooks."""
        profile = self._get_profile()
        triggers = profile.get("triggers", {})
        if not profile.get("enabled", False):
            if self._hold_trigger_pressed:
                self._hold_trigger_pressed = False
                self.stop(show_message=False)
            return

        mode = triggers.get("mode")
        if mode == "holdKey":
            is_pressed = self._hold_hotkey_matches(triggers.get("holdKey", {}))
        elif mode == "holdMouseButton":
            is_pressed = self._mouse_button_pressed(triggers.get("holdMouseButton", "middle"))
        else:
            if self._hold_trigger_pressed:
                self._hold_trigger_pressed = False
            return

        if is_pressed and not self._hold_trigger_pressed:
            self._hold_trigger_pressed = True
            self.start(show_message=False, immediate_click=True)
        elif not is_pressed and self._hold_trigger_pressed:
            self._hold_trigger_pressed = False
            self.stop(show_message=False)

    def _on_clicker_tick(self) -> None:
        """Perform a click on each timer tick."""
        if not self._running:
            return
        profile = self._get_profile()
        if not profile.get("enabled", False):
            self.stop(show_message=False)
            return
        click_mouse(profile.get("button", "left"))
