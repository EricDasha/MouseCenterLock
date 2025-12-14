"""
MouseCenterLock GUI Application
A Windows tool to lock the mouse cursor to the screen center.
"""
import sys
import json
import os
import ctypes
from ctypes import wintypes
from typing import Optional, Dict, Any

from PySide6 import QtCore, QtGui, QtWidgets

# Import our modules
from win_api import (
    WM_HOTKEY, MSG,
    HOTKEY_ID_LOCK, HOTKEY_ID_UNLOCK, HOTKEY_ID_TOGGLE,
    acquire_single_instance, release_single_instance, bring_existing_instance_to_front,
    get_virtual_screen_center, get_primary_screen_center,
    set_cursor_to, clip_cursor_to_point, unclip_cursor,
    get_active_window_info, format_hotkey_display,
    register_hotkeys, unregister_hotkeys,
    is_startup_enabled, set_startup_enabled, user32
)
from widgets import HotkeyCapture, ProcessPickerDialog, CloseActionDialog


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

CONFIG_DEFAULT_PATH = os.path.join(APP_DIR, "config.json")
CONFIG_PATH = os.path.join(_RUN_DIR, "config.json")


def load_json(path: str, default: Any) -> Any:
    """Load JSON from file, returning default on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


class SettingsManager:
    """Manages application settings including loading, validation, and saving."""
    
    DEFAULT_HOTKEYS = {
        "lock": {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "L"},
        "unlock": {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "U"},
        "toggle": {"modCtrl": True, "modAlt": True, "modShift": False, "modWin": False, "key": "K"}
    }
    
    def __init__(self):
        # Load user config, falling back to default
        data = load_json(CONFIG_PATH, None)
        if data is None:
            data = load_json(CONFIG_DEFAULT_PATH, {})
        
        self.data: Dict[str, Any] = data if isinstance(data, dict) else {}
        self._set_defaults()
    
    def _set_defaults(self):
        """Ensure all required settings have default values."""
        self.data.setdefault("language", "zh-Hans")
        self.data.setdefault("theme", "dark")
        self.data.setdefault("hotkeys", self.DEFAULT_HOTKEYS.copy())
        
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
        self.data.setdefault("windowSpecific", {
            "enabled": False,
            "targetWindow": "",
            "targetWindowHandle": 0,
            "autoLockOnWindowFocus": False
        })
        self.data.setdefault("startup", {"launchOnBoot": False})
        self.data.setdefault("closeAction", "ask")  # ask, minimize, quit
    
    def save(self) -> bool:
        """Save settings to file. Returns True if successful."""
        try:
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
        return False, 0


class MainWindow(QtWidgets.QMainWindow):
    """Main application window."""
    
    def __init__(self, settings: SettingsManager, i18n: I18n):
        super().__init__()
        self.settings = settings
        self.i18n = i18n
        
        self._locked = False
        self._auto_lock_suspended = False
        self._force_lock = False
        self._last_active_window = ""
        self._custom_icon: Optional[QtGui.QIcon] = None
        
        self._setup_window()
        self._setup_timers()
        self._build_ui()
        self._apply_theme()
        self._create_tray()
    
    @property
    def locked(self) -> bool:
        return self._locked
    
    @locked.setter
    def locked(self, value: bool):
        self._locked = value
        self._on_lock_state_changed()
    
    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle(self.i18n.t("app.title", "Mouse Center Lock"))
        self.setMinimumSize(450, 500)
        self.resize(550, 620)
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
        
        window_layout = QtWidgets.QHBoxLayout()
        self.targetWindowEdit = QtWidgets.QLineEdit()
        self.targetWindowEdit.setPlaceholderText(self.i18n.t("window.specific.placeholder", "Target window title"))
        self.targetWindowEdit.setText(self.settings.data["windowSpecific"].get("targetWindow", ""))
        window_layout.addWidget(self.targetWindowEdit)
        
        self.pickProcessBtn = QtWidgets.QPushButton(self.i18n.t("window.specific.pick", "Pick"))
        self.pickProcessBtn.clicked.connect(self._pick_process)
        window_layout.addWidget(self.pickProcessBtn)
        layout.addLayout(window_layout)
        
        self.autoLockCheck = QtWidgets.QCheckBox(
            self.i18n.t("window.specific.autoLock", "Auto lock/unlock on window switch")
        )
        self.autoLockCheck.setChecked(
            self.settings.data["windowSpecific"].get("autoLockOnWindowFocus", False)
        )
        layout.addWidget(self.autoLockCheck)
        
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
                self.targetWindowEdit.setText(selected)
    
    def _on_apply(self):
        """Apply and save settings."""
        # Save hotkeys
        self.settings.data["hotkeys"]["lock"] = self.lockHotkeyCapture.get_hotkey()
        self.settings.data["hotkeys"]["unlock"] = self.unlockHotkeyCapture.get_hotkey()
        self.settings.data["hotkeys"]["toggle"] = self.toggleHotkeyCapture.get_hotkey()
        
        # Save behavior
        self.settings.data["recenter"]["enabled"] = self.recenterCheck.isChecked()
        self.settings.data["recenter"]["intervalMs"] = self.recenterSpin.value()
        
        # Save position
        self.settings.data["position"]["mode"] = self.posCombo.currentData()
        self.settings.data["position"]["customX"] = self.customXSpin.value()
        self.settings.data["position"]["customY"] = self.customYSpin.value()
        
        # Save window specific
        self.settings.data["windowSpecific"]["enabled"] = self.windowSpecificCheck.isChecked()
        self.settings.data["windowSpecific"]["targetWindow"] = self.targetWindowEdit.text()
        self.settings.data["windowSpecific"]["autoLockOnWindowFocus"] = self.autoLockCheck.isChecked()
        
        # Save language and theme
        self.settings.data["language"] = self.langCombo.currentData()
        self.settings.data["theme"] = self.themeCombo.currentData()
        
        # Handle startup
        set_startup_enabled(self.startupCheck.isChecked())
        self.settings.data.setdefault("startup", {})
        self.settings.data["startup"]["launchOnBoot"] = self.startupCheck.isChecked()
        
        self.settings.save()
        
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
        self._update_simple_info()
        self._update_tray_meta()
        
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

        if manual:
            self._auto_lock_suspended = False
            self._force_lock = True
        else:
            self._force_lock = False
            if not self._should_lock_for_window():
                return
        
        try:
            cx, cy = self._get_target_position()
            set_cursor_to(cx, cy)
            clip_cursor_to_point(cx, cy)
            self.locked = True
            self._apply_recenter_timer()
            
            self.tray.showMessage(
                self.i18n.t("app.title", "Mouse Center Lock"),
                self.i18n.t("locked.message", "Locked to screen center"),
                QtWidgets.QSystemTrayIcon.Information, 1500
            )
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
            
            self.tray.showMessage(
                self.i18n.t("app.title", "Mouse Center Lock"),
                self.i18n.t("unlocked.message", "Unlocked"),
                QtWidgets.QSystemTrayIcon.Information, 1500
            )
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
    
    def _should_lock_for_window(self) -> bool:
        """Check if locking should proceed based on window-specific settings."""
        # If specific window locking is enabled, it takes precedence over manual lock
        if self.settings.data["windowSpecific"].get("enabled", False):
            hwnd, title = get_active_window_info()
            target = self.settings.data["windowSpecific"].get("targetWindow", "")
            match = (title == target)
            print(f"[DEBUG] Lock Check - Title: '{title}' | Target: '{target}' | Match: {match}")
            return match
            
        # If not enabled, we allow locking (force_lock is irrelevant here as this function 
        # is essentially answering 'Is the current window valid for locking?')
        return True
    
    def _get_target_position(self) -> tuple:
        """Get the target lock position based on settings."""
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
        self._update_tray_icon()
        self._update_tray_meta()
    
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
    
    def _check_window_focus(self):
        """Check window focus for auto lock/unlock."""
        ws = self.settings.data.get("windowSpecific", {})
        if not ws.get("enabled") or not ws.get("autoLockOnWindowFocus"):
            return
        
        _, title = get_active_window_info()
        if title is None:
            return
        
        if title != self._last_active_window:
            self._last_active_window = title
            target = ws.get("targetWindow", "")
            
            if self._locked and title != target:
                self.unlock(manual=False)
            elif not self._locked and title == target and not self._auto_lock_suspended:
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
            target = ws.get("targetWindow", "")
            auto_focus = bool(ws.get("autoLockOnWindowFocus", False))
            if target:
                ws_text += f"\n  Target: {target}"
            if auto_focus:
                ws_text += f" ({self.i18n.t('window.specific.autoLock', 'Auto')})"
        config_parts.append(ws_text)
        
        self.configLabel.setText("\n".join(config_parts))
        
        # Build hotkey information
        hk_parts = []
        lock_key = format_hotkey_display(hk.get('lock', {}))
        unlock_key = format_hotkey_display(hk.get('unlock', {}))
        toggle_key = format_hotkey_display(hk.get('toggle', {}))
        
        hk_parts.append(f"{self.i18n.t('hotkey.lock', 'Lock')}: {lock_key}")
        hk_parts.append(f"{self.i18n.t('hotkey.unlock', 'Unlock')}: {unlock_key}")
        hk_parts.append(f"{self.i18n.t('hotkey.toggle', 'Toggle')}: {toggle_key}")
        
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
        menu.addSeparator()
        menu.addAction(self.i18n.t("menu.show", "Show Window")).triggered.connect(self._show_from_tray)
        menu.addAction(self.i18n.t("menu.quit", "Quit")).triggered.connect(self._quit)
        
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self._update_tray_meta()
        self.tray.show()
    
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
        self.stateAction.setText(f"● {state}")
        
        hk = self.settings.data["hotkeys"]
        self.hkInfoAction.setText(f"Toggle: {format_hotkey_display(hk['toggle'])}")
    
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
                    self.tray.showMessage(
                        self.i18n.t("app.title", "Mouse Center Lock"),
                        self.i18n.t("tray.minimized", "Minimized to tray."),
                        QtWidgets.QSystemTrayIcon.Information, 2000
                    )
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
    
    emitter.hotkeyPressed.connect(on_hotkey)
    
    ret = app.exec()
    
    # Cleanup
    try:
        if window.locked:
            unclip_cursor()
    finally:
        unregister_hotkeys()
        release_single_instance()
    
    return ret


if __name__ == "__main__":
    sys.exit(main())
