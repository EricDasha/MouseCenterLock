import ctypes
import sys
import json
import os
from ctypes import wintypes

from PySide6 import QtCore, QtGui, QtWidgets


# --- Windows constants and helpers ---
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WM_HOTKEY = 0x0312

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002

HOTKEY_ID_LOCK = 1
HOTKEY_ID_UNLOCK = 2
HOTKEY_ID_TOGGLE = 4

# --- Configuration & i18n ---
if getattr(sys, 'frozen', False):
    _BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    _RUN_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _RUN_DIR = _BASE_DIR

APP_DIR = _BASE_DIR
I18N_DIR = os.path.join(APP_DIR, "i18n")
ASSETS_DIR = os.path.join(APP_DIR, "assets")

# Config: prefer writable alongside exe/run dir; fall back to packaged default
CONFIG_DEFAULT_PATH = os.path.join(APP_DIR, "config.json")
CONFIG_PATH = os.path.join(_RUN_DIR, "config.json")


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


class SettingsManager:
    """Manages application settings including loading, default values, and saving."""
    
    def __init__(self):
        # Load user config if present; otherwise from packaged default
        data = load_json(CONFIG_PATH, None)
        if data is None:
            data = load_json(CONFIG_DEFAULT_PATH, {})
        
        # Ensure data is a dictionary
        if not isinstance(data, dict):
            data = {}
            
        self.data = data
        
        # Set default values for all settings
        self._set_default_settings()

    def _set_default_settings(self):
        """Set default values for all settings."""
        self.data.setdefault("language", "zh-Hans")
        self.data.setdefault("theme", "dark")
        self.data.setdefault("hotkeys", {
            "lock": {"modCtrl": True, "modAlt": True, "modShift": False, "key": "L"},
            "unlock": {"modCtrl": True, "modAlt": True, "modShift": False, "key": "U"},
            "toggle": {"modCtrl": True, "modAlt": True, "modShift": False, "key": "K"}
        })
        self.data.setdefault("recenter", {"enabled": True, "intervalMs": 250})
        self.data.setdefault("position", {"mode": "virtualCenter", "customX": 0, "customY": 0})
        # Add window-specific locking settings
        self.data.setdefault("windowSpecific", {
            "enabled": False,
            "targetWindow": "",
            "targetWindowHandle": 0,
            "autoLockOnWindowFocus": False
        })

    def save(self):
        """Save current settings to the configuration file."""
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


class I18n:
    def __init__(self, lang_code: str):
        self.lang_code = lang_code
        self.strings = load_json(os.path.join(I18N_DIR, f"{lang_code}.json"), {})

    def t(self, key: str, fallback: str = "") -> str:
        if key in self.strings:
            return self.strings[key]
        return fallback if fallback else key


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def get_virtual_screen_center():
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79

    x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return x + w // 2, y + h // 2


def set_cursor_to(x, y):
    user32.SetCursorPos(int(x), int(y))


def clip_cursor_to_point(x, y):
    rect = RECT(x, y, x, y)
    if not user32.ClipCursor(ctypes.byref(rect)):
        raise ctypes.WinError()


def unclip_cursor():
    if not user32.ClipCursor(None):
        raise ctypes.WinError()


# Add function to get active window information
def get_active_window_info():
    """Get the handle and title of the currently active window."""
    hwnd = user32.GetForegroundWindow()
    if hwnd == 0:
        return None, None
    
    # Get window title
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return hwnd, ""
    
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return hwnd, buffer.value


# --- Native hotkey bridge ---
class HotkeyEmitter(QtCore.QObject):
    hotkeyPressed = QtCore.Signal(int)


class NativeEventFilter(QtCore.QAbstractNativeEventFilter):
    def __init__(self, emitter: 'HotkeyEmitter'):
        super().__init__()
        self._emitter = emitter

    def nativeEventFilter(self, eventType, message):
        if eventType == "windows_generic_MSG":
            msg = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
            if msg.message == WM_HOTKEY:
                self._emitter.hotkeyPressed.emit(msg.wParam)
        return False, 0


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


def build_mod_flags(cfg):
    mods = 0
    if cfg.get("modCtrl"):
        mods |= MOD_CONTROL
    if cfg.get("modAlt"):
        mods |= MOD_ALT
    if cfg.get("modShift"):
        mods |= 0x0004
    return mods


def key_to_vk(key_str: str):
    s = (key_str or "").upper()
    if len(s) == 1 and 'A' <= s <= 'Z':
        return ord(s)
    if len(s) == 1 and '0' <= s <= '9':
        return ord(s)
    if s.startswith('F') and s[1:].isdigit():
        n = int(s[1:])
        if 1 <= n <= 24:
            return 0x70 + (n - 1)
    return None


def register_hotkeys(settings):
    hk = settings.data["hotkeys"]
    specs = [
        (HOTKEY_ID_LOCK, hk["lock"]),
        (HOTKEY_ID_UNLOCK, hk["unlock"]),
        (HOTKEY_ID_TOGGLE, hk["toggle"]),
    ]
    for id_, spec in specs:
        mods = build_mod_flags(spec)
        vk = key_to_vk(spec.get("key", ""))
        if not vk:
            raise ValueError("Unsupported hotkey key: " + str(spec.get("key")))
        if not user32.RegisterHotKey(None, id_, mods, vk):
            raise ctypes.WinError()


