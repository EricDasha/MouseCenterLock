"""
MouseCenterLock GUI Application
A Windows tool to lock the mouse cursor to the screen center.
"""
import sys
import json
import os
import ctypes
import copy
import html
import subprocess
import uuid
from pathlib import Path
from ctypes import wintypes
from typing import Optional, Dict, Any, List

from PySide6 import QtCore, QtGui, QtWidgets
try:
    from PySide6 import QtMultimedia
except Exception:
    QtMultimedia = None

# Import our modules
from win_api import (
    WM_HOTKEY, MSG,
    HOTKEY_ID_LOCK, HOTKEY_ID_UNLOCK, HOTKEY_ID_TOGGLE, HOTKEY_ID_CLICKER_TOGGLE,
    acquire_single_instance, release_single_instance, bring_existing_instance_to_front,
    get_virtual_screen_center, get_primary_screen_center,
    set_cursor_to, clip_cursor_to_point, unclip_cursor,
    get_active_window_info, format_hotkey_display,
    register_hotkeys, unregister_hotkeys, get_window_center,
    is_startup_enabled, set_startup_enabled, user32,
    get_window_process_name, click_mouse, GlobalInputListener
)
from widgets import HotkeyCapture, ProcessPickerDialog, CloseActionDialog, WindowResizeDialog


# --- Configuration & i18n Paths ---
if getattr(sys, 'frozen', False):
    _BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    _RUN_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _RUN_DIR = _BASE_DIR

APP_DIR = _BASE_DIR
I18N_DIR = os.path.join(APP_DIR, "pythonProject", "i18n")
if not os.path.exists(I18N_DIR):
    I18N_DIR = os.path.join(APP_DIR, "i18n")
ASSETS_DIR = os.path.join(APP_DIR, "pythonProject", "assets")
if not os.path.exists(ASSETS_DIR):
    ASSETS_DIR = os.path.join(APP_DIR, "assets")

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
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
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
        "lock": {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "L"},
        "unlock": {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "U"},
        "toggle": {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "K"}
    }
    DEFAULT_CLICKER_HOTKEY = {
        "modCtrl": False, "modAlt": False, "modShift": False, "modWin": False, "key": "F6"
    }
    DEFAULT_HOLD_KEY = {
        "modCtrl": False, "modAlt": False, "modShift": False, "modWin": False, "key": "F7"
    }
    DEFAULT_CLICKER_SOUND = {
        "enabled": False,
        "preset": "systemAsterisk",
        "customFile": ""
    }
    
    def __init__(self):
        self.loaded_from_path = ""
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

        # Ensure each hotkey has all required fields
        for key in ["lock", "unlock", "toggle"]:
            if key not in self.data["hotkeys"]:
                self.data["hotkeys"][key] = self.DEFAULT_HOTKEYS[key].copy()
            else:
                for field in ["modCtrl", "modAlt", "modShift", "modWin", "key"]:
                    self.data["hotkeys"][key].setdefault(
                        field, 
                        self.DEFAULT_HOTKEYS[key].get(field, False if field != "key" else "")
                    )
        
        self.data.setdefault("recenter", {"enabled": True, "intervalMs": 250})
        self.data.setdefault("position", {"mode": "virtualCenter", "customX": 0, "customY": 0})
        ws = self.data.setdefault("windowSpecific", {})
        # Migration: targetWindow (str) -> targetWindows (list)
        if "targetWindow" in ws and "targetWindows" not in ws:
            val = ws.pop("targetWindow")
            ws["targetWindows"] = [val] if val else []
            
        ws.setdefault("enabled", False)
        ws.setdefault("targetWindows", [])
        ws.setdefault("targetWindowHandle", 0)
        ws.setdefault("autoLockOnWindowFocus", False)
        ws.setdefault("resumeAfterWindowSwitch", False)
        self.data.setdefault("startup", {"launchOnBoot": False})
        self.data.setdefault("closeAction", "ask")  # ask, minimize, quit

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
        normalized["button"] = source.get("button", "left") if source.get("button") in ("left", "right") else "left"
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
        self.data["clickerActiveProfile"] = self.get_active_clicker_profile()
        self.data.setdefault("clicker", self.get_active_clicker_profile())

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
                self.data["clickerActiveProfile"] = deep_copy(profile)
                self.data["clicker"] = deep_copy(profile)
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
            self.data["clickerActiveProfile"] = self.get_active_clicker_profile()
            self.data["clicker"] = self.get_active_clicker_profile()
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False


class I18n:
    """Internationalization helper for loading and accessing translations."""
    
    SUPPORTED_LANGUAGES = ["en", "zh-Hans", "zh-Hant", "ja", "ko"]
    
    def __init__(self, lang_code: str):
        self.lang_code = lang_code if lang_code in self.SUPPORTED_LANGUAGES else "en"
        self.strings: Dict[str, str] = load_json(
            os.path.join(I18N_DIR, f"{self.lang_code}.json"), {}
        )
        # Load English as fallback
        if self.lang_code != "en":
            self._fallback = load_json(os.path.join(I18N_DIR, "en.json"), {})
        else:
            self._fallback = {}
    
    def t(self, key: str, fallback: str = "") -> str:
        """Get translation for key, with fallback chain."""
        if key in self.strings:
            return self.strings[key]
        if key in self._fallback:
            return self._fallback[key]
        return fallback if fallback else key


