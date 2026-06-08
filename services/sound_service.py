"""
Reusable runtime sound helpers for clicker and macro state changes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from PySide6 import QtCore

try:
    from PySide6 import QtMultimedia
except Exception:
    QtMultimedia = None


SYSTEM_SOUND_PRESETS: Dict[str, Any] = {
    "systemAsterisk": 0x00000040,
    "systemExclamation": 0x00000030,
    "systemQuestion": 0x00000020,
    "systemHand": 0x00000010,
    "win10Notify": r"C:\Windows\Media\Windows Notify System Generic.wav",
    "win10Ding": r"C:\Windows\Media\Windows Ding.wav",
    "win10Chimes": r"C:\Windows\Media\Windows Notify Calendar.wav",
    "win11Notify": r"C:\Windows\Media\Windows Notify System Generic.wav",
    "win11Ding": r"C:\Windows\Media\Windows Ding.wav",
    "win11Chimes": r"C:\Windows\Media\Windows Notify Calendar.wav",
    "custom": None,
}


DEFAULT_SOUND_EVENT = {
    "enabled": False,
    "preset": "systemAsterisk",
    "customFile": "",
}


def normalize_sound_event(sound: Dict[str, Any] | None, fallback: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Normalize one sound event config."""
    source = sound if isinstance(sound, dict) else {}
    default = dict(fallback or DEFAULT_SOUND_EVENT)
    preset = str(source.get("preset", default["preset"]) or default["preset"])
    return {
        "enabled": bool(source.get("enabled", default["enabled"])),
        "preset": preset if preset in SYSTEM_SOUND_PRESETS else default["preset"],
        "customFile": str(source.get("customFile", default["customFile"]) or ""),
    }


def normalize_sound_config(sound: Dict[str, Any] | None) -> Dict[str, Dict[str, Any]]:
    """Normalize start/stop sound config, migrating the legacy single-start shape."""
    source = sound if isinstance(sound, dict) else {}
    if "start" in source or "stop" in source:
        return {
            "start": normalize_sound_event(source.get("start", {})),
            "stop": normalize_sound_event(source.get("stop", {}), {"enabled": False, "preset": "systemHand", "customFile": ""}),
        }
    return {
        "start": normalize_sound_event(source),
        "stop": normalize_sound_event({}, {"enabled": False, "preset": "systemHand", "customFile": ""}),
    }


class SoundPlayer(QtCore.QObject):
    """Play system preset sounds or custom local audio files."""

    def __init__(self, parent=None):
        super().__init__(parent)
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

    def play_event(self, sound: Dict[str, Any]) -> None:
        """Play a normalized event sound if enabled."""
        if not isinstance(sound, dict) or not sound.get("enabled", False):
            return

        preset = str(sound.get("preset", "systemAsterisk") or "systemAsterisk")
        if preset == "custom":
            self._play_custom_file(sound.get("customFile", ""))
            return

        value = SYSTEM_SOUND_PRESETS.get(preset, SYSTEM_SOUND_PRESETS["systemAsterisk"])
        if isinstance(value, int):
            self._play_message_beep(value)
        elif isinstance(value, str):
            self._play_custom_file(value)

    def _play_message_beep(self, value: int) -> None:
        try:
            import winsound

            winsound.MessageBeep(value)
        except Exception:
            pass

    def _play_custom_file(self, file_path: str) -> None:
        path = Path(str(file_path or ""))
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