def unregister_hotkeys():
    user32.UnregisterHotKey(None, HOTKEY_ID_LOCK)
    user32.UnregisterHotKey(None, HOTKEY_ID_UNLOCK)
    user32.UnregisterHotKey(None, HOTKEY_ID_TOGGLE)


# --- Main Window ---
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, settings: 'SettingsManager', i18n: 'I18n'):
        super().__init__()
        self.settings = settings
        self.i18n = i18n
        self.setWindowTitle(self.i18n.t("app.title", "Mouse Center Lock"))
        self.setMinimumSize(400, 300)  # 最小窗口大小
        self.resize(620, 650)  # 默认窗口大小设置为620×650
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self.locked = False
        self.lastActiveWindowTitle = ""
        self.recenterTimer = QtCore.QTimer(self)
        self.recenterTimer.timeout.connect(self._on_recenter_tick)
        
        # Timer for checking window focus changes
        self.windowFocusTimer = QtCore.QTimer(self)
        self.windowFocusTimer.timeout.connect(self._check_window_focus)
        self.windowFocusTimer.start(500)  # Check every 500ms

        # Set window icon (prefer external, fallback to built-in) and apply globally
        win_icon = self._load_external_icon()
        if win_icon is None:
            win_icon = self._make_tray_icon(False)
        QtWidgets.QApplication.setWindowIcon(win_icon)
        self.setWindowIcon(win_icon)

        # Central UI with Simple/Advanced
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        self.stack = QtWidgets.QStackedWidget()
        self.simplePage = self._build_simple_page()
        self.advancedPage = self._build_advanced_page()
        self.stack.addWidget(self.simplePage)
        self.stack.addWidget(self.advancedPage)

        self.modeTabs = QtWidgets.QTabBar()
        self.modeTabs.addTab(self.i18n.t("mode.simple", "Simple"))
        self.modeTabs.addTab(self.i18n.t("mode.advanced", "Advanced"))
        self.modeTabs.currentChanged.connect(self._on_mode_changed)

        v = QtWidgets.QVBoxLayout(central)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(16)
        v.addWidget(self.modeTabs)
        v.addWidget(self.stack)

        self._apply_theme()

        # Tray
        self.tray = self._create_tray()
        self.tray.show()

    # --- Styling ---
    def _apply_theme(self):
        QtWidgets.QApplication.setStyle("Fusion")
        
        # Get theme setting, default to dark
        theme = self.settings.data.get("theme", "dark")
        
        if theme == "light":
            # Light theme colors
            base = QtGui.QColor(242, 242, 247)
            alt = QtGui.QColor(255, 255, 255)
            text = QtGui.QColor(20, 20, 25)
            hint = QtGui.QColor(142, 142, 147)
            accent = QtGui.QColor(10, 132, 255)

            palette = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.Window, base)
            palette.setColor(QtGui.QPalette.Base, alt)
            palette.setColor(QtGui.QPalette.AlternateBase, base)
            palette.setColor(QtGui.QPalette.Button, alt)
            palette.setColor(QtGui.QPalette.ButtonText, text)
            palette.setColor(QtGui.QPalette.Text, text)
            palette.setColor(QtGui.QPalette.WindowText, text)
            palette.setColor(QtGui.QPalette.ToolTipBase, alt)
            palette.setColor(QtGui.QPalette.ToolTipText, text)
            palette.setColor(QtGui.QPalette.Highlight, accent)
            palette.setColor(QtGui.QPalette.BrightText, text)
            palette.setColor(QtGui.QPalette.PlaceholderText, hint)
            QtWidgets.QApplication.setPalette(palette)

            self.setStyleSheet(
                """
                QMainWindow { background: #f2f2f7; }
                QWidget { color: #141419; font-size: 14px; }
                QPushButton { background: #0a84ff; border: none; border-radius: 10px; padding: 8px 14px; color: white; }
                QPushButton:hover { background: #2b95ff; }
                QPushButton:pressed { background: #0671dd; }
                QLabel { font-size: 13px; }
                """
            )
        else:
            # Dark theme colors
            base = QtGui.QColor(28, 28, 30)
            alt = QtGui.QColor(44, 44, 46)
            text = QtGui.QColor(235, 235, 245)
            hint = QtGui.QColor(142, 142, 147)
            accent = QtGui.QColor(10, 132, 255)

            palette = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.Window, base)
            palette.setColor(QtGui.QPalette.Base, alt)
            palette.setColor(QtGui.QPalette.AlternateBase, base)
            palette.setColor(QtGui.QPalette.Button, alt)
            palette.setColor(QtGui.QPalette.ButtonText, text)
            palette.setColor(QtGui.QPalette.Text, text)
            palette.setColor(QtGui.QPalette.WindowText, text)
            palette.setColor(QtGui.QPalette.ToolTipBase, alt)
            palette.setColor(QtGui.QPalette.ToolTipText, text)
            palette.setColor(QtGui.QPalette.Highlight, accent)
            palette.setColor(QtGui.QPalette.BrightText, text)
            palette.setColor(QtGui.QPalette.PlaceholderText, hint)
            QtWidgets.QApplication.setPalette(palette)

            self.setStyleSheet(
                """
                QMainWindow { background: #1c1c1e; }
                QWidget { color: #ebebf5; font-size: 14px; }
                QPushButton { background: #0a84ff; border: none; border-radius: 10px; padding: 8px 14px; }
                QPushButton:hover { background: #2b95ff; }
                QPushButton:pressed { background: #0671dd; }
                QLabel { font-size: 13px; }
                """
            )

    def _badge_style(self, locked):
        if locked:
            bg = "#1e5631"
            fg = "#c8facc"
            text = "已锁定"
        else:
            bg = "#5c1e1e"
            fg = "#ffdede"
            text = "未锁定"
        return f"background:{bg}; color:{fg}; border-radius:10px; font-weight:600; line-height:42px;" if False else f"background:{bg}; color:{fg}; border-radius:10px; font-weight:600;"

    # --- Tray ---
    def _create_tray(self):
        self._customIcon = self._load_external_icon()
        tray = QtWidgets.QSystemTrayIcon(self._customIcon or self._make_tray_icon(False), self)
        self.trayMenu = QtWidgets.QMenu()

        self.stateHeader = self.trayMenu.addAction(self.i18n.t("menu.state", "State"))
        self.stateHeader.setEnabled(False)
        self.stateAction = self.trayMenu.addAction("")
        self.stateAction.setEnabled(False)

        self.trayMenu.addSeparator()
        self.trayMenu.addAction(self.i18n.t("menu.hotkeys", "Hotkeys")).setEnabled(False)
        self.hkLockAction = self.trayMenu.addAction("")
        self.hkLockAction.setEnabled(False)
        self.hkUnlockAction = self.trayMenu.addAction("")
        self.hkUnlockAction.setEnabled(False)
        self.hkToggleAction = self.trayMenu.addAction("")
        self.hkToggleAction.setEnabled(False)

        self.trayMenu.addSeparator()
        act_toggle = self.trayMenu.addAction(self.i18n.t("menu.toggle", "Toggle Lock"))
        act_toggle.triggered.connect(self.toggle_lock)
        act_lock = self.trayMenu.addAction(self.i18n.t("menu.lock", "Lock"))
        act_lock.triggered.connect(self.lock)
        act_unlock = self.trayMenu.addAction(self.i18n.t("menu.unlock", "Unlock"))
        act_unlock.triggered.connect(self.unlock)

        self.trayMenu.addSeparator()
        act_show = self.trayMenu.addAction(self.i18n.t("menu.show", "Show Window"))
        act_show.triggered.connect(self._show_from_tray)
        act_quit = self.trayMenu.addAction(self.i18n.t("menu.quit", "Quit"))
        act_quit.triggered.connect(self._quit)

        tray.setContextMenu(self.trayMenu)
        tray.activated.connect(self._tray_activated)
        self._update_tray_meta()
        return tray

    def _make_tray_icon(self, locked):
        size = 128
        pm = QtGui.QPixmap(size, size)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        # background circle
        bg = QtGui.QColor(10, 132, 255) if not locked else QtGui.QColor(46, 204, 113)
        p.setBrush(bg)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(0, 0, size, size)
        # lock glyph
        pad = 28
        body_rect = QtCore.QRect(pad, pad + 18, size - 2 * pad, size - 2 * pad - 18)
        p.setBrush(QtGui.QColor(255, 255, 255))
        p.drawRoundedRect(body_rect, 14, 14)
        # shackle
        pen = QtGui.QPen(QtGui.QColor(255, 255, 255))
        pen.setWidth(14)
        p.setPen(pen)
        p.setBrush(QtCore.Qt.NoBrush)
        center_x = size // 2
        p.drawArc(center_x - 30, pad - 6, 60, 48, 0 * 16, 180 * 16)
        p.end()
        return QtGui.QIcon(pm)

    def _load_external_icon(self):
        # Try multiple locations: assets folder, run dir, and packaged location
        candidates = [
            os.path.join(ASSETS_DIR, "app.ico"),
            os.path.join(ASSETS_DIR, "icon.ico"),
            os.path.join(ASSETS_DIR, "app.png"),
            os.path.join(ASSETS_DIR, "icon.png"),
            os.path.join(_RUN_DIR, "app.ico"),
            os.path.join(_RUN_DIR, "icon.ico"),
            os.path.join(_RUN_DIR, "assets", "app.ico"),
            os.path.join(_RUN_DIR, "assets", "icon.ico"),
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    icon = QtGui.QIcon(path)
                    if not icon.isNull():
                        return icon
                except Exception:
                    continue
        return None

    def _should_perform_window_specific_locking(self):
        """
        Check if window-specific locking is enabled and if the current window matches the target.
        Returns True if locking should proceed, False otherwise.
        """
        window_specific_enabled = self.settings.data.get("windowSpecific", {}).get("enabled", False)
        if not window_specific_enabled:
            # If window-specific locking is not enabled, proceed with locking
            return True
            
        # Get the active window
        hwnd, title = get_active_window_info()
        target_window = self.settings.data.get("windowSpecific", {}).get("targetWindow", "")
        
        # Only proceed with locking if the active window matches the target window
        return title == target_window

    # --- Lock logic ---
    def lock(self):
        # Check if we should perform locking based on window-specific settings
        if not self._should_perform_window_specific_locking():
            return
        
        if self.locked:
            return
        try:
            cx, cy = self._resolve_target_position()
            set_cursor_to(cx, cy)
            clip_cursor_to_point(cx, cy)
            self.locked = True
            self.statusBadge.setText(self.i18n.t("status.locked", "Locked"))
            self.statusBadge.setStyleSheet(self._badge_style(True))
            self._update_toggle_button()
            if self._customIcon is None:
                self.tray.setIcon(self._make_tray_icon(True))
            self.tray.showMessage(
                self.i18n.t("app.title", "Mouse Center Lock"), 
                self.i18n.t("locked.message", "Locked to screen center"), 
                QtWidgets.QSystemTrayIcon.Information, 1500
            )
            self._apply_recenter_timer()
            self._update_tray_meta()
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, 
                self.i18n.t("error", "Error"), 
                self.i18n.t("lock.failed", "Failed to lock: {}").format(str(e))
            )

    def unlock(self):
        if not self.locked:
            return
        try:
            unclip_cursor()
            self.locked = False
            self.statusBadge.setText(self.i18n.t("status.unlocked", "Unlocked"))
            self.statusBadge.setStyleSheet(self._badge_style(False))
            self._update_toggle_button()
            if self._customIcon is None:
                self.tray.setIcon(self._make_tray_icon(False))
            self.tray.showMessage(
                self.i18n.t("app.title", "Mouse Center Lock"), 
                self.i18n.t("unlocked.message", "Unlocked from screen center"), 
                QtWidgets.QSystemTrayIcon.Information, 1500
            )
            self._apply_recenter_timer()
            self._update_tray_meta()
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, 
                self.i18n.t("error", "Error"), 
                self.i18n.t("unlock.failed", "Failed to unlock: {}").format(str(e))
            )

    def toggle_lock(self):
        if self.locked:
            self.unlock()
        else:
            self.lock()

    # --- Tray interactions ---
    def _tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self._show_from_tray()

    def _show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit(self):
        try:
            if self.locked:
                unclip_cursor()
        finally:
            unregister_hotkeys()
            QtWidgets.QApplication.quit()

    def closeEvent(self, event):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        # Shift+Close = truly quit, otherwise minimize to tray
        if modifiers & QtCore.Qt.ShiftModifier:
            event.accept()
            self._quit()
        else:
            event.ignore()
            self.hide()
            self.tray.showMessage(
                self.i18n.t("app.title", "Mouse Center Lock"),
                self.i18n.t("tray.minimized", "Minimized to tray. Right-click tray icon to quit."),
                QtWidgets.QSystemTrayIcon.Information, 2000
            )

    # --- Simple/Advanced builders and helpers ---
    def _build_simple_page(self):
        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(16)

        self.statusBadge = QtWidgets.QLabel()
        self.statusBadge.setAlignment(QtCore.Qt.AlignCenter)
        self.statusBadge.setFixedHeight(42)
        self.statusBadge.setStyleSheet(self._badge_style(False))
        self.statusBadge.setText(self.i18n.t("status.unlocked", "Unlocked"))

        self.toggleBtn = QtWidgets.QPushButton()
        self.toggleBtn.setCursor(QtCore.Qt.PointingHandCursor)
        self.toggleBtn.setFixedHeight(44)
        self.toggleBtn.clicked.connect(self.toggle_lock)
        self._update_toggle_button()

        hint = QtWidgets.QLabel("")
        hint.setAlignment(QtCore.Qt.AlignCenter)
        hint.setStyleSheet("color: palette(mid);")

        v.addWidget(self.statusBadge)
        v.addStretch(1)
        v.addWidget(self.toggleBtn)
        v.addWidget(hint)
        return page

    def _build_advanced_page(self):
        page = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(page)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        row = 0

        hotkeysLabel = QtWidgets.QLabel("" + "")
        hotkeysLabel.setStyleSheet("font-weight:600;")
        grid.addWidget(hotkeysLabel, row, 0, 1, 4)
        row += 1

        def make_hotkey_row(title_text, spec_key):
            title = QtWidgets.QLabel(title_text)
            modCtrl = QtWidgets.QCheckBox("Ctrl")
            modAlt = QtWidgets.QCheckBox("Alt")
            modShift = QtWidgets.QCheckBox("Shift")
            keyCombo = QtWidgets.QComboBox()
            keyCombo.setEditable(True)
            items = [f"F{i}" for i in range(1, 25)] + [chr(c) for c in range(ord('A'), ord('Z')+1)] + [str(i) for i in range(0,10)]
            keyCombo.addItems(items)
            spec = self.settings.data["hotkeys"][spec_key]
            modCtrl.setChecked(bool(spec.get("modCtrl")))
            modAlt.setChecked(bool(spec.get("modAlt")))
            modShift.setChecked(bool(spec.get("modShift")))
            keyCombo.setCurrentText(str(spec.get("key", "")))
            return title, modCtrl, modAlt, modShift, keyCombo

        t1, c1, a1, s1, k1 = make_hotkey_row("" + "", "lock")
        t2, c2, a2, s2, k2 = make_hotkey_row("" + "", "unlock")
        t3, c3, a3, s3, k3 = make_hotkey_row("" + "", "toggle")

        grid.addWidget(t1, row, 0)
        grid.addWidget(c1, row, 1)
        grid.addWidget(a1, row, 2)
        grid.addWidget(s1, row, 3)
        grid.addWidget(k1, row, 4)
        row += 1

        grid.addWidget(t2, row, 0)
        grid.addWidget(c2, row, 1)
        grid.addWidget(a2, row, 2)
        grid.addWidget(s2, row, 3)
        grid.addWidget(k2, row, 4)
        row += 1

        grid.addWidget(t3, row, 0)
        grid.addWidget(c3, row, 1)
        grid.addWidget(a3, row, 2)
        grid.addWidget(s3, row, 3)
        grid.addWidget(k3, row, 4)
        row += 2

        behaviorLabel = QtWidgets.QLabel("" + "")
        behaviorLabel.setStyleSheet("font-weight:600;")
        grid.addWidget(behaviorLabel, row, 0, 1, 4)
        row += 1

        recenterEnabled = QtWidgets.QCheckBox("")
        recenterEnabled.setChecked(bool(self.settings.data["recenter"].get("enabled", True)))
        grid.addWidget(recenterEnabled, row, 0, 1, 2)

        recenterLabel = QtWidgets.QLabel("")
        recenterSpin = QtWidgets.QSpinBox()
        recenterSpin.setRange(16, 5000)
        recenterSpin.setSingleStep(16)
        recenterSpin.setValue(int(self.settings.data["recenter"].get("intervalMs", 250)))
        grid.addWidget(recenterLabel, row, 2)
        grid.addWidget(recenterSpin, row, 3)
        row += 1

        # Add window-specific locking controls
        windowSpecificEnabled = QtWidgets.QCheckBox("")
        windowSpecificEnabled.setChecked(bool(self.settings.data["windowSpecific"].get("enabled", False)))
        grid.addWidget(windowSpecificEnabled, row, 0, 1, 2)
        row += 1

        windowSpecificLabel = QtWidgets.QLabel("")
        windowSpecificCombo = QtWidgets.QComboBox()
        windowSpecificCombo.setEditable(True)
        # Populate with currently active window as default option
        # We'll populate this when the dialog is actually shown, not when it's created
        windowSpecificCombo.setCurrentText(self.settings.data["windowSpecific"].get("targetWindow", ""))
        grid.addWidget(windowSpecificLabel, row, 0)
        grid.addWidget(windowSpecificCombo, row, 1, 1, 3)
        
        # Add refresh button to update window list
        refreshWindowsBtn = QtWidgets.QPushButton("")
        grid.addWidget(refreshWindowsBtn, row, 4)
        row += 1

        # Add process picker button similar to Cheat Engine
        pickProcessBtn = QtWidgets.QPushButton("")
        grid.addWidget(pickProcessBtn, row, 4)
        row += 1
        
        # Add auto-lock checkbox for window-specific locking
        autoLockWindowCheckbox = QtWidgets.QCheckBox("")
        autoLockWindowCheckbox.setChecked(bool(self.settings.data["windowSpecific"].get("autoLockOnWindowFocus", False)))
        grid.addWidget(autoLockWindowCheckbox, row, 0, 1, 2)
        row += 1

        posLabel = QtWidgets.QLabel("")
        posCombo = QtWidgets.QComboBox()
        posCombo.addItem("", "virtualCenter")
        posCombo.addItem("", "primaryCenter")
        posCombo.addItem("", "custom")
        posCombo.setCurrentIndex(["virtualCenter","primaryCenter","custom"].index(self.settings.data["position"].get("mode","virtualCenter")))
        grid.addWidget(posLabel, row, 0)
        grid.addWidget(posCombo, row, 1)

        xLabel = QtWidgets.QLabel("X")
        xSpin = QtWidgets.QSpinBox()
        xSpin.setRange(-10000, 10000)
        xSpin.setValue(int(self.settings.data["position"].get("customX", 0)))
        yLabel = QtWidgets.QLabel("Y")
        ySpin = QtWidgets.QSpinBox()
        ySpin.setRange(-10000, 10000)
        ySpin.setValue(int(self.settings.data["position"].get("customY", 0)))
        grid.addWidget(xLabel, row, 2)
        grid.addWidget(xSpin, row, 3)
        row += 1
        grid.addWidget(yLabel, row, 2)
        grid.addWidget(ySpin, row, 3)
        row += 1

        langLabel = QtWidgets.QLabel("")
        langCombo = QtWidgets.QComboBox()
        langCombo.addItem("English", "en")
        langCombo.addItem("简体中文", "zh-Hans")
        langCombo.addItem("繁體中文", "zh-Hant")
        langCombo.addItem("日本語", "ja")
        langCombo.addItem("한국어", "ko")
        current_lang = self.settings.data.get("language", "zh-Hans")
        langs = [langCombo.itemData(i) for i in range(langCombo.count())]
        if current_lang in langs:
            langCombo.setCurrentIndex(langs.index(current_lang))
        grid.addWidget(langLabel, row, 0)
        grid.addWidget(langCombo, row, 1)
        row += 1
        
        # Add theme selection
        themeLabel = QtWidgets.QLabel("")
        themeCombo = QtWidgets.QComboBox()
        themeCombo.addItem("Dark", "dark")
        themeCombo.addItem("Light", "light")
        current_theme = self.settings.data.get("theme", "dark")
        themes = [themeCombo.itemData(i) for i in range(themeCombo.count())]
        if current_theme in themes:
            themeCombo.setCurrentIndex(themes.index(current_theme))
        grid.addWidget(themeLabel, row, 0)
        grid.addWidget(themeCombo, row, 1)
        row += 1

        applyBtn = QtWidgets.QPushButton("")
        applyBtn.setFixedHeight(36)
        grid.addWidget(applyBtn, row, 0, 1, 2)

        # i18n texts
        hotkeysLabel.setText(self.i18n.t("section.hotkeys", "Hotkeys"))
        t1.setText(self.i18n.t("hotkey.lock", "Lock hotkey"))
        t2.setText(self.i18n.t("hotkey.unlock", "Unlock hotkey"))
        t3.setText(self.i18n.t("hotkey.toggle", "Toggle hotkey"))
        behaviorLabel.setText(self.i18n.t("section.behavior", "Behavior"))
        recenterEnabled.setText(self.i18n.t("recenter.enabled", "Enable recentering"))
        recenterLabel.setText(self.i18n.t("recenter.interval", "Recenter interval (ms)"))
        windowSpecificEnabled.setText(self.i18n.t("window.specific.enabled", "Enable window-specific locking"))
        windowSpecificLabel.setText(self.i18n.t("window.specific.title", "Target window"))
        refreshWindowsBtn.setText(self.i18n.t("window.specific.refresh", "Refresh"))
        pickProcessBtn.setText(self.i18n.t("window.specific.pick", "Pick Process"))
        autoLockWindowCheckbox.setText(self.i18n.t("window.specific.autoLock", "Auto lock/unlock on window switch"))
        posLabel.setText(self.i18n.t("position.title", "Target position"))
        posCombo.setItemText(0, self.i18n.t("position.virtualCenter", "Virtual screen center"))
        posCombo.setItemText(1, self.i18n.t("position.primaryCenter", "Primary screen center"))
        posCombo.setItemText(2, self.i18n.t("position.custom", "Custom"))
        langLabel.setText(self.i18n.t("language.title", "Language"))
        themeLabel.setText(self.i18n.t("theme.title", "Theme"))
        applyBtn.setText(self.i18n.t("apply", "Apply"))

        def refresh_windows_list():
            """Refresh the list of available windows."""
            # Clear current items
            windowSpecificCombo.clear()
            
            # Add currently active window
            hwnd, title = get_active_window_info()
            if title:
                windowSpecificCombo.addItem(title, hwnd)
                
            # Set current value
            current_text = self.settings.data["windowSpecific"].get("targetWindow", "")
            windowSpecificCombo.setCurrentText(current_text)

        def pick_process():
            """Open process picker dialog similar to Cheat Engine."""
            dialog = ProcessPickerDialog(self)
            if dialog.exec() == QtWidgets.QDialog.Accepted:
                selected_process = dialog.get_selected_process()
                if selected_process:
                    windowSpecificCombo.setCurrentText(selected_process)

        def on_apply():
            hk = self.settings.data["hotkeys"]
            hk["lock"] = {"modCtrl": c1.isChecked(), "modAlt": a1.isChecked(), "modShift": s1.isChecked(), "key": k1.currentText().strip()}
            hk["unlock"] = {"modCtrl": c2.isChecked(), "modAlt": a2.isChecked(), "modShift": s2.isChecked(), "key": k2.currentText().strip()}
            hk["toggle"] = {"modCtrl": c3.isChecked(), "modAlt": a3.isChecked(), "modShift": s3.isChecked(), "key": k3.currentText().strip()}

            self.settings.data["recenter"]["enabled"] = recenterEnabled.isChecked()
            self.settings.data["recenter"]["intervalMs"] = int(recenterSpin.value())
            
            # Save window-specific settings
            self.settings.data["windowSpecific"]["enabled"] = windowSpecificEnabled.isChecked()
            self.settings.data["windowSpecific"]["targetWindow"] = windowSpecificCombo.currentText()
            # Save handle data if item has userData (handle)
            current_index = windowSpecificCombo.currentIndex()
            if current_index >= 0 and windowSpecificCombo.itemData(current_index) is not None:
                self.settings.data["windowSpecific"]["targetWindowHandle"] = windowSpecificCombo.itemData(current_index)
            
            # Add auto-lock setting
            self.settings.data["windowSpecific"]["autoLockOnWindowFocus"] = autoLockWindowCheckbox.isChecked()
            
            self.settings.data["position"]["mode"] = posCombo.currentData()
            self.settings.data["position"]["customX"] = int(xSpin.value())
            self.settings.data["position"]["customY"] = int(ySpin.value())
            self.settings.data["language"] = langCombo.currentData()
            self.settings.data["theme"] = themeCombo.currentData()

            self.settings.save()

            try:
                unregister_hotkeys()
                register_hotkeys(self.settings)
            except Exception:
                QtWidgets.QMessageBox.critical(self, self.i18n.t("error", "Error"), self.i18n.t("hotkey.register.fail", "Failed to register hotkeys"))

            self._update_toggle_button()
            self._update_tray_meta()
            self._apply_theme()  # Apply theme changes
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), self.i18n.t("saved", "Saved"), page)

        # Connect refresh button
        refreshWindowsBtn.clicked.connect(refresh_windows_list)
        
        # Connect process picker button
        pickProcessBtn.clicked.connect(pick_process)
        
        applyBtn.clicked.connect(on_apply)

        return page

    def _on_mode_changed(self, idx):
        self.stack.setCurrentIndex(idx)

    # --- Behavior helpers ---
    def _resolve_target_position(self):
        mode = self.settings.data["position"].get("mode", "virtualCenter")
        if mode == "primaryCenter":
            SM_CXSCREEN = 0
            SM_CYSCREEN = 1
            w = user32.GetSystemMetrics(SM_CXSCREEN)
            h = user32.GetSystemMetrics(SM_CYSCREEN)
            return w // 2, h // 2
        if mode == "custom":
            return int(self.settings.data["position"].get("customX", 0)), int(self.settings.data["position"].get("customY", 0))
        return get_virtual_screen_center()

    def _apply_recenter_timer(self):
        if self.locked and self.settings.data["recenter"].get("enabled", True):
            interval = max(16, int(self.settings.data["recenter"].get("intervalMs", 250)))
            if self.recenterTimer.interval() != interval or not self.recenterTimer.isActive():
                self.recenterTimer.start(interval)
        else:
            self.recenterTimer.stop()

    def _on_recenter_tick(self):
        if not self.locked:
            return
            
        # Check if we should still keep the mouse locked based on window-specific settings
        if not self._should_perform_window_specific_locking():
            self.unlock()
            return
                
        cx, cy = self._resolve_target_position()
        set_cursor_to(cx, cy)
        try:
            clip_cursor_to_point(cx, cy)
        except Exception:
            pass

    def _check_window_focus(self):
        """Check if window focus has changed and handle auto-locking if enabled."""
        # Check if window-specific locking is enabled
        window_specific_enabled = self.settings.data.get("windowSpecific", {}).get("enabled", False)
        auto_lock_enabled = self.settings.data.get("windowSpecific", {}).get("autoLockOnWindowFocus", False)
        
        if not window_specific_enabled or not auto_lock_enabled:
            return
            
        # Get current active window
        hwnd, title = get_active_window_info()
        
        if title is None:
            return
            
        # Check if the active window has changed
        if title != self.lastActiveWindowTitle:
            self.lastActiveWindowTitle = title
            
            # Get target window from settings
            target_window = self.settings.data.get("windowSpecific", {}).get("targetWindow", "")
            
            # If we were locked and the window changed, unlock
            if self.locked and title != target_window:
                self.unlock()
            # If we weren't locked and switched to target window, lock
            elif not self.locked and title == target_window:
                self.lock()

    def _should_perform_window_specific_locking(self):
        """
        Check if window-specific locking is enabled and if the current window matches the target.
        Returns True if locking should proceed, False otherwise.
        """
        window_specific_enabled = self.settings.data.get("windowSpecific", {}).get("enabled", False)
        if not window_specific_enabled:
            # If window-specific locking is not enabled, proceed with locking
            return True
            
        # Get the active window
        hwnd, title = get_active_window_info()
        target_window = self.settings.data.get("windowSpecific", {}).get("targetWindow", "")
        
        # Only proceed with locking if the active window matches the target window
        return title == target_window

    def _update_toggle_button(self):
        hk = self.settings.data["hotkeys"]
        def fmt(spec):
            mods = []
            if spec.get("modCtrl"): mods.append("Ctrl")
            if spec.get("modAlt"): mods.append("Alt")
            if spec.get("modShift"): mods.append("Shift")
            return "+".join(mods + [spec.get("key", "?")])
        if hasattr(self, 'toggleBtn'):
            if self.locked:
                self.toggleBtn.setText(f"{self.i18n.t('btn.unlock','Unlock')} ({fmt(hk['unlock'])} / {fmt(hk['toggle'])})")
            else:
                self.toggleBtn.setText(f"{self.i18n.t('btn.lock','Lock to center')} ({fmt(hk['lock'])} / {fmt(hk['toggle'])})")

    def _update_tray_meta(self):
        if hasattr(self, 'stateAction'):
            self.stateAction.setText(self.i18n.t("status.locked","Locked") if self.locked else self.i18n.t("status.unlocked","Unlocked"))
        if hasattr(self, 'hkLockAction'):
            hk = self.settings.data["hotkeys"]
            def fmt(spec):
                mods = []
                if spec.get("modCtrl"): mods.append("Ctrl")
                if spec.get("modAlt"): mods.append("Alt")
                if spec.get("modShift"): mods.append("Shift")
                return "+".join(mods + [spec.get("key", "?")])
            self.hkLockAction.setText(f"{self.i18n.t('hotkey.lock','Lock hotkey')}: {fmt(hk['lock'])}")
            self.hkUnlockAction.setText(f"{self.i18n.t('hotkey.unlock','Unlock hotkey')}: {fmt(hk['unlock'])}")
            self.hkToggleAction.setText(f"{self.i18n.t('hotkey.toggle','Toggle hotkey')}: {fmt(hk['toggle'])}")


