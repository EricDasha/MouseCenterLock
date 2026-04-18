"""
Application settings loading, migration, and persistence.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import uuid
from typing import Any, Dict, List, Optional

from app_logging import log_exception


if getattr(sys, "frozen", False):
    _BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    _RUN_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _RUN_DIR = _BASE_DIR

APP_DIR = _BASE_DIR
CONFIG_DEFAULT_PATH = os.path.join(APP_DIR, "Mconfig.json")
CONFIG_PATH = os.path.join(_RUN_DIR, "Mconfig.json")
LEGACY_CONFIG_PATH = os.path.join(_RUN_DIR, "config.json")

CLICKER_PRESETS = {
    "custom": None,
    "efficient": 100,
    "extreme": 10,
}

CLICKER_SOUND_PRESETS = {
    "systemAsterisk": 0x00000040,
    "systemExclamation": 0x00000030,
    "systemQuestion": 0x00000020,
    "systemHand": 0x00000010,
    "custom": None,
}

CLICKER_TRIGGER_MODES = {
    "toggle": "clicker.trigger.toggle",
    "holdKey": "clicker.trigger.holdKey",
    "holdMouseButton": "clicker.trigger.holdMouseButton",
}

MOUSE_TRIGGER_BUTTONS = ("middle", "x1", "x2", "left", "right")


def load_json(path: str, default: Any) -> Any:
    """Load JSON from file, returning default on error."""
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def deep_copy(data: Any) -> Any:
    """Return a detached copy of nested config data."""
    return copy.deepcopy(data)


def normalize_hotkey(config: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize hotkey dictionaries to the expected shape."""
    data = config if isinstance(config, dict) else {}
    normalized = deep_copy(fallback)
    for field in ["modCtrl", "modAlt", "modShift", "modWin", "key"]:
        if field == "key":
            normalized[field] = str(data.get(field, normalized[field]) or "")
        else:
            normalized[field] = bool(data.get(field, normalized[field]))
    return normalized