class NotificationManager:
    """Windows notification helper with native-toast fallback behavior."""

    def __init__(self, tray: QtWidgets.QSystemTrayIcon, app_id: str = "MouseCenterLock"):
        self.tray = tray
        self.app_id = app_id

    def show(
        self,
        title: str,
        message: str,
        icon: QtWidgets.QSystemTrayIcon.MessageIcon = QtWidgets.QSystemTrayIcon.Information,
        timeout_ms: int = 2000,
    ) -> None:
        """Try native Windows toast first, then fall back to tray balloons."""
        if not self._show_windows_toast(title, message):
            self.tray.showMessage(title, message, icon, timeout_ms)

    def _show_windows_toast(self, title: str, message: str) -> bool:
        """Best-effort native Windows toast via PowerShell WinRT APIs."""
        if os.name != "nt":
            return False

        escaped_title = html.escape(title, quote=False).replace("'", "''")
        escaped_message = html.escape(message, quote=False).replace("'", "''")
        escaped_app_id = self.app_id.replace("'", "''")
        script = (
            "$ErrorActionPreference='Stop';"
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null;"
            "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime] > $null;"
            f"$xml=@\"<toast><visual><binding template='ToastGeneric'><text>{escaped_title}</text>"
            f"<text>{escaped_message}</text></binding></visual></toast>\"@;"
            "$doc=New-Object Windows.Data.Xml.Dom.XmlDocument;"
            "$doc.LoadXml($xml);"
            "$toast=[Windows.UI.Notifications.ToastNotification]::new($doc);"
            f"$notifier=[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{escaped_app_id}');"
            "$notifier.Show($toast);"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                check=True,
                timeout=4,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return True
        except Exception:
            return False


class ClickerSoundPlayer(QtCore.QObject):
    """Play clicker start sounds from system presets or local files."""

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
            winsound.MessageBeep(CLICKER_SOUND_PRESETS.get(preset, CLICKER_SOUND_PRESETS["systemAsterisk"]))
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


# --- Native Event Filter for Hotkeys ---
class HotkeyEmitter(QtCore.QObject):
    """Emits signals when hotkeys are pressed."""
    hotkeyPressed = QtCore.Signal(int)


class NativeEventFilter(QtCore.QAbstractNativeEventFilter):
    """Filters native Windows messages to detect hotkey presses."""
    
    def __init__(self, emitter: HotkeyEmitter):
        super().__init__()
        self._emitter = emitter
    
    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
            if msg.message == WM_HOTKEY:
                self._emitter.hotkeyPressed.emit(msg.wParam)
        return False


class MainWindow(QtWidgets.QMainWindow):
    """Main application window."""
    
    def __init__(self, settings: SettingsManager, i18n: I18n):
        super().__init__()
        self.settings = settings
        self.i18n = i18n
        
        self._locked = False
        self._clicker_running = False
        self._hold_trigger_pressed = False
        self._auto_lock_suspended = False
        self._force_lock = False
        self._last_active_window = ""
        self._custom_icon: Optional[QtGui.QIcon] = None
        self._notification_manager: Optional[NotificationManager] = None
        self._sound_player = ClickerSoundPlayer(self)
        self._input_listener = GlobalInputListener(
            on_key_event=self._handle_global_key_event,
            on_mouse_event=self._handle_global_mouse_event,
        )
        self._selected_profile_id = self.settings.data.get("activeClickerProfileId", "default")
        self._profile_dirty = False
        
        self._setup_window()
        self._setup_timers()
        self._build_ui()
        self._apply_theme()
        self._create_tray()
        self._input_listener.start()
    
    @property
    def locked(self) -> bool:
        return self._locked
    
    @locked.setter
    def locked(self, value: bool):
        self._locked = value
        self._on_lock_state_changed()

    @property
    def clicker_running(self) -> bool:
        return self._clicker_running

    def _get_active_clicker_profile(self) -> Dict[str, Any]:
        """Return the active clicker profile from settings."""
        profile = self.settings.get_active_clicker_profile()
        self.settings.data["clickerActiveProfile"] = deep_copy(profile)
        self.settings.data["clicker"] = deep_copy(profile)
        return profile

    def _notify(self, message: str, timeout_ms: int = 2000) -> None:
        """Show a Windows notification using the configured fallback chain."""
        if self._notification_manager is not None:
            self._notification_manager.show(
                self.i18n.t("app.title", "Mouse Center Lock"),
                message,
                QtWidgets.QSystemTrayIcon.Information,
                timeout_ms,
            )
        elif hasattr(self, "tray"):
            self.tray.showMessage(
                self.i18n.t("app.title", "Mouse Center Lock"),
                message,
                QtWidgets.QSystemTrayIcon.Information,
                timeout_ms,
            )
    
    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle(self.i18n.t("app.title", "Mouse Center Lock"))
        self.setMinimumSize(450, 500)
        self.resize(550, 680)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        
        # Load window icon
        self._custom_icon = self._load_external_icon()
        icon = self._custom_icon or self._make_icon(False)
        QtWidgets.QApplication.setWindowIcon(icon)
        self.setWindowIcon(icon)
    
    def _setup_timers(self):
        """Setup timers for recentering and window focus checking."""
        self.recenterTimer = QtCore.QTimer(self)
        self.recenterTimer.timeout.connect(self._on_recenter_tick)

        self.clickerTimer = QtCore.QTimer(self)
        self.clickerTimer.timeout.connect(self._on_clicker_tick)
        
        self.windowFocusTimer = QtCore.QTimer(self)
        self.windowFocusTimer.timeout.connect(self._check_window_focus)
        self.windowFocusTimer.start(500)
    
    def _build_ui(self):
        """Build the main UI."""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Mode tabs
        self.modeTabs = QtWidgets.QTabBar()
        self.modeTabs.addTab(self.i18n.t("mode.simple", "Simple"))
        self.modeTabs.addTab(self.i18n.t("mode.advanced", "Advanced"))
        self.modeTabs.currentChanged.connect(self._on_mode_changed)
        layout.addWidget(self.modeTabs)
        
        # Stacked pages
        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self._build_simple_page())
        self.stack.addWidget(self._build_advanced_page())
        layout.addWidget(self.stack)
    
    def _build_simple_page(self) -> QtWidgets.QWidget:
        """Build the simple mode page."""
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(16)
        
        # Status badge
        self.statusBadge = QtWidgets.QLabel()
        self.statusBadge.setAlignment(QtCore.Qt.AlignCenter)
        self.statusBadge.setFixedHeight(56)
        self._update_status_badge()
        layout.addWidget(self.statusBadge)

        # Configuration card
        self.configCard = self._build_info_card(
            self.i18n.t("simple.config.title", "Current Configuration")
        )
        self.configLabel = QtWidgets.QLabel()
        self.configLabel.setWordWrap(True)
        self.configLabel.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.configLabel.setStyleSheet("color: rgba(235, 235, 245, 0.90); font-size: 13px; line-height: 1.6;")
        self.configCard.layout().addWidget(self.configLabel)
        layout.addWidget(self.configCard)

        # Hotkeys card
        self.hotkeysCard = self._build_info_card(
            self.i18n.t("simple.hotkeys.title", "Hotkeys")
        )
        self.hotkeysLabel = QtWidgets.QLabel()
        self.hotkeysLabel.setWordWrap(True)
        self.hotkeysLabel.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.hotkeysLabel.setStyleSheet("color: rgba(235, 235, 245, 0.90); font-size: 13px; font-family: 'Consolas', 'Courier New', monospace; line-height: 1.8;")
        self.hotkeysCard.layout().addWidget(self.hotkeysLabel)
        layout.addWidget(self.hotkeysCard)
        
        self._update_simple_info()
        
        layout.addStretch(1)
        
        # Toggle button
        self.toggleBtn = QtWidgets.QPushButton()
        self.toggleBtn.setFixedHeight(56)
        self.toggleBtn.setCursor(QtCore.Qt.PointingHandCursor)
        self.toggleBtn.clicked.connect(self.toggle_lock)
        self._update_toggle_button()
        layout.addWidget(self.toggleBtn)

        # Auto clicker button
        self.clickerBtn = QtWidgets.QPushButton()
        self.clickerBtn.setFixedHeight(48)
        self.clickerBtn.setCursor(QtCore.Qt.PointingHandCursor)
        self.clickerBtn.clicked.connect(self.toggle_clicker)
        self._update_clicker_button()
        layout.addWidget(self.clickerBtn)
        
        # Hint
        hint = QtWidgets.QLabel(self.i18n.t("simple.hint", "Use hotkeys for quick access ⌨️"))
        hint.setAlignment(QtCore.Qt.AlignCenter)
        hint.setStyleSheet("color: rgba(142, 142, 147, 0.95); font-size: 12px;")
        layout.addWidget(hint)
        
        return page
    
    def _build_advanced_page(self) -> QtWidgets.QWidget:
        """Build the advanced settings page."""
        page = QtWidgets.QWidget()
        
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(16)
        
        # --- Hotkeys Section ---
        layout.addWidget(self._section_label(self.i18n.t("section.hotkeys", "Hotkeys")))
        
        hotkey_grid = QtWidgets.QGridLayout()
        hotkey_grid.setSpacing(12)
        
        # Lock hotkey
        hotkey_grid.addWidget(QtWidgets.QLabel(self.i18n.t("hotkey.lock", "Lock")), 0, 0)
        self.lockHotkeyCapture = HotkeyCapture(i18n=self.i18n)
        self.lockHotkeyCapture.set_hotkey(self.settings.data["hotkeys"]["lock"])
        hotkey_grid.addWidget(self.lockHotkeyCapture, 0, 1)
        
        # Unlock hotkey
        hotkey_grid.addWidget(QtWidgets.QLabel(self.i18n.t("hotkey.unlock", "Unlock")), 1, 0)
        self.unlockHotkeyCapture = HotkeyCapture(i18n=self.i18n)
        self.unlockHotkeyCapture.set_hotkey(self.settings.data["hotkeys"]["unlock"])
        hotkey_grid.addWidget(self.unlockHotkeyCapture, 1, 1)
        
        # Toggle hotkey
        hotkey_grid.addWidget(QtWidgets.QLabel(self.i18n.t("hotkey.toggle", "Toggle")), 2, 0)
        self.toggleHotkeyCapture = HotkeyCapture(i18n=self.i18n)
        self.toggleHotkeyCapture.set_hotkey(self.settings.data["hotkeys"]["toggle"])
        hotkey_grid.addWidget(self.toggleHotkeyCapture, 2, 1)

        hotkey_hint = QtWidgets.QLabel(
            self.i18n.t("clicker.hotkey.profileHint", "Auto clicker trigger keys are configured per clicker profile below.")
        )
        hotkey_hint.setWordWrap(True)
        hotkey_hint.setStyleSheet("color: rgba(142, 142, 147, 0.95); font-size: 12px;")
        hotkey_grid.addWidget(hotkey_hint, 3, 0, 1, 2)
        
        layout.addLayout(hotkey_grid)
        
        # --- Behavior Section ---
        layout.addWidget(self._section_label(self.i18n.t("section.behavior", "Behavior")))
        
        # Recenter enabled
        self.recenterCheck = QtWidgets.QCheckBox(self.i18n.t("recenter.enabled", "Enable periodic recentering"))
        self.recenterCheck.setChecked(self.settings.data["recenter"].get("enabled", True))
        layout.addWidget(self.recenterCheck)
        
        # Recenter interval
        interval_layout = QtWidgets.QHBoxLayout()
        interval_layout.addWidget(QtWidgets.QLabel(self.i18n.t("recenter.interval", "Interval (ms)")))
        self.recenterSpin = QtWidgets.QSpinBox()
        self.recenterSpin.setRange(16, 5000)
        self.recenterSpin.setSingleStep(16)
        self.recenterSpin.setValue(self.settings.data["recenter"].get("intervalMs", 250))
        interval_layout.addWidget(self.recenterSpin)
        interval_layout.addStretch()
        layout.addLayout(interval_layout)

        # --- Auto Clicker Section ---
        layout.addWidget(self._section_label(self.i18n.t("clicker.section", "Auto Clicker")))

        profile_layout = QtWidgets.QHBoxLayout()
        profile_layout.addWidget(QtWidgets.QLabel(self.i18n.t("clicker.profile.select", "Profile")))
        self.clickerProfileCombo = QtWidgets.QComboBox()
        self.clickerProfileCombo.currentIndexChanged.connect(self._on_clicker_profile_selected)
        profile_layout.addWidget(self.clickerProfileCombo)
        layout.addLayout(profile_layout)

        profile_name_layout = QtWidgets.QHBoxLayout()
        profile_name_layout.addWidget(QtWidgets.QLabel(self.i18n.t("clicker.profile.name", "Profile Name")))
        self.clickerProfileNameEdit = QtWidgets.QLineEdit()
        self.clickerProfileNameEdit.setPlaceholderText(self.i18n.t("clicker.profile.placeholder", "Input a profile name"))
        profile_name_layout.addWidget(self.clickerProfileNameEdit)
        layout.addLayout(profile_name_layout)

        profile_btn_layout = QtWidgets.QHBoxLayout()
        self.newClickerProfileBtn = QtWidgets.QPushButton(self.i18n.t("clicker.profile.new", "New"))
        self.newClickerProfileBtn.clicked.connect(self._create_clicker_profile)
        profile_btn_layout.addWidget(self.newClickerProfileBtn)
        self.saveClickerProfileBtn = QtWidgets.QPushButton(self.i18n.t("clicker.profile.save", "Save Profile"))
        self.saveClickerProfileBtn.clicked.connect(self._save_clicker_profile)
        profile_btn_layout.addWidget(self.saveClickerProfileBtn)
        self.deleteClickerProfileBtn = QtWidgets.QPushButton(self.i18n.t("clicker.profile.delete", "Delete"))
        self.deleteClickerProfileBtn.clicked.connect(self._delete_clicker_profile)
        profile_btn_layout.addWidget(self.deleteClickerProfileBtn)
        profile_btn_layout.addStretch()
        layout.addLayout(profile_btn_layout)

        self.clickerEnabledCheck = QtWidgets.QCheckBox(self.i18n.t("clicker.enabled", "Enable auto clicker"))
        layout.addWidget(self.clickerEnabledCheck)

        clicker_button_layout = QtWidgets.QHBoxLayout()
        clicker_button_layout.addWidget(QtWidgets.QLabel(self.i18n.t("clicker.button", "Click Button")))
        self.clickerButtonCombo = QtWidgets.QComboBox()
        self.clickerButtonCombo.addItem(self.i18n.t("clicker.button.left", "Left Click"), "left")
        self.clickerButtonCombo.addItem(self.i18n.t("clicker.button.right", "Right Click"), "right")
        self.clickerButtonCombo.addItem(self.i18n.t("clicker.button.middle", "Middle Click"), "middle")
        clicker_button_layout.addWidget(self.clickerButtonCombo)
        clicker_button_layout.addStretch()
        layout.addLayout(clicker_button_layout)

        clicker_preset_layout = QtWidgets.QHBoxLayout()
        clicker_preset_layout.addWidget(QtWidgets.QLabel(self.i18n.t("clicker.preset", "Click Speed")))
        self.clickerPresetCombo = QtWidgets.QComboBox()
        self.clickerPresetCombo.addItem(self.i18n.t("clicker.preset.efficient", "Efficient Mode"), "efficient")
        self.clickerPresetCombo.addItem(self.i18n.t("clicker.preset.extreme", "Extreme Mode"), "extreme")
        self.clickerPresetCombo.addItem(self.i18n.t("clicker.preset.custom", "Custom"), "custom")
        self.clickerPresetCombo.currentIndexChanged.connect(self._on_clicker_preset_changed)
        clicker_preset_layout.addWidget(self.clickerPresetCombo)
        clicker_preset_layout.addStretch()
        layout.addLayout(clicker_preset_layout)

        self.clickerPresetHint = QtWidgets.QLabel()
        self.clickerPresetHint.setWordWrap(True)
        self.clickerPresetHint.setStyleSheet("color: rgba(142, 142, 147, 0.95); font-size: 12px;")
        layout.addWidget(self.clickerPresetHint)

        clicker_interval_layout = QtWidgets.QHBoxLayout()
        self.clickerIntervalLabel = QtWidgets.QLabel(self.i18n.t("clicker.interval", "Click Interval (ms)"))
        clicker_interval_layout.addWidget(self.clickerIntervalLabel)
        self.clickerIntervalSpin = QtWidgets.QSpinBox()
        self.clickerIntervalSpin.setRange(1, 5000)
        self.clickerIntervalSpin.setSingleStep(10)
        self.clickerIntervalSpin.setSuffix(" ms")
        clicker_interval_layout.addWidget(self.clickerIntervalSpin)
        clicker_interval_layout.addStretch()
        layout.addLayout(clicker_interval_layout)

        trigger_mode_layout = QtWidgets.QHBoxLayout()
        trigger_mode_layout.addWidget(QtWidgets.QLabel(self.i18n.t("clicker.trigger.mode", "Trigger Mode")))
        self.clickerTriggerModeCombo = QtWidgets.QComboBox()
        self.clickerTriggerModeCombo.addItem(self.i18n.t("clicker.trigger.toggle", "Toggle"), "toggle")
        self.clickerTriggerModeCombo.addItem(self.i18n.t("clicker.trigger.holdKey", "Hold Key"), "holdKey")
        self.clickerTriggerModeCombo.addItem(self.i18n.t("clicker.trigger.holdMouseButton", "Hold Mouse Button"), "holdMouseButton")
        self.clickerTriggerModeCombo.currentIndexChanged.connect(self._sync_clicker_trigger_controls)
        trigger_mode_layout.addWidget(self.clickerTriggerModeCombo)
        trigger_mode_layout.addStretch()
        layout.addLayout(trigger_mode_layout)

        toggle_hotkey_layout = QtWidgets.QHBoxLayout()
        self.clickerToggleHotkeyLabel = QtWidgets.QLabel(self.i18n.t("clicker.hotkey", "Auto Clicker Toggle"))
        toggle_hotkey_layout.addWidget(self.clickerToggleHotkeyLabel)
        self.clickerToggleHotkeyCapture = HotkeyCapture(i18n=self.i18n)
        toggle_hotkey_layout.addWidget(self.clickerToggleHotkeyCapture)
        layout.addLayout(toggle_hotkey_layout)

        hold_key_layout = QtWidgets.QHBoxLayout()
        self.clickerHoldKeyLabel = QtWidgets.QLabel(self.i18n.t("clicker.trigger.holdKey.input", "Hold Key"))
        hold_key_layout.addWidget(self.clickerHoldKeyLabel)
        self.clickerHoldKeyCapture = HotkeyCapture(i18n=self.i18n)
        hold_key_layout.addWidget(self.clickerHoldKeyCapture)
        layout.addLayout(hold_key_layout)

        hold_mouse_layout = QtWidgets.QHBoxLayout()
        self.clickerHoldMouseLabel = QtWidgets.QLabel(self.i18n.t("clicker.trigger.holdMouseButton.input", "Hold Mouse Button"))
        hold_mouse_layout.addWidget(self.clickerHoldMouseLabel)
        self.clickerHoldMouseCombo = QtWidgets.QComboBox()
        self.clickerHoldMouseCombo.addItem(self.i18n.t("clicker.mouse.middle", "Middle Button"), "middle")
        self.clickerHoldMouseCombo.addItem(self.i18n.t("clicker.mouse.x1", "Side Button X1 (usually Back)"), "x1")
        self.clickerHoldMouseCombo.addItem(self.i18n.t("clicker.mouse.x2", "Side Button X2 (usually Forward)"), "x2")
        self.clickerHoldMouseCombo.addItem(self.i18n.t("clicker.mouse.left", "Left Button"), "left")
        self.clickerHoldMouseCombo.addItem(self.i18n.t("clicker.mouse.right", "Right Button"), "right")
        hold_mouse_layout.addWidget(self.clickerHoldMouseCombo)
        hold_mouse_layout.addStretch()
        layout.addLayout(hold_mouse_layout)

        sound_enabled_layout = QtWidgets.QHBoxLayout()
        self.clickerSoundEnabledCheck = QtWidgets.QCheckBox(self.i18n.t("clicker.sound.enabled", "Play start sound"))
        self.clickerSoundEnabledCheck.toggled.connect(self._sync_clicker_sound_controls)
        sound_enabled_layout.addWidget(self.clickerSoundEnabledCheck)
        sound_enabled_layout.addStretch()
        layout.addLayout(sound_enabled_layout)

        sound_preset_layout = QtWidgets.QHBoxLayout()
        self.clickerSoundPresetLabel = QtWidgets.QLabel(self.i18n.t("clicker.sound.preset", "Start Sound"))
        sound_preset_layout.addWidget(self.clickerSoundPresetLabel)
        self.clickerSoundPresetCombo = QtWidgets.QComboBox()
        self.clickerSoundPresetCombo.addItem(self.i18n.t("clicker.sound.preset.systemAsterisk", "System Asterisk"), "systemAsterisk")
        self.clickerSoundPresetCombo.addItem(self.i18n.t("clicker.sound.preset.systemExclamation", "System Exclamation"), "systemExclamation")
        self.clickerSoundPresetCombo.addItem(self.i18n.t("clicker.sound.preset.systemQuestion", "System Question"), "systemQuestion")
        self.clickerSoundPresetCombo.addItem(self.i18n.t("clicker.sound.preset.systemHand", "System Hand"), "systemHand")
        self.clickerSoundPresetCombo.addItem(self.i18n.t("clicker.sound.preset.custom", "Custom File"), "custom")
        self.clickerSoundPresetCombo.currentIndexChanged.connect(self._sync_clicker_sound_controls)
        sound_preset_layout.addWidget(self.clickerSoundPresetCombo)
        self.clickerSoundPreviewBtn = QtWidgets.QPushButton(self.i18n.t("clicker.sound.preview", "Preview"))
        self.clickerSoundPreviewBtn.clicked.connect(self._preview_clicker_sound)
        sound_preset_layout.addWidget(self.clickerSoundPreviewBtn)
        sound_preset_layout.addStretch()
        layout.addLayout(sound_preset_layout)

        custom_sound_layout = QtWidgets.QHBoxLayout()
        self.clickerCustomSoundPathEdit = QtWidgets.QLineEdit()
        self.clickerCustomSoundPathEdit.setPlaceholderText(self.i18n.t("clicker.sound.path.placeholder", "Select a local audio file"))
        custom_sound_layout.addWidget(self.clickerCustomSoundPathEdit)
        self.clickerCustomSoundBrowseBtn = QtWidgets.QPushButton(self.i18n.t("browse", "Browse"))
        self.clickerCustomSoundBrowseBtn.clicked.connect(self._browse_clicker_sound_file)
        custom_sound_layout.addWidget(self.clickerCustomSoundBrowseBtn)
        layout.addLayout(custom_sound_layout)

        self.clickerConfigHint = QtWidgets.QLabel(
            self.i18n.t(
                "clicker.config.hint",
                "Restore defaults by deleting Mconfig.json. Legacy config.json is still read for compatibility."
            )
        )
        self.clickerConfigHint.setWordWrap(True)
        self.clickerConfigHint.setStyleSheet("color: rgba(142, 142, 147, 0.95); font-size: 12px;")
        layout.addWidget(self.clickerConfigHint)
        self._populate_clicker_profiles()
        
        # --- Position Section ---
        layout.addWidget(self._section_label(self.i18n.t("position.title", "Target Position")))
        
        pos_layout = QtWidgets.QHBoxLayout()
        self.posCombo = QtWidgets.QComboBox()
        self.posCombo.addItem(self.i18n.t("position.virtualCenter", "Virtual screen center"), "virtualCenter")
        self.posCombo.addItem(self.i18n.t("position.primaryCenter", "Primary screen center"), "primaryCenter")
        self.posCombo.addItem(self.i18n.t("position.custom", "Custom"), "custom")
        
        current_mode = self.settings.data["position"].get("mode", "virtualCenter")
        for i in range(self.posCombo.count()):
            if self.posCombo.itemData(i) == current_mode:
                self.posCombo.setCurrentIndex(i)
                break
        pos_layout.addWidget(self.posCombo)
        layout.addLayout(pos_layout)
        
        # Custom position
        custom_layout = QtWidgets.QHBoxLayout()
        custom_layout.addWidget(QtWidgets.QLabel("X:"))
        self.customXSpin = QtWidgets.QSpinBox()
        self.customXSpin.setRange(-10000, 10000)
        self.customXSpin.setValue(self.settings.data["position"].get("customX", 0))
        custom_layout.addWidget(self.customXSpin)
        custom_layout.addWidget(QtWidgets.QLabel("Y:"))
        self.customYSpin = QtWidgets.QSpinBox()
        self.customYSpin.setRange(-10000, 10000)
        self.customYSpin.setValue(self.settings.data["position"].get("customY", 0))
        custom_layout.addWidget(self.customYSpin)
        custom_layout.addStretch()
        layout.addLayout(custom_layout)
        
        # --- Window Specific Section ---
        layout.addWidget(self._section_label(self.i18n.t("window.specific.title", "Window-Specific Locking")))
        
        self.windowSpecificCheck = QtWidgets.QCheckBox(
            self.i18n.t("window.specific.enabled", "Enable window-specific locking")
        )
        self.windowSpecificCheck.setChecked(
            self.settings.data["windowSpecific"].get("enabled", False)
        )
        layout.addWidget(self.windowSpecificCheck)
        
        # Target Windows List Management
        list_layout = QtWidgets.QVBoxLayout()
        list_layout.setSpacing(8)
        
        # List widget
        list_label = QtWidgets.QLabel(self.i18n.t("window.specific.listLabel", "Target Windows List"))
        list_layout.addWidget(list_label)
        
        self.targetList = QtWidgets.QListWidget()
        self.targetList.setFixedHeight(120)
        self.targetList.setStyleSheet("""
            QListWidget {
                background: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(128, 128, 128, 0.3);
                border-radius: 6px;
                padding: 4px;
            }
        """)
        # Populate existing items
        for win_title in self.settings.data["windowSpecific"].get("targetWindows", []):
            self.targetList.addItem(win_title)
        list_layout.addWidget(self.targetList)
        
        # Input controls
        input_layout = QtWidgets.QHBoxLayout()
        
        self.manualInputEdit = QtWidgets.QLineEdit()
        self.manualInputEdit.setPlaceholderText(self.i18n.t("window.specific.placeholder", "Target window title"))
        input_layout.addWidget(self.manualInputEdit)
        
        self.pickProcessBtn = QtWidgets.QPushButton(self.i18n.t("window.specific.pick", "Pick Process"))
        self.pickProcessBtn.clicked.connect(self._pick_process)
        input_layout.addWidget(self.pickProcessBtn)
        
        list_layout.addLayout(input_layout)
        
        # Action buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.addBtn = QtWidgets.QPushButton(self.i18n.t("window.specific.add", "Add"))
        self.addBtn.clicked.connect(self._add_target_window)
        btn_layout.addWidget(self.addBtn)
        
        self.removeBtn = QtWidgets.QPushButton(self.i18n.t("window.specific.remove", "Remove"))
        self.removeBtn.clicked.connect(self._remove_target_window)
        btn_layout.addWidget(self.removeBtn)
        
        btn_layout.addStretch()
        list_layout.addLayout(btn_layout)
        
        layout.addLayout(list_layout)
        
        self.autoLockCheck = QtWidgets.QCheckBox(
            self.i18n.t("window.specific.autoLock", "Auto lock/unlock on window switch")
        )
        self.autoLockCheck.setChecked(
            self.settings.data["windowSpecific"].get("autoLockOnWindowFocus", False)
        )
        layout.addWidget(self.autoLockCheck)

        self.resumeAfterSwitchCheck = QtWidgets.QCheckBox(
            self.i18n.t("window.specific.resumeAfterSwitch", "Auto re-lock after leaving and re-entering target window (for manual unlock)")
        )
        self.resumeAfterSwitchCheck.setChecked(
            self.settings.data["windowSpecific"].get("resumeAfterWindowSwitch", False)
        )
        layout.addWidget(self.resumeAfterSwitchCheck)
        
        # --- Window Tools Section ---
        layout.addWidget(self._section_label(self.i18n.t("section.windowTools", "Window Tools")))
        
        self.resizeCenterBtn = QtWidgets.QPushButton(
            self.i18n.t("windowTools.resizeCenter", "Resize & Center Window")
        )
        self.resizeCenterBtn.setFixedHeight(40)
        self.resizeCenterBtn.setCursor(QtCore.Qt.PointingHandCursor)
        self.resizeCenterBtn.clicked.connect(self._open_window_resize)
        layout.addWidget(self.resizeCenterBtn)
        
        # --- Settings Section ---
        layout.addWidget(self._section_label(self.i18n.t("section.settings", "Settings")))
        
        # Language
        lang_layout = QtWidgets.QHBoxLayout()
        lang_layout.addWidget(QtWidgets.QLabel(self.i18n.t("language.title", "Language")))
        self.langCombo = QtWidgets.QComboBox()
        self.langCombo.addItem("English", "en")
        self.langCombo.addItem("简体中文", "zh-Hans")
        self.langCombo.addItem("繁體中文", "zh-Hant")
        self.langCombo.addItem("日本語", "ja")
        self.langCombo.addItem("한국어", "ko")
        
        current_lang = self.settings.data.get("language", "zh-Hans")
        for i in range(self.langCombo.count()):
            if self.langCombo.itemData(i) == current_lang:
                self.langCombo.setCurrentIndex(i)
                break
        lang_layout.addWidget(self.langCombo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)
        
        # Theme
        theme_layout = QtWidgets.QHBoxLayout()
        theme_layout.addWidget(QtWidgets.QLabel(self.i18n.t("theme.title", "Theme")))
        self.themeCombo = QtWidgets.QComboBox()
        self.themeCombo.addItem(self.i18n.t("theme.dark", "Dark"), "dark")
        self.themeCombo.addItem(self.i18n.t("theme.light", "Light"), "light")
        
        current_theme = self.settings.data.get("theme", "dark")
        for i in range(self.themeCombo.count()):
            if self.themeCombo.itemData(i) == current_theme:
                self.themeCombo.setCurrentIndex(i)
                break
        theme_layout.addWidget(self.themeCombo)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)
        
        # Close Action Reset
        close_action_layout = QtWidgets.QHBoxLayout()
        close_action_layout.addWidget(QtWidgets.QLabel(self.i18n.t("close.action.title", "Close Behavior")))
        self.resetCloseActionBtn = QtWidgets.QPushButton(self.i18n.t("close.action.reset", "Reset 'Don't ask again'"))
        self.resetCloseActionBtn.clicked.connect(self._reset_close_action)
        close_action_layout.addWidget(self.resetCloseActionBtn)
        close_action_layout.addStretch()
        layout.addLayout(close_action_layout)
        
        # Startup
        self.startupCheck = QtWidgets.QCheckBox(
            self.i18n.t("startup.autostart", "Launch on system startup")
        )
        self.startupCheck.setChecked(is_startup_enabled())
        layout.addWidget(self.startupCheck)
        
        layout.addStretch()
        
        # Apply button
        self.applyBtn = QtWidgets.QPushButton(self.i18n.t("apply", "Apply"))
        self.applyBtn.setFixedHeight(44)
        self.applyBtn.clicked.connect(self._on_apply)
        layout.addWidget(self.applyBtn)
        
        scroll.setWidget(content)
        
        page_layout = QtWidgets.QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        
        return page
    
    def _section_label(self, text: str) -> QtWidgets.QLabel:
        """Create a styled section label."""
        label = QtWidgets.QLabel(text)
        label.setStyleSheet("font-weight: 600; font-size: 15px; margin-top: 8px;")
        return label
    
    def _build_info_card(self, title: str) -> QtWidgets.QFrame:
        """Create a styled information card with title."""
        card = QtWidgets.QFrame()
        card.setFrameShape(QtWidgets.QFrame.NoFrame)
        card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
        """)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)
        
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("font-weight: 600; font-size: 14px; color: rgba(10, 132, 255, 1.0);")
        card_layout.addWidget(title_label)
        
        return card
    
    def _pick_process(self):
        """Open process picker dialog."""
        dialog = ProcessPickerDialog(self, self.i18n)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            selected = dialog.get_selected_process()
            if selected:
                self.manualInputEdit.setText(selected)

    def _open_window_resize(self):
        """Open window resize & center dialog."""
        dialog = WindowResizeDialog(self, self.i18n)
        dialog.exec()

    def _add_target_window(self):
        """Add current input to target list."""
        text = self.manualInputEdit.text().strip()
        if not text:
            return
            
        # Check for duplicates
        items = [self.targetList.item(i).text() for i in range(self.targetList.count())]
        if text in items:
            return
            
        self.targetList.addItem(text)
        self.manualInputEdit.clear()

    def _remove_target_window(self):
        """Remove selected item from target list."""
        row = self.targetList.currentRow()
        if row >= 0:
            self.targetList.takeItem(row)

    def _current_profile_form_data(self) -> Dict[str, Any]:
        """Build a clicker profile from the current form controls."""
        active = self._get_active_clicker_profile()
        profile_id = self._selected_profile_id or active.get("id", "default")
        profile_name = self.clickerProfileNameEdit.text().strip() or active.get("name", "默认方案")
        preset = self.clickerPresetCombo.currentData() or "custom"
        interval_ms = self.clickerIntervalSpin.value()
        return {
            "id": profile_id,
            "name": profile_name,
            "enabled": self.clickerEnabledCheck.isChecked(),
            "button": self.clickerButtonCombo.currentData(),
            "preset": preset,
            "intervalMs": interval_ms,
            "sound": {
                "enabled": self.clickerSoundEnabledCheck.isChecked(),
                "preset": self.clickerSoundPresetCombo.currentData() or "systemAsterisk",
                "customFile": self.clickerCustomSoundPathEdit.text().strip(),
            },
            "triggers": {
                "mode": self.clickerTriggerModeCombo.currentData() or "toggle",
                "toggleHotkey": self.clickerToggleHotkeyCapture.get_hotkey(),
                "holdKey": self.clickerHoldKeyCapture.get_hotkey(),
                "holdMouseButton": self.clickerHoldMouseCombo.currentData() or "middle",
            },
        }

    def _load_profile_into_form(self, profile: Dict[str, Any]) -> None:
        """Populate clicker controls from a profile."""
        self._selected_profile_id = profile.get("id", "default")
        self.clickerProfileNameEdit.setText(profile.get("name", "默认方案"))
        self.clickerEnabledCheck.setChecked(profile.get("enabled", False))

        for i in range(self.clickerButtonCombo.count()):
            if self.clickerButtonCombo.itemData(i) == profile.get("button", "left"):
                self.clickerButtonCombo.setCurrentIndex(i)
                break

        preset = profile.get("preset", self._get_clicker_preset_for_interval(profile.get("intervalMs", 100)))
        for i in range(self.clickerPresetCombo.count()):
            if self.clickerPresetCombo.itemData(i) == preset:
                self.clickerPresetCombo.setCurrentIndex(i)
                break
        self.clickerIntervalSpin.setValue(int(profile.get("intervalMs", 100)))

        triggers = profile.get("triggers", {})
        for i in range(self.clickerTriggerModeCombo.count()):
            if self.clickerTriggerModeCombo.itemData(i) == triggers.get("mode", "toggle"):
                self.clickerTriggerModeCombo.setCurrentIndex(i)
                break
        self.clickerToggleHotkeyCapture.set_hotkey(triggers.get("toggleHotkey", self.settings.DEFAULT_CLICKER_HOTKEY))
        self.clickerHoldKeyCapture.set_hotkey(triggers.get("holdKey", self.settings.DEFAULT_HOLD_KEY))
        for i in range(self.clickerHoldMouseCombo.count()):
            if self.clickerHoldMouseCombo.itemData(i) == triggers.get("holdMouseButton", "middle"):
                self.clickerHoldMouseCombo.setCurrentIndex(i)
                break

        sound = profile.get("sound", {})
        self.clickerSoundEnabledCheck.setChecked(sound.get("enabled", False))
        for i in range(self.clickerSoundPresetCombo.count()):
            if self.clickerSoundPresetCombo.itemData(i) == sound.get("preset", "systemAsterisk"):
                self.clickerSoundPresetCombo.setCurrentIndex(i)
                break
        self.clickerCustomSoundPathEdit.setText(sound.get("customFile", ""))
        self._sync_clicker_interval_controls()
        self._sync_clicker_trigger_controls()
        self._sync_clicker_sound_controls()
        self._profile_dirty = False

    def _populate_clicker_profiles(self) -> None:
        """Refresh the profile combo box from settings."""
        if not hasattr(self, "clickerProfileCombo"):
            return

        current_id = self.settings.data.get("activeClickerProfileId", self._selected_profile_id)
        self.clickerProfileCombo.blockSignals(True)
        self.clickerProfileCombo.clear()
        profiles = self.settings.get_clicker_profiles()
        target_index = 0
        for profile in profiles:
            self.clickerProfileCombo.addItem(profile.get("name", "默认方案"), profile.get("id"))
        for i in range(self.clickerProfileCombo.count()):
            if self.clickerProfileCombo.itemData(i) == current_id:
                target_index = i
                break
        self.clickerProfileCombo.setCurrentIndex(target_index)
        self.clickerProfileCombo.blockSignals(False)
        active = self.settings.set_active_clicker_profile(current_id)
        self._load_profile_into_form(active)

    def _on_clicker_profile_selected(self, _index: int) -> None:
        """Switch the active clicker profile."""
        profile_id = self.clickerProfileCombo.currentData()
        if not profile_id:
            return
        if self._clicker_running:
            self.stop_clicker(show_message=False)
        active = self.settings.set_active_clicker_profile(profile_id)
        self.settings.save()
        self._load_profile_into_form(active)
        self._update_clicker_button()
        self._update_simple_info()
        self._update_tray_meta()
        self._notify(
            self.i18n.t("clicker.profile.switched", "Switched clicker profile: {0}").format(active.get("name", ""))
        )

    def _save_clicker_profile(self) -> None:
        """Save the currently edited clicker profile."""
        profile = self.settings.upsert_clicker_profile(self._current_profile_form_data())
        self._selected_profile_id = profile.get("id", "default")
        self._populate_clicker_profiles()
        self.settings.save()
        self._apply_clicker_timer()
        self._update_clicker_button()
        self._update_simple_info()
        self._update_tray_meta()
        self._profile_dirty = False
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), self.i18n.t("saved", "Settings saved"), self)

    def _create_clicker_profile(self) -> None:
        """Create a new clicker profile based on the current editor state."""
        profile = self.settings.create_clicker_profile(
            self.clickerProfileNameEdit.text().strip(),
            self._current_profile_form_data(),
        )
        self._selected_profile_id = profile.get("id", "default")
        self._populate_clicker_profiles()
        self.settings.save()
        self._notify(
            self.i18n.t("clicker.profile.created", "Created clicker profile: {0}").format(profile.get("name", ""))
        )

    def _delete_clicker_profile(self) -> None:
        """Delete the currently selected clicker profile."""
        active = self._get_active_clicker_profile()
        if self._clicker_running:
            self.stop_clicker(show_message=False)
        new_active = self.settings.delete_clicker_profile(active.get("id", "default"))
        self._selected_profile_id = new_active.get("id", "default")
        self._populate_clicker_profiles()
        self.settings.save()
        self._update_clicker_button()
        self._update_simple_info()
        self._update_tray_meta()
        self._notify(
            self.i18n.t("clicker.profile.deleted", "Deleted clicker profile. Active profile: {0}").format(
                new_active.get("name", "")
            )
        )

    def _browse_clicker_sound_file(self) -> None:
        """Select a custom start-sound file."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.i18n.t("clicker.sound.path.title", "Select Audio File"),
            "",
            self.i18n.t("clicker.sound.path.filter", "Audio Files (*.wav *.mp3 *.ogg *.flac);;All Files (*.*)"),
        )
        if path:
            self.clickerCustomSoundPathEdit.setText(path)
            for i in range(self.clickerSoundPresetCombo.count()):
                if self.clickerSoundPresetCombo.itemData(i) == "custom":
                    self.clickerSoundPresetCombo.setCurrentIndex(i)
                    break
            self._sync_clicker_sound_controls()

    def _preview_clicker_sound(self) -> None:
        """Preview the currently selected clicker start sound."""
        sound_config = {
            "enabled": True,
            "preset": self.clickerSoundPresetCombo.currentData() or "systemAsterisk",
            "customFile": self.clickerCustomSoundPathEdit.text().strip(),
        }
        self._sound_player.play_sound_config(sound_config)

    def _sync_clicker_trigger_controls(self):
        """Only show trigger inputs relevant to the selected trigger mode."""
        mode = self.clickerTriggerModeCombo.currentData() or "toggle"
        toggle_visible = mode == "toggle"
        hold_key_visible = mode == "holdKey"
        hold_mouse_visible = mode == "holdMouseButton"
        self.clickerToggleHotkeyLabel.setVisible(toggle_visible)
        self.clickerToggleHotkeyCapture.setVisible(toggle_visible)
        self.clickerHoldKeyLabel.setVisible(hold_key_visible)
        self.clickerHoldKeyCapture.setVisible(hold_key_visible)
        self.clickerHoldMouseLabel.setVisible(hold_mouse_visible)
        self.clickerHoldMouseCombo.setVisible(hold_mouse_visible)
        self._update_clicker_button()
        self._update_simple_info()

    def _sync_clicker_sound_controls(self):
        """Show the custom sound path only for custom-file mode."""
        preset = self.clickerSoundPresetCombo.currentData() or "systemAsterisk"
        use_custom = preset == "custom"
        enabled = self.clickerSoundEnabledCheck.isChecked()
        self.clickerSoundPresetLabel.setEnabled(enabled)
        self.clickerSoundPresetCombo.setEnabled(enabled)
        self.clickerSoundPreviewBtn.setEnabled(enabled)
        self.clickerCustomSoundPathEdit.setVisible(enabled and use_custom)
        self.clickerCustomSoundBrowseBtn.setVisible(enabled and use_custom)
    
    def _on_apply(self):
        """Apply and save settings."""
        # Save hotkeys
        self.settings.data["hotkeys"]["lock"] = self.lockHotkeyCapture.get_hotkey()
        self.settings.data["hotkeys"]["unlock"] = self.unlockHotkeyCapture.get_hotkey()
        self.settings.data["hotkeys"]["toggle"] = self.toggleHotkeyCapture.get_hotkey()
        self.settings.upsert_clicker_profile(self._current_profile_form_data())
        
        # Save behavior
        self.settings.data["recenter"]["enabled"] = self.recenterCheck.isChecked()
        self.settings.data["recenter"]["intervalMs"] = self.recenterSpin.value()
        
        # Save position
        self.settings.data["position"]["mode"] = self.posCombo.currentData()
        self.settings.data["position"]["customX"] = self.customXSpin.value()
        self.settings.data["position"]["customY"] = self.customYSpin.value()
        
        # Save window specific
        self.settings.data["windowSpecific"]["enabled"] = self.windowSpecificCheck.isChecked()
        # Save list items
        items = [self.targetList.item(i).text() for i in range(self.targetList.count())]
        self.settings.data["windowSpecific"]["targetWindows"] = items
        
        self.settings.data["windowSpecific"]["autoLockOnWindowFocus"] = self.autoLockCheck.isChecked()
        self.settings.data["windowSpecific"]["resumeAfterWindowSwitch"] = self.resumeAfterSwitchCheck.isChecked()
        
        # Save language and theme
        self.settings.data["language"] = self.langCombo.currentData()
        self.settings.data["theme"] = self.themeCombo.currentData()
        
        # Handle startup
        set_startup_enabled(self.startupCheck.isChecked())
        self.settings.data.setdefault("startup", {})
        self.settings.data["startup"]["launchOnBoot"] = self.startupCheck.isChecked()
        
        self.settings.save()

        if not self._get_active_clicker_profile().get("enabled", False):
            self.stop_clicker(show_message=False)
        else:
            self._apply_clicker_timer()
        
        # Re-register hotkeys
        unregister_hotkeys()
        success, errors = register_hotkeys(self.settings.data)
        if not success:
            QtWidgets.QMessageBox.warning(
                self,
                self.i18n.t("hotkey.conflict", "Hotkey Conflict"),
                self.i18n.t("hotkey.register.fail", "Some hotkeys could not be registered:") + 
                "\n" + "\n".join(errors)
            )
        
        # Apply theme and update UI
        self._apply_theme()
        self._update_toggle_button()
        self._update_clicker_button()
        self._update_simple_info()
        self._update_tray_meta()
        self._populate_clicker_profiles()
        
        # Show confirmation
        QtWidgets.QToolTip.showText(
            QtGui.QCursor.pos(),
            self.i18n.t("saved", "Settings saved"),
            self
        )
    
    def _on_mode_changed(self, idx: int):
        """Handle mode tab change."""
        self.stack.setCurrentIndex(idx)
    
    # --- Lock/Unlock Logic ---
    def lock(self, manual: bool = False):
        """Lock the cursor to target position."""
        if self._locked:
            return

        # Enforce window check even for manual lock if specific window locking is enabled
        if not self._should_lock_for_window():
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
            self.locked = True
            self._apply_recenter_timer()
            self._notify(self.i18n.t("locked.message", "Locked to screen center"))
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                self.i18n.t("error", "Error"),
                self.i18n.t("lock.failed", "Failed to lock: {}").format(str(e))
            )

    def unlock(self, manual: bool = False):
        """Unlock the cursor."""
        if not self._locked:
            return

        if manual and self.settings.data.get("windowSpecific", {}).get("autoLockOnWindowFocus", False):
            self._auto_lock_suspended = True
        
        if manual:
            self._force_lock = False
        
        try:
            unclip_cursor()
            self.locked = False
            self._apply_recenter_timer()
            self._notify(self.i18n.t("unlocked.message", "Unlocked"))
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                self.i18n.t("error", "Error"),
                self.i18n.t("unlock.failed", "Failed to unlock: {}").format(str(e))
            )
    
    def toggle_lock(self):
        """Toggle lock state."""
        if self._locked:
            self.unlock(manual=True)
        else:
            self.lock(manual=True)
    
    def _check_match(self, title: str, process: str, targets: list) -> bool:
        """Check if current window matches any target (by title substring or process name)."""
        if not title:
            title = ""
        if not process:
            process = ""
            
        title_lower = title.lower()
        process_lower = process.lower()
        
        for t in targets:
            t_lower = t.lower()
            if not t_lower:
                continue
            # Check 1: Exact process name match
            if t_lower == process_lower:
                return True
            # Check 2: Title substring match
            if t_lower in title_lower:
                return True
        
        return False

    def _should_lock_for_window(self) -> bool:
        """Check if locking should proceed based on window-specific settings."""
        # If specific window locking is enabled, it takes precedence over manual lock
        if self.settings.data["windowSpecific"].get("enabled", False):
            hwnd, title = get_active_window_info()
            targets = self.settings.data["windowSpecific"].get("targetWindows", [])
            
            # Get process name for more robust matching
            proc_name = get_window_process_name(hwnd) if hwnd else ""
            
            match = self._check_match(title, proc_name, targets)
            # print(f"[DEBUG] Lock Check - Title: '{title}' | Proc: '{proc_name}' | Match: {match}")
            return match
            
        # If not enabled, we allow locking (force_lock is irrelevant here as this function 
        # is essentially answering 'Is the current window valid for locking?')
        return True
    
    def _get_target_position(self) -> tuple:
        """Get the target lock position based on settings."""
        # 1. Check for Window-Specific Locking
        if self.settings.data["windowSpecific"].get("enabled", False):
            hwnd, title = get_active_window_info()
            if hwnd:
                proc_name = get_window_process_name(hwnd) or ""
                targets = self.settings.data["windowSpecific"].get("targetWindows", [])
                
                if self._check_match(title, proc_name, targets):
                    center = get_window_center(hwnd)
                    if center:
                        # log_debug(f"Target Position: Window Center {center}")
                        return center

        # 2. Fallback to global positioning settings
        mode = self.settings.data["position"].get("mode", "virtualCenter")
        
        if mode == "primaryCenter":
            return get_primary_screen_center()
        elif mode == "custom":
            return (
                self.settings.data["position"].get("customX", 0),
                self.settings.data["position"].get("customY", 0)
            )
        return get_virtual_screen_center()
    
    def _on_lock_state_changed(self):
        """Called when lock state changes."""
        self._update_status_badge()
        self._update_simple_info()
        self._update_toggle_button()
        self._update_clicker_button()
        self._update_tray_icon()
        self._update_tray_meta()

    def _apply_clicker_timer(self):
        """Start or stop the clicker timer based on state and settings."""
        clicker = self._get_active_clicker_profile()
        if self._clicker_running and clicker.get("enabled", False):
            interval = max(1, int(clicker.get("intervalMs", 100)))
            if self.clickerTimer.interval() != interval or not self.clickerTimer.isActive():
                self.clickerTimer.start(interval)
        else:
            self.clickerTimer.stop()

    def start_clicker(self, show_message: bool = True):
        """Start the auto clicker."""
        profile = self._get_active_clicker_profile()
        if self._clicker_running or not profile.get("enabled", False):
            return

        self._clicker_running = True
        self._apply_clicker_timer()
        self._sound_player.play_for_profile(profile)
        self._update_simple_info()
        self._update_clicker_button()
        self._update_tray_meta()
        if show_message:
            mode_text = self.i18n.t(
                CLICKER_TRIGGER_MODES.get(profile.get("triggers", {}).get("mode", "toggle"), ""),
                profile.get("triggers", {}).get("mode", "toggle"),
            )
            self._notify(
                self.i18n.t("clicker.started.detail", "Auto clicker started: {0} ({1})").format(
                    profile.get("name", ""),
                    mode_text,
                )
            )

    def stop_clicker(self, show_message: bool = True):
        """Stop the auto clicker."""
        if not self._clicker_running:
            return

        self._clicker_running = False
        self._apply_clicker_timer()
        self._update_simple_info()
        self._update_clicker_button()
        self._update_tray_meta()
        if show_message:
            profile = self._get_active_clicker_profile()
            self._notify(
                self.i18n.t("clicker.stopped.detail", "Auto clicker stopped: {0}").format(
                    profile.get("name", "")
                )
            )

    def toggle_clicker(self):
        """Toggle the auto clicker."""
        profile = self._get_active_clicker_profile()
        if profile.get("triggers", {}).get("mode") != "toggle":
            if not self._clicker_running:
                self.start_clicker()
            else:
                self.stop_clicker()
            return
        if self._clicker_running:
            self.stop_clicker()
        else:
            self.start_clicker()

    def _modifier_pressed(self, vk: int) -> bool:
        """Return whether a modifier virtual key is currently pressed."""
        return bool(user32.GetAsyncKeyState(vk) & 0x8000)

    def _hold_hotkey_matches(self, hold_key: Dict[str, Any], key_name: str) -> bool:
        """Check whether the incoming key event matches the configured hold hotkey."""
        if key_name != hold_key.get("key", ""):
            return False

        modifier_map = [
            ("modCtrl", 0x11),
            ("modAlt", 0x12),
            ("modShift", 0x10),
            ("modWin", 0x5B),
        ]
        for flag_name, vk in modifier_map:
            expected = bool(hold_key.get(flag_name, False))
            pressed = self._modifier_pressed(vk)
            if expected != pressed:
                return False
        return True

    def _handle_global_key_event(self, key_name: str, is_pressed: bool) -> None:
        """Handle global key down/up events for hold-to-click triggers."""
        profile = self._get_active_clicker_profile()
        triggers = profile.get("triggers", {})
        if triggers.get("mode") != "holdKey":
            return
        hold_key = triggers.get("holdKey", {})
        if is_pressed and self._hold_hotkey_matches(hold_key, key_name) and not self._hold_trigger_pressed:
            self._hold_trigger_pressed = True
            self.start_clicker(show_message=True)
            return

        watched_keys = {
            hold_key.get("key", ""),
            "Ctrl",
            "Alt",
            "Shift",
            "Win",
        }
        if not is_pressed and self._hold_trigger_pressed and key_name in watched_keys:
            self._hold_trigger_pressed = False
            self.stop_clicker(show_message=True)

    def _handle_global_mouse_event(self, button_name: str, is_pressed: bool) -> None:
        """Handle global mouse down/up events for hold-to-click triggers."""
        profile = self._get_active_clicker_profile()
        triggers = profile.get("triggers", {})
        if triggers.get("mode") != "holdMouseButton":
            return
        if button_name != triggers.get("holdMouseButton", "middle"):
            return
        if is_pressed and not self._hold_trigger_pressed:
            self._hold_trigger_pressed = True
            self.start_clicker(show_message=True)
        elif not is_pressed and self._hold_trigger_pressed:
            self._hold_trigger_pressed = False
            self.stop_clicker(show_message=True)
    
    def _apply_recenter_timer(self):
        """Start or stop the recenter timer based on state and settings."""
        if self._locked and self.settings.data["recenter"].get("enabled", True):
            interval = max(16, self.settings.data["recenter"].get("intervalMs", 250))
            if self.recenterTimer.interval() != interval or not self.recenterTimer.isActive():
                self.recenterTimer.start(interval)
        else:
            self.recenterTimer.stop()
    
    def _on_recenter_tick(self):
        """Periodically recenter cursor."""
        if not self._locked:
            return
        
        if not self._should_lock_for_window():
            self.unlock(manual=False)
            return
        
        cx, cy = self._get_target_position()
        set_cursor_to(cx, cy)
        try:
            clip_cursor_to_point(cx, cy)
        except Exception:
            pass

    def _on_clicker_tick(self):
        """Perform one click while the clicker is running."""
        if not self._clicker_running:
            return

        clicker = self._get_active_clicker_profile()
        if not clicker.get("enabled", False):
            self.stop_clicker(show_message=False)
            return

        click_mouse(clicker.get("button", "left"))
    
    def _check_window_focus(self):
        """Check window focus for auto lock/unlock."""
        ws = self.settings.data.get("windowSpecific", {})
        if not ws.get("enabled") or not ws.get("autoLockOnWindowFocus"):
            return
        
        hwnd, title = get_active_window_info()
        if title is None:
            return
            
        # Get process name for matching
        proc_name = get_window_process_name(hwnd) if hwnd else ""
        
        # Log active window info periodically or on change
        if title != self._last_active_window:
            prev_title = self._last_active_window
            self._last_active_window = title
            targets = ws.get("targetWindows", [])
            
            # Resume logic: matching check
            is_target = self._check_match(title, proc_name, targets)
            
            # We don't have previous process name easily, but resume logic is "was target" -> "now not target".
            # The previous title check is weak if locking by process.
            # Simplified: If we are leaving a state where we SHOULD match.
            # But we can't easily check "was_target" without full history.
            # Workaround: If we are UNLOCKING, we are leaving. 
            
            # Let's trust is_target.
            
            if ws.get("resumeAfterWindowSwitch", False) and not is_target and self._auto_lock_suspended:
                 # If we are suspended (meaning we manually unlocked inside a target), and now we leave target...
                 # We should clear suspended so when we return, it locks.
                 # Wait, 'was_target' check was: "prev_title == target".
                 # If we rely on _auto_lock_suspended being True, it IMPLIES we were in a target window and unlocked it.
                 self._auto_lock_suspended = False
            
            # If currently locked but moved to a non-target window -> Unlock
            if self._locked and not is_target:
                self.unlock(manual=False)
            # If not locked, moved to a target window, and not manually paused -> Lock
            elif not self._locked and is_target and not self._auto_lock_suspended:
                self.lock(manual=False)
            self._update_simple_info()
    
    # --- UI Updates ---
    def _update_status_badge(self):
        """Update the status badge appearance."""
        if self._locked:
            # Locked state - green
            if self._force_lock:
                text = self.i18n.t("status.locked.manual", "LOCKED (Manual)")
            else:
                text = self.i18n.t("status.locked.auto", "LOCKED (Auto)")
            self.statusBadge.setText(text)
            self.statusBadge.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #1e5631, stop:1 #2d7a4a);
                color: #c8facc;
                border: 1px solid #2d7a4a;
                border-radius: 14px;
                font-weight: 600;
                font-size: 16px;
                padding: 4px;
            """)
        else:
            # Unlocked state - check if waiting for auto-lock
            ws = self.settings.data.get("windowSpecific", {})
            is_auto_enabled = ws.get("enabled", False) and ws.get("autoLockOnWindowFocus", False)
            
            if is_auto_enabled and not self._auto_lock_suspended:
                # Waiting for window switch - yellow/orange
                text = self.i18n.t("status.waiting", "WAITING (Auto-lock enabled)")
                self.statusBadge.setText(text)
                self.statusBadge.setStyleSheet("""
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #8a6d3b, stop:1 #c9a961);
                    color: #fff8e1;
                    border: 1px solid #c9a961;
                    border-radius: 14px;
                    font-weight: 600;
                    font-size: 16px;
                    padding: 4px;
                """)
            elif self._auto_lock_suspended:
                # Auto-lock paused - red
                text = self.i18n.t("status.unlocked.suspended", "UNLOCKED (Auto-lock paused)")
                self.statusBadge.setText(text)
                self.statusBadge.setStyleSheet("""
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #5c1e1e, stop:1 #8a2929);
                    color: #ffdede;
                    border: 1px solid #8a2929;
                    border-radius: 14px;
                    font-weight: 600;
                    font-size: 16px;
                    padding: 4px;
                """)
            else:
                # Normal unlocked - red
                text = self.i18n.t("status.unlocked", "UNLOCKED")
                self.statusBadge.setText(text)
                self.statusBadge.setStyleSheet("""
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 #5c1e1e, stop:1 #8a2929);
                    color: #ffdede;
                    border: 1px solid #8a2929;
                    border-radius: 14px;
                    font-weight: 600;
                    font-size: 16px;
                    padding: 4px;
                """)

    def _update_simple_info(self):
        """Update simple mode information cards."""
        if not hasattr(self, "configLabel") or not hasattr(self, "hotkeysLabel"):
            return

        # Get settings
        rec = self.settings.data.get("recenter", {})
        pos = self.settings.data.get("position", {})
        ws = self.settings.data.get("windowSpecific", {})
        hk = self.settings.data.get("hotkeys", {})
        clicker = self._get_active_clicker_profile()

        # Build configuration information
        config_parts = []
        
        # Position
        mode = pos.get("mode", "virtualCenter")
        if mode == "primaryCenter":
            pos_text = self.i18n.t("position.primaryCenter", "Primary screen center")
        elif mode == "custom":
            pos_text = f"{self.i18n.t('position.custom', 'Custom')} ({pos.get('customX', 0)}, {pos.get('customY', 0)})"
        else:
            pos_text = self.i18n.t("position.virtualCenter", "Virtual screen center")
        config_parts.append(f"{self.i18n.t('simple.position', 'Position')}: {pos_text}")
        
        # Recenter
        rec_enabled = bool(rec.get("enabled", True))
        interval = int(rec.get("intervalMs", 250))
        rec_status = self.i18n.t('simple.enabled', 'Enabled') if rec_enabled else self.i18n.t('simple.disabled', 'Disabled')
        rec_text = f"{self.i18n.t('simple.recenter', 'Auto-Recenter')}: {rec_status}"
        if rec_enabled:
            rec_text += f" ({interval}ms)"
        config_parts.append(rec_text)
        
        # Window specific
        ws_enabled = bool(ws.get("enabled", False))
        ws_status = self.i18n.t('simple.enabled', 'Enabled') if ws_enabled else self.i18n.t('simple.disabled', 'Disabled')
        ws_text = f"{self.i18n.t('simple.window', 'Window Lock')}: {ws_status}"
        if ws_enabled:
            targets = ws.get("targetWindows", [])
            auto_focus = bool(ws.get("autoLockOnWindowFocus", False))
            
            if targets:
                if len(targets) == 1:
                    ws_text += f"\n  Target: {targets[0]}"
                else:
                    count_text = self.i18n.t("simple.window.count", "{0} windows").format(len(targets))
                    ws_text += f"\n  Target: {count_text}"
            
            if auto_focus:
                ws_text += f" ({self.i18n.t('window.specific.autoLock', 'Auto')})"
            resume_after = bool(ws.get("resumeAfterWindowSwitch", False)) # Moved this line
            if auto_focus and resume_after: # This block was missing in the provided snippet, re-added for correctness
                ws_text += f"\n  {self.i18n.t('window.specific.resumeAfterSwitch', 'Auto re-lock after window switch')}"
        config_parts.append(ws_text)

        clicker_enabled = bool(clicker.get("enabled", False))
        clicker_status = self.i18n.t('simple.enabled', 'Enabled') if clicker_enabled else self.i18n.t('simple.disabled', 'Disabled')
        clicker_runtime = self.i18n.t('simple.on', 'On') if self._clicker_running else self.i18n.t('simple.off', 'Off')
        button_name = clicker.get("button", "left")
        if button_name == "right":
            button_key = "clicker.button.right"
        elif button_name == "middle":
            button_key = "clicker.button.middle"
        else:
            button_key = "clicker.button.left"
        preset_key = clicker.get("preset", self._get_clicker_preset_for_interval(clicker.get("intervalMs", 100)))
        preset_label_key = f"clicker.preset.{preset_key}" if preset_key in CLICKER_PRESETS else "clicker.preset.custom"
        clicker_text = (
            f"{self.i18n.t('simple.clicker', 'Auto Clicker')}: {clicker_status}"
            f" ({self.i18n.t('clicker.runtime', 'Running')}: {clicker_runtime})"
        )
        if clicker_enabled:
            trigger_mode = clicker.get("triggers", {}).get("mode", "toggle")
            clicker_text += (
                f"\n  {self.i18n.t(button_key, 'Left Click')} | "
                f"{self.i18n.t(preset_label_key, 'Custom')} @ {int(clicker.get('intervalMs', 100))}ms | "
                f"{self.i18n.t(CLICKER_TRIGGER_MODES.get(trigger_mode, ''), trigger_mode)}"
            )
        config_parts.append(clicker_text)
        
        self.configLabel.setText("\n".join(config_parts))
        
        # Build hotkey information
        hk_parts = []
        lock_key = format_hotkey_display(hk.get('lock', {}))
        unlock_key = format_hotkey_display(hk.get('unlock', {}))
        toggle_key = format_hotkey_display(hk.get('toggle', {}))
        
        hk_parts.append(f"{self.i18n.t('hotkey.lock', 'Lock')}: {lock_key}")
        hk_parts.append(f"{self.i18n.t('hotkey.unlock', 'Unlock')}: {unlock_key}")
        hk_parts.append(f"{self.i18n.t('hotkey.toggle', 'Toggle')}: {toggle_key}")
        triggers = clicker.get("triggers", {})
        trigger_mode = triggers.get("mode", "toggle")
        if trigger_mode == "toggle":
            trigger_text = format_hotkey_display(triggers.get("toggleHotkey", {}))
        elif trigger_mode == "holdKey":
            trigger_text = format_hotkey_display(triggers.get("holdKey", {}))
        else:
            trigger_text = self.i18n.t(f"clicker.mouse.{triggers.get('holdMouseButton', 'middle')}", triggers.get("holdMouseButton", "middle"))
        hk_parts.append(f"{self.i18n.t('clicker.trigger.mode', 'Trigger Mode')}: {self.i18n.t(CLICKER_TRIGGER_MODES.get(trigger_mode, ''), trigger_mode)}")
        hk_parts.append(f"{self.i18n.t('clicker.hotkey', 'Auto Clicker Toggle')}: {trigger_text}")
        
        self.hotkeysLabel.setText("\n".join(hk_parts))
    
    def _update_toggle_button(self):
        """Update the toggle button text."""
        hk = self.settings.data["hotkeys"]
        
        if self._locked:
            text = self.i18n.t("btn.unlock", "Unlock")
            keys = f"({format_hotkey_display(hk['unlock'])} / {format_hotkey_display(hk['toggle'])})"
        else:
            text = self.i18n.t("btn.lock", "Lock to center")
            keys = f"({format_hotkey_display(hk['lock'])} / {format_hotkey_display(hk['toggle'])})"

        self.toggleBtn.setText(f"{text} {keys}")

    def _get_clicker_preset_for_interval(self, interval_ms: int) -> str:
        """Resolve the current interval to a preset key when possible."""
        normalized = max(1, int(interval_ms))
        for preset_key, preset_interval in CLICKER_PRESETS.items():
            if preset_interval == normalized:
                return preset_key
        return "custom"

    def _describe_clicker_preset(self, preset_key: str, interval_ms: int) -> str:
        """Return a short descriptive label for the clicker preset."""
        if preset_key == "efficient":
            return self.i18n.t("clicker.preset.desc.efficient", "100 ms per click (10 clicks/sec)")
        if preset_key == "extreme":
            return self.i18n.t("clicker.preset.desc.extreme", "10 ms per click (100 clicks/sec)")
        return self.i18n.t("clicker.preset.desc.custom", "Manually set the click interval")

    def _sync_clicker_interval_controls(self):
        """Show the custom interval editor only for the custom preset."""
        if not hasattr(self, "clickerPresetCombo"):
            return

        preset_key = self.clickerPresetCombo.currentData() or "custom"
        interval_ms = self.clickerIntervalSpin.value() if hasattr(self, "clickerIntervalSpin") else 100
        is_custom = preset_key == "custom"

        if hasattr(self, "clickerIntervalLabel"):
            self.clickerIntervalLabel.setVisible(is_custom)
        if hasattr(self, "clickerIntervalSpin"):
            self.clickerIntervalSpin.setVisible(is_custom)
            self.clickerIntervalSpin.setEnabled(is_custom)
        if hasattr(self, "clickerPresetHint"):
            self.clickerPresetHint.setText(self._describe_clicker_preset(preset_key, interval_ms))

    def _on_clicker_preset_changed(self, _index: int = -1):
        """Apply preset interval values and refresh the UI."""
        preset_key = self.clickerPresetCombo.currentData() or "custom"
        preset_interval = CLICKER_PRESETS.get(preset_key)
        if preset_interval is not None:
            self.clickerIntervalSpin.setValue(preset_interval)
        self._sync_clicker_interval_controls()

    def _update_clicker_button(self):
        """Update the auto clicker button text and enabled state."""
        if not hasattr(self, "clickerBtn"):
            return

        clicker = self._get_active_clicker_profile()
        triggers = clicker.get("triggers", {})
        mode = triggers.get("mode", "toggle")
        if mode == "toggle":
            hotkey = format_hotkey_display(triggers.get("toggleHotkey", {}))
        elif mode == "holdKey":
            hotkey = format_hotkey_display(triggers.get("holdKey", {}))
        else:
            hotkey = self.i18n.t(f"clicker.mouse.{triggers.get('holdMouseButton', 'middle')}", triggers.get("holdMouseButton", "middle"))
        if self._clicker_running:
            text = self.i18n.t("btn.clicker.stop", "Stop Auto Clicker")
        else:
            text = self.i18n.t("btn.clicker.start", "Start Auto Clicker")

        if hotkey and hotkey != "?":
            text = f"{text} ({hotkey})"

        self.clickerBtn.setText(text)
        self.clickerBtn.setEnabled(clicker.get("enabled", False))
    
    # --- Theme ---
    def _apply_theme(self):
        """Apply the current theme."""
        QtWidgets.QApplication.setStyle("Fusion")
        theme = self.settings.data.get("theme", "dark")
        
        if theme == "light":
            palette = self._create_light_palette()
            stylesheet = self._light_stylesheet()
        else:
            palette = self._create_dark_palette()
            stylesheet = self._dark_stylesheet()
        
        QtWidgets.QApplication.setPalette(palette)
        self.setStyleSheet(stylesheet)
    
    def _create_dark_palette(self) -> QtGui.QPalette:
        """Create dark theme palette."""
        p = QtGui.QPalette()
        p.setColor(QtGui.QPalette.Window, QtGui.QColor(28, 28, 30))
        p.setColor(QtGui.QPalette.WindowText, QtGui.QColor(235, 235, 245))
        p.setColor(QtGui.QPalette.Base, QtGui.QColor(44, 44, 46))
        p.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(28, 28, 30))
        p.setColor(QtGui.QPalette.Text, QtGui.QColor(235, 235, 245))
        p.setColor(QtGui.QPalette.Button, QtGui.QColor(44, 44, 46))
        p.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(235, 235, 245))
        p.setColor(QtGui.QPalette.Highlight, QtGui.QColor(10, 132, 255))
        p.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor(142, 142, 147))
        return p
    
    def _create_light_palette(self) -> QtGui.QPalette:
        """Create light theme palette."""
        p = QtGui.QPalette()
        p.setColor(QtGui.QPalette.Window, QtGui.QColor(242, 242, 247))
        p.setColor(QtGui.QPalette.WindowText, QtGui.QColor(20, 20, 25))
        p.setColor(QtGui.QPalette.Base, QtGui.QColor(255, 255, 255))
        p.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(242, 242, 247))
        p.setColor(QtGui.QPalette.Text, QtGui.QColor(20, 20, 25))
        p.setColor(QtGui.QPalette.Button, QtGui.QColor(255, 255, 255))
        p.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(20, 20, 25))
        p.setColor(QtGui.QPalette.Highlight, QtGui.QColor(10, 132, 255))
        p.setColor(QtGui.QPalette.PlaceholderText, QtGui.QColor(142, 142, 147))
        return p
    
    def _dark_stylesheet(self) -> str:
        return """
            QMainWindow { background: #1c1c1e; }
            QWidget { color: #ebebf5; font-size: 14px; }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0a84ff, stop:1 #0671dd);
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                color: white;
                font-weight: 500;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2b95ff, stop:1 #1982ee); 
            }
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0671dd, stop:1 #0558bb); 
            }
            QComboBox, QSpinBox, QLineEdit {
                background: #2c2c2e;
                border: 1px solid #48484a;
                border-radius: 6px;
                padding: 6px;
            }
            QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
                border: 1px solid #0a84ff;
            }
            QCheckBox { spacing: 8px; }
            QScrollArea { border: none; }
        """
    
    def _light_stylesheet(self) -> str:
        return """
            QMainWindow { background: #f2f2f7; }
            QWidget { color: #141419; font-size: 14px; }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0a84ff, stop:1 #0671dd);
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                color: white;
                font-weight: 500;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2b95ff, stop:1 #1982ee); 
            }
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0671dd, stop:1 #0558bb); 
            }
            QComboBox, QSpinBox, QLineEdit {
                background: #ffffff;
                border: 1px solid #d1d1d6;
                border-radius: 6px;
                padding: 6px;
            }
            QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
                border: 1px solid #0a84ff;
            }
            QCheckBox { spacing: 8px; }
            QScrollArea { border: none; }
        """
    
    # --- System Tray ---
    def _create_tray(self):
        """Create system tray icon and menu."""
        self.tray = QtWidgets.QSystemTrayIcon(self._custom_icon or self._make_icon(False), self)
        
        menu = QtWidgets.QMenu()
        
        # State header
        self.stateAction = menu.addAction("")
        self.stateAction.setEnabled(False)
        menu.addSeparator()
        
        # Hotkey info
        self.hkInfoAction = menu.addAction("")
        self.hkInfoAction.setEnabled(False)
        menu.addSeparator()
        
        # Actions
        menu.addAction(self.i18n.t("menu.toggle", "Toggle Lock")).triggered.connect(self.toggle_lock)
        menu.addAction(self.i18n.t("menu.lock", "Lock")).triggered.connect(lambda: self.lock(manual=True))
        menu.addAction(self.i18n.t("menu.unlock", "Unlock")).triggered.connect(lambda: self.unlock(manual=True))
        self.clickerAction = menu.addAction("")
        self.clickerAction.triggered.connect(self.toggle_clicker)
        menu.addSeparator()
        menu.addAction(self.i18n.t("menu.show", "Show Window")).triggered.connect(self._show_from_tray)
        menu.addAction(self.i18n.t("menu.quit", "Quit")).triggered.connect(self._quit)
        
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self._update_tray_meta()
        self.tray.show()
        self._notification_manager = NotificationManager(self.tray)
    
    def _make_icon(self, locked: bool) -> QtGui.QIcon:
        """Create a programmatic icon."""
        size = 128
        pm = QtGui.QPixmap(size, size)
        pm.fill(QtCore.Qt.transparent)
        
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # Background circle
        color = QtGui.QColor(46, 204, 113) if locked else QtGui.QColor(10, 132, 255)
        p.setBrush(color)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(0, 0, size, size)
        
        # Lock body
        pad = 28
        body = QtCore.QRect(pad, pad + 18, size - 2*pad, size - 2*pad - 18)
        p.setBrush(QtGui.QColor(255, 255, 255))
        p.drawRoundedRect(body, 14, 14)
        
        # Shackle
        pen = QtGui.QPen(QtGui.QColor(255, 255, 255))
        pen.setWidth(14)
        p.setPen(pen)
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawArc(size//2 - 30, pad - 6, 60, 48, 0, 180*16)
        
        p.end()
        return QtGui.QIcon(pm)
    
    def _load_external_icon(self) -> Optional[QtGui.QIcon]:
        """Try to load external icon file."""
        candidates = [
            os.path.join(ASSETS_DIR, "app.ico"),
            os.path.join(ASSETS_DIR, "icon.ico"),
            os.path.join(ASSETS_DIR, "app.png"),
            os.path.join(_RUN_DIR, "app.ico"),
        ]
        
        for path in candidates:
            if os.path.exists(path):
                icon = QtGui.QIcon(path)
                if not icon.isNull():
                    return icon
        return None
    
    def _update_tray_icon(self):
        """Update tray icon based on lock state."""
        if self._custom_icon is None:
            self.tray.setIcon(self._make_icon(self._locked))
    
    def _update_tray_meta(self):
        """Update tray menu information."""
        state = self.i18n.t("status.locked", "Locked") if self._locked else self.i18n.t("status.unlocked", "Unlocked")
        clicker_state = self.i18n.t("simple.on", "On") if self._clicker_running else self.i18n.t("simple.off", "Off")
        clicker = self._get_active_clicker_profile()
        self.stateAction.setText(
            f"● {state} | {self.i18n.t('simple.clicker', 'Auto Clicker')}: {clicker_state} | {clicker.get('name', '')}"
        )
        
        hk = self.settings.data["hotkeys"]
        clicker_hotkey = clicker.get("triggers", {}).get("toggleHotkey", {})
        self.hkInfoAction.setText(
            f"{self.i18n.t('hotkey.toggle', 'Toggle')}: {format_hotkey_display(hk['toggle'])} | "
            f"{self.i18n.t('clicker.hotkey', 'Auto Clicker Toggle')}: {format_hotkey_display(clicker_hotkey)}"
        )
        self.clickerAction.setText(
            self.i18n.t("menu.clicker.stop", "Stop Auto Clicker")
            if self._clicker_running else
            self.i18n.t("menu.clicker.start", "Start Auto Clicker")
        )
        self.clickerAction.setEnabled(clicker.get("enabled", False))
    
    def _tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self._show_from_tray()
    
    def _show_from_tray(self):
        """Show window from tray."""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def _quit(self):
        """Quit the application."""
        try:
            self.stop_clicker(show_message=False)
            self._input_listener.stop()
            if self._locked:
                unclip_cursor()
        finally:
            unregister_hotkeys()
            release_single_instance()
            QtWidgets.QApplication.quit()
    
    def _reset_close_action(self):
        """Reset the close action to 'ask'."""
        self.settings.data["closeAction"] = "ask"
        self.settings.save()
        QtWidgets.QMessageBox.information(
            self,
            self.i18n.t("settings.reset", "Settings Reset"),
            self.i18n.t("close.action.reset.done", "Close behavior has been reset to 'Ask every time'.")
        )

    def closeEvent(self, event):
        """Handle window close - minimize to tray or quit."""
        # Shift+Close always quits
        if QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier:
            event.accept()
            self._quit()
            return

        action = self.settings.data.get("closeAction", "ask")
        
        if action == "ask":
            dialog = CloseActionDialog(self, self.i18n)
            if dialog.exec() == QtWidgets.QDialog.Accepted:
                if dialog.action == "minimize":
                    event.ignore()
                    self.hide()
                    self._notify(self.i18n.t("tray.minimized", "Minimized to tray."))
                elif dialog.action == "quit":
                    event.accept()
                    self._quit()
                
                if dialog.dont_ask_again and dialog.action:
                    self.settings.data["closeAction"] = dialog.action
                    self.settings.save()
            else:
                # Cancelled
                event.ignore()
        elif action == "minimize":
            event.ignore()
            self.hide()
        elif action == "quit":
            event.accept()
            self._quit()


def main() -> int:
    """Application entry point."""
    # Check single instance
    if not acquire_single_instance():
        # Try to bring existing window to front
        bring_existing_instance_to_front()
        
        # Show message box
        app = QtWidgets.QApplication(sys.argv)
        QtWidgets.QMessageBox.information(
            None,
            "Mouse Center Lock",
            "Application is already running.\nCheck the system tray."
        )
        return 0
    
    app = QtWidgets.QApplication(sys.argv)
    
    settings = SettingsManager()
    i18n = I18n(settings.data.get("language", "zh-Hans"))
    
    # Register hotkeys
    success, errors = register_hotkeys(settings.data)
    if not success:
        QtWidgets.QMessageBox.warning(
            None,
            i18n.t("error", "Error"),
            i18n.t("hotkey.register.fail", "Some hotkeys could not be registered:") +
            "\n" + "\n".join(errors)
        )
    
    window = MainWindow(settings, i18n)
    window.show()
    
    # Setup hotkey handling
    emitter = HotkeyEmitter()
    event_filter = NativeEventFilter(emitter)
    app.installNativeEventFilter(event_filter)
    
    def on_hotkey(hid: int):
        if hid == HOTKEY_ID_LOCK:
            window.lock(manual=True)
        elif hid == HOTKEY_ID_UNLOCK:
            window.unlock(manual=True)
        elif hid == HOTKEY_ID_TOGGLE:
            window.toggle_lock()
        elif hid == HOTKEY_ID_CLICKER_TOGGLE:
            window.toggle_clicker()
    
    emitter.hotkeyPressed.connect(on_hotkey)
    
    ret = app.exec()
    
    # Cleanup
    try:
        window.stop_clicker(show_message=False)
        window._input_listener.stop()
        if window.locked:
            unclip_cursor()
    finally:
        unregister_hotkeys()
        release_single_instance()
    
    return ret


if __name__ == "__main__":
    sys.exit(main())