# Add Process Picker Dialog similar to Cheat Engine
class ProcessPickerDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Process")
        self.setGeometry(100, 100, 400, 300)
        self.selected_process = None
        
        layout = QtWidgets.QVBoxLayout()
        
        # Add label
        label = QtWidgets.QLabel("Select a process to lock the mouse to:")
        layout.addWidget(label)
        
        # Add list widget for processes
        self.processList = QtWidgets.QListWidget()
        self.processList.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.processList)
        
        # Add buttons
        buttonLayout = QtWidgets.QHBoxLayout()
        refreshBtn = QtWidgets.QPushButton("Refresh")
        refreshBtn.clicked.connect(self.refresh_processes)
        okBtn = QtWidgets.QPushButton("OK")
        okBtn.clicked.connect(self.accept)
        cancelBtn = QtWidgets.QPushButton("Cancel")
        cancelBtn.clicked.connect(self.reject)
        
        buttonLayout.addWidget(refreshBtn)
        buttonLayout.addStretch()
        buttonLayout.addWidget(okBtn)
        buttonLayout.addWidget(cancelBtn)
        
        layout.addLayout(buttonLayout)
        self.setLayout(layout)
        
        # Load processes
        self.refresh_processes()

    def refresh_processes(self):
        """Refresh the list of running processes."""
        self.processList.clear()
        
        # Get list of running processes
        processes = self._get_running_processes()
        for proc_name, proc_title in processes:
            item = QtWidgets.QListWidgetItem(f"{proc_title} ({proc_name})")
            item.setData(QtCore.Qt.UserRole, proc_title)
            self.processList.addItem(item)

    def _get_running_processes(self):
        """Get list of running processes with their window titles."""
        processes = []
        
        # Use EnumWindows to enumerate all top-level windows
        def enum_windows_proc(hwnd, lParam):
            # Check if window is visible
            if user32.IsWindowVisible(hwnd):
                # Get window title
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buffer, length + 1)
                    title = buffer.value
                    
                    # Get process ID
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    
                    # Get process name
                    try:
                        PROCESS_QUERY_INFORMATION = 0x0400
                        PROCESS_VM_READ = 0x0010
                        handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
                        if handle:
                            filename_buffer = ctypes.create_unicode_buffer(260)
                            kernel32.QueryFullProcessImageNameW(handle, 0, filename_buffer, ctypes.byref(wintypes.DWORD(260)))
                            kernel32.CloseHandle(handle)
                            
                            # Extract process name from full path
                            proc_name = os.path.basename(filename_buffer.value)
                            processes.append((proc_name, title))
                    except Exception:
                        # Fallback if we can't get process name
                        processes.append(("unknown.exe", title))
            return True
        
        # Define enum windows callback type
        enum_windows_proc_t = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        callback = enum_windows_proc_t(enum_windows_proc)
        
        # Enumerate windows
        user32.EnumWindows(callback, 0)
        
        # Sort by title
        processes.sort(key=lambda x: x[1].lower())
        return processes

    def get_selected_process(self):
        """Return the selected process title."""
        current_item = self.processList.currentItem()
        if current_item:
            return current_item.data(QtCore.Qt.UserRole)
        return None

    def accept(self):
        """Handle OK button or double-click."""
        self.selected_process = self.get_selected_process()
        if self.selected_process:
            super().accept()


def main():
    app = QtWidgets.QApplication(sys.argv)

    settings = SettingsManager()
    i18n = I18n(settings.data.get("language", "zh-Hans"))

    try:
        register_hotkeys(settings)
    except Exception:
        QtWidgets.QMessageBox.critical(None, i18n.t("error","Error"), i18n.t("hotkey.register.fail","Failed to register hotkeys"))

    window = MainWindow(settings, i18n)
    window.show()

    emitter = HotkeyEmitter()
    nef = NativeEventFilter(emitter)
    app.installNativeEventFilter(nef)

    emitter.hotkeyPressed.connect(lambda hid: (
        window.lock() if hid == HOTKEY_ID_LOCK else
        window.unlock() if hid == HOTKEY_ID_UNLOCK else
        window.toggle_lock() if hid == HOTKEY_ID_TOGGLE else None
    ))

    ret = app.exec()
    try:
        if window.locked:
            unclip_cursor()
    finally:
        unregister_hotkeys()
    return ret


if __name__ == "__main__":
    sys.exit(main())