class SettingsManager:
    """Manages application settings including loading, validation, and saving."""

    DEFAULT_HOTKEYS = {
        "lock": {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "F9"},
        "unlock": {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "F10"},
        "toggle": {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "K"},
    }
    DEFAULT_CLICKER_HOTKEY = {
        "modCtrl": False, "modAlt": False, "modShift": False, "modWin": False, "key": "F6",
    }
    DEFAULT_HOLD_KEY = {
        "modCtrl": False, "modAlt": False, "modShift": False, "modWin": False, "key": "F7",
    }
    DEFAULT_CLICKER_SOUND = {
        "enabled": False,
        "preset": "systemAsterisk",
        "customFile": "",
    }

    def __init__(self):
        self.loaded_from_path = ""
        self.last_error = ""
        data = None
        for candidate in [CONFIG_PATH, LEGACY_CONFIG_PATH, CONFIG_DEFAULT_PATH]:
            loaded = load_json(candidate, None)
            if isinstance(loaded, dict):
                self.loaded_from_path = candidate
                data = loaded
                break
        if data is None:
            data = {}

        self.data: Dict[str, Any] = data if isinstance(data, dict) else {}
        self._set_defaults()

    def _set_defaults(self):
        """Ensure all required settings have default values."""
        self.data.setdefault("language", "zh-Hans")
        self.data.setdefault("theme", "dark")
        self.data.setdefault("hotkeys", self.DEFAULT_HOTKEYS.copy())
        self._ensure_clicker_profiles()

        for key in ["lock", "unlock", "toggle"]:
            if key not in self.data["hotkeys"]:
                self.data["hotkeys"][key] = self.DEFAULT_HOTKEYS[key].copy()
            else:
                for field in ["modCtrl", "modAlt", "modShift", "modWin", "key"]:
                    self.data["hotkeys"][key].setdefault(
                        field,
                        self.DEFAULT_HOTKEYS[key].get(field, False if field != "key" else ""),
                    )

        self.data.setdefault("recenter", {"enabled": True, "intervalMs": 250})
        self.data.setdefault("position", {"mode": "virtualCenter", "customX": 0, "customY": 0})
        window_specific = self.data.setdefault("windowSpecific", {})
        if "targetWindow" in window_specific and "targetWindows" not in window_specific:
            value = window_specific.pop("targetWindow")
            window_specific["targetWindows"] = [value] if value else []

        window_specific.setdefault("enabled", False)
        window_specific.setdefault("targetWindows", [])
        window_specific.setdefault("targetWindowHandle", 0)
        window_specific.setdefault("autoLockOnWindowFocus", False)
        window_specific.setdefault("resumeAfterWindowSwitch", False)
        self.data.setdefault("startup", {"launchOnBoot": False})
        self.data.setdefault("closeAction", "ask")

    def _default_clicker_profile(self) -> Dict[str, Any]:
        """Return the default clicker profile template."""
        return {
            "id": "default",
            "name": "默认方案",
            "enabled": False,
            "button": "left",
            "intervalMs": 100,
            "preset": "efficient",
            "sound": deep_copy(self.DEFAULT_CLICKER_SOUND),
            "triggers": {
                "mode": "toggle",
                "toggleHotkey": deep_copy(self.DEFAULT_CLICKER_HOTKEY),
                "holdKey": deep_copy(self.DEFAULT_HOLD_KEY),
                "holdMouseButton": "middle",
            },
        }

    def _normalize_clicker_profile(self, profile: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
        """Normalize a clicker profile from config."""
        base = self._default_clicker_profile()
        source = profile if isinstance(profile, dict) else {}

        normalized = deep_copy(base)
        normalized["id"] = str(source.get("id") or f"profile-{index + 1}")
        normalized["name"] = str(source.get("name") or base["name"])
        normalized["enabled"] = bool(source.get("enabled", False))
        normalized["button"] = source.get("button", "left") if source.get("button") in ("left", "right", "middle") else "left"
        normalized["intervalMs"] = max(1, int(source.get("intervalMs", 100)))
        preset = source.get("preset")
        normalized["preset"] = preset if preset in CLICKER_PRESETS else self._resolve_preset(normalized["intervalMs"])

        sound = source.get("sound", {})
        normalized["sound"]["enabled"] = bool(sound.get("enabled", normalized["sound"]["enabled"]))
        sound_preset = sound.get("preset", normalized["sound"]["preset"])
        normalized["sound"]["preset"] = sound_preset if sound_preset in CLICKER_SOUND_PRESETS else "systemAsterisk"
        normalized["sound"]["customFile"] = str(sound.get("customFile", "") or "")

        triggers = source.get("triggers", {})
        legacy_toggle = source.get("hotkeyToggle", {})
        normalized["triggers"]["mode"] = triggers.get("mode", "toggle")
        if normalized["triggers"]["mode"] not in CLICKER_TRIGGER_MODES:
            normalized["triggers"]["mode"] = "toggle"
        normalized["triggers"]["toggleHotkey"] = normalize_hotkey(
            triggers.get("toggleHotkey", legacy_toggle), self.DEFAULT_CLICKER_HOTKEY
        )
        normalized["triggers"]["holdKey"] = normalize_hotkey(
            triggers.get("holdKey", {}), self.DEFAULT_HOLD_KEY
        )
        hold_mouse_button = str(triggers.get("holdMouseButton", "middle") or "middle").lower()
        normalized["triggers"]["holdMouseButton"] = hold_mouse_button if hold_mouse_button in MOUSE_TRIGGER_BUTTONS else "middle"
        return normalized

    def _resolve_preset(self, interval_ms: int) -> str:
        """Resolve a click interval to its preset label."""
        normalized = max(1, int(interval_ms))
        for preset_key, preset_interval in CLICKER_PRESETS.items():
            if preset_interval == normalized:
                return preset_key
        return "custom"

    def _ensure_clicker_profiles(self):
        """Migrate legacy clicker config and normalize clicker profile storage."""
        profiles = self.data.get("clickerProfiles")
        if not isinstance(profiles, list) or not profiles:
            legacy_clicker = self.data.get("clicker", {})
            profile = self._default_clicker_profile()
            if isinstance(legacy_clicker, dict):
                legacy_profile = {
                    "id": "default",
                    "name": "默认方案",
                    "enabled": legacy_clicker.get("enabled", False),
                    "button": legacy_clicker.get("button", "left"),
                    "intervalMs": legacy_clicker.get("intervalMs", 100),
                    "preset": legacy_clicker.get("preset", self._resolve_preset(legacy_clicker.get("intervalMs", 100))),
                    "triggers": {
                        "mode": "toggle",
                        "toggleHotkey": legacy_clicker.get("hotkeyToggle", self.DEFAULT_CLICKER_HOTKEY),
                        "holdKey": self.DEFAULT_HOLD_KEY,
                        "holdMouseButton": "middle",
                    },
                }
                profile = self._normalize_clicker_profile(legacy_profile)
            profiles = [profile]
            self.data["clickerProfiles"] = profiles

        normalized_profiles: List[Dict[str, Any]] = []
        seen_ids = set()
        for index, profile in enumerate(profiles):
            normalized = self._normalize_clicker_profile(profile, index)
            if normalized["id"] in seen_ids:
                normalized["id"] = f"{normalized['id']}-{index + 1}"
            seen_ids.add(normalized["id"])
            normalized_profiles.append(normalized)

        if not normalized_profiles:
            normalized_profiles = [self._default_clicker_profile()]

        self.data["clickerProfiles"] = normalized_profiles
        active_id = str(self.data.get("activeClickerProfileId") or normalized_profiles[0]["id"])
        if not any(profile["id"] == active_id for profile in normalized_profiles):
            active_id = normalized_profiles[0]["id"]
        self.data["activeClickerProfileId"] = active_id
        self.data.pop("clickerActiveProfile", None)
        self.data.pop("clicker", None)

    def get_clicker_profiles(self) -> List[Dict[str, Any]]:
        """Return deep-copied clicker profiles."""
        return [deep_copy(profile) for profile in self.data.get("clickerProfiles", [])]

    def get_active_clicker_profile(self) -> Dict[str, Any]:
        """Return the active clicker profile."""
        active_id = self.data.get("activeClickerProfileId")
        for profile in self.data.get("clickerProfiles", []):
            if profile.get("id") == active_id:
                return deep_copy(profile)
        first = self.data.get("clickerProfiles", [self._default_clicker_profile()])[0]
        return deep_copy(first)

    def set_active_clicker_profile(self, profile_id: str) -> Dict[str, Any]:
        """Set the active clicker profile by id."""
        for profile in self.data.get("clickerProfiles", []):
            if profile.get("id") == profile_id:
                self.data["activeClickerProfileId"] = profile_id
                return deep_copy(profile)
        return self.get_active_clicker_profile()

    def upsert_clicker_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a clicker profile and make it active."""
        normalized = self._normalize_clicker_profile(profile, len(self.data.get("clickerProfiles", [])))
        profiles = self.data.setdefault("clickerProfiles", [])
        for index, existing in enumerate(profiles):
            if existing.get("id") == normalized["id"]:
                profiles[index] = normalized
                break
        else:
            if any(existing.get("id") == normalized["id"] for existing in profiles):
                normalized["id"] = uuid.uuid4().hex[:8]
            profiles.append(normalized)
        return self.set_active_clicker_profile(normalized["id"])

    def create_clicker_profile(self, name: str, base_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new clicker profile from the provided base."""
        profile = self._normalize_clicker_profile(base_profile or self.get_active_clicker_profile())
        profile["id"] = uuid.uuid4().hex[:8]
        profile["name"] = name.strip() or self._generate_profile_name()
        return self.upsert_clicker_profile(profile)

    def delete_clicker_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete a clicker profile while preserving at least one profile."""
        profiles = self.data.get("clickerProfiles", [])
        if len(profiles) <= 1:
            remaining = self._normalize_clicker_profile(profiles[0] if profiles else self._default_clicker_profile())
            remaining["id"] = "default"
            remaining["name"] = "默认方案"
            self.data["clickerProfiles"] = [remaining]
            return self.set_active_clicker_profile(remaining["id"])

        self.data["clickerProfiles"] = [profile for profile in profiles if profile.get("id") != profile_id]
        if not self.data["clickerProfiles"]:
            self.data["clickerProfiles"] = [self._default_clicker_profile()]
        default_target = self.data["clickerProfiles"][0]["id"]
        return self.set_active_clicker_profile(default_target)

    def _generate_profile_name(self) -> str:
        """Generate a readable default profile name."""
        existing_names = {str(profile.get("name", "")) for profile in self.data.get("clickerProfiles", [])}
        base = "新方案"
        index = 1
        while True:
            candidate = f"{base} {index}"
            if candidate not in existing_names:
                return candidate
            index += 1

    def save(self) -> bool:
        """Save settings to file. Returns True if successful."""
        try:
            self.last_error = ""
            payload = deep_copy(self.data)
            payload.pop("clickerActiveProfile", None)
            payload.pop("clicker", None)
            with open(CONFIG_PATH, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
            return True
        except Exception as exc:
            self.last_error = str(exc)
            log_exception("Failed to save settings", exc)
            return False
