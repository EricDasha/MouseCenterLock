import ctypes
import sys
import json
import os
from ctypes import wintypes

from PySide6 import QtCore, QtGui, QtWidgets
import keyboard


# --- Windows constants and helpers ---
user32 = ctypes.windll.user32

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
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


class SettingsManager:
    def __init__(self):
        # Load user config if present; otherwise from packaged default
        self.data = load_json(CONFIG_PATH, None)
        if self.data is None:
            self.data = load_json(CONFIG_DEFAULT_PATH, {})
        self.data.setdefault("language", "zh-Hans")
        self.data.setdefault("theme", "dark")  # "dark" or "light"
        self.data.setdefault("closeBehavior", None)  # None = ask first time, "quit" or "tray"
        self.data.setdefault("hotkeys", {
            "lock": {"modCtrl": True, "modAlt": True, "modShift": False, "key": "L"},
            "unlock": {"modCtrl": True, "modAlt": True, "modShift": False, "key": "U"},
            "toggle": {"modCtrl": True, "modAlt": True, "modShift": False, "key": "K"}
        })
        self.data.setdefault("recenter", {"enabled": True, "intervalMs": 250})
        self.data.setdefault("position", {"mode": "virtualCenter", "customX": 0, "customY": 0})

    def save(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


class I18n:
    def __init__(self, lang_code: str):
        self.lang_code = lang_code
        # 尝试多个路径加载语言文件
        lang_paths = [
            os.path.join(I18N_DIR, f"{lang_code}.json"),  # 主要路径
            os.path.join(_RUN_DIR, "i18n", f"{lang_code}.json"),  # 运行目录
        ]
        
        self.strings = {}
        for path in lang_paths:
            self.strings = load_json(path, {})
            if self.strings:
                break
        
        # 如果还是失败，尝试默认语言
        if not self.strings:
            default_paths = [
                os.path.join(I18N_DIR, "zh-Hans.json"),
                os.path.join(_RUN_DIR, "i18n", "zh-Hans.json"),
            ]
            for path in default_paths:
                self.strings = load_json(path, {})
                if self.strings:
                    break
        
        # 如果所有路径都失败，使用空字典（会使用 fallback）
        if not self.strings:
            self.strings = {}

    def t(self, key: str, fallback: str = None) -> str:
        if key in self.strings:
            return self.strings[key]
        return fallback if fallback is not None else key


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


# --- Hotkey management using keyboard library ---
_hotkey_strings = {}  # Store hotkey strings for removal


def build_hotkey_string(cfg):
    """Build keyboard library hotkey string from config."""
    mods = []
    if cfg.get("modCtrl"):
        mods.append("ctrl")
    if cfg.get("modAlt"):
        mods.append("alt")
    if cfg.get("modShift"):
        mods.append("shift")
    
    key = cfg.get("key", "").lower()
    if key.startswith('f') and key[1:].isdigit():
        # F keys: f1, f2, etc.
        return "+".join(mods + [key])
    elif len(key) == 1 and key.isalnum():
        # Single character keys
        return "+".join(mods + [key])
    else:
        raise ValueError(f"Unsupported hotkey key: {key}")


def register_hotkeys(settings, callbacks):
    """Register hotkeys using keyboard library.
    
    Args:
        settings: SettingsManager instance
        callbacks: dict with keys 'lock', 'unlock', 'toggle', each is a callable
    """
    global _hotkey_strings
    hk = settings.data["hotkeys"]
    
    # Clear existing hotkeys
    unregister_hotkeys()
    
    # Create thread-safe wrappers that execute in Qt main thread
    def make_thread_safe(callback):
        def wrapper():
            QtCore.QTimer.singleShot(0, callback)
        return wrapper
    
    try:
        # Register lock hotkey
        lock_str = build_hotkey_string(hk["lock"])
        keyboard.add_hotkey(lock_str, make_thread_safe(callbacks["lock"]), suppress=False)
        _hotkey_strings["lock"] = lock_str
        
        # Register unlock hotkey
        unlock_str = build_hotkey_string(hk["unlock"])
        keyboard.add_hotkey(unlock_str, make_thread_safe(callbacks["unlock"]), suppress=False)
        _hotkey_strings["unlock"] = unlock_str
        
        # Register toggle hotkey
        toggle_str = build_hotkey_string(hk["toggle"])
        keyboard.add_hotkey(toggle_str, make_thread_safe(callbacks["toggle"]), suppress=False)
        _hotkey_strings["toggle"] = toggle_str
        
    except Exception as e:
        unregister_hotkeys()
        raise e


def unregister_hotkeys():
    """Unregister all hotkeys."""
    global _hotkey_strings
    # Use clear_all_hotkeys for simplicity, or remove individually
    try:
        keyboard.clear_all_hotkeys()
    except Exception:
        # Fallback: try to remove each hotkey individually
        for key, hotkey_str in _hotkey_strings.items():
            try:
                keyboard.remove_hotkey(hotkey_str)
            except Exception:
                pass
    _hotkey_strings.clear()


# --- Hotkey Key Capture Widget ---
class HotkeyKeyEdit(QtWidgets.QLineEdit):
    """自定义按键捕获控件，用于捕获单个按键"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("点击后按任意键...")
        self._capturing = False
        
    def mousePressEvent(self, event):
        """点击时开始捕获按键"""
        if event.button() == QtCore.Qt.LeftButton:
            self._start_capture()
        super().mousePressEvent(event)
    
    def _start_capture(self):
        """开始捕获按键"""
        self._capturing = True
        self.setText("")
        self.setPlaceholderText("按任意键...")
        # 使用主题适配的样式
        palette = QtWidgets.QApplication.palette()
        bg_color = palette.color(QtGui.QPalette.Base).name()
        self.setStyleSheet(f"background-color: {bg_color}; border: 2px solid #0a84ff;")
        self.setFocus()
    
    def _stop_capture(self):
        """停止捕获按键"""
        self._capturing = False
        self.setStyleSheet("")
        if not self.text():
            self.setPlaceholderText("点击后按任意键...")
    
    def keyPressEvent(self, event):
        """捕获按键"""
        if not self._capturing:
            super().keyPressEvent(event)
            return
        
        # 忽略修饰键
        if event.key() in (QtCore.Qt.Key_Control, QtCore.Qt.Key_Alt, QtCore.Qt.Key_Shift,
                          QtCore.Qt.Key_Meta, QtCore.Qt.Key_AltGr):
            return
        
        key_text = self._key_to_string(event.key())
        if key_text:
            self.setText(key_text)
            self._stop_capture()
        else:
            # 无效按键，显示提示
            palette = QtWidgets.QApplication.palette()
            bg_color = palette.color(QtGui.QPalette.Base).name()
            self.setStyleSheet(f"background-color: {bg_color}; border: 2px solid #ff3b30;")
            QtCore.QTimer.singleShot(500, self._stop_capture)
    
    def _key_to_string(self, key):
        """将 Qt 按键码转换为字符串"""
        # 字母键 A-Z
        if QtCore.Qt.Key_A <= key <= QtCore.Qt.Key_Z:
            return chr(key)
        
        # 数字键 0-9
        if QtCore.Qt.Key_0 <= key <= QtCore.Qt.Key_9:
            return chr(key)
        
        # 功能键 F1-F24
        if QtCore.Qt.Key_F1 <= key <= QtCore.Qt.Key_F24:
            num = key - QtCore.Qt.Key_F1 + 1
            return f"F{num}"
        
        return None
    
    def focusOutEvent(self, event):
        """失去焦点时停止捕获"""
        if self._capturing:
            self._stop_capture()
        super().focusOutEvent(event)


# --- Main Window ---
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, settings: 'SettingsManager', i18n: 'I18n'):
        super().__init__()
        self.settings = settings
        self.i18n = i18n
        self.setWindowTitle(self.i18n.t("app.title", "Mouse Center Lock"))
        self.setMinimumSize(600, 450)  # 设置最小窗口大小，确保文字清晰
        self.resize(680, 520)  # 设置合适的初始窗口大小
        # 确保关闭按钮可用，只移除帮助按钮
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self.locked = False
        self.recenterTimer = QtCore.QTimer(self)
        self.recenterTimer.timeout.connect(self._on_recenter_tick)

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
    def _apply_theme(self, theme=None):
        if theme is None:
            theme = self.settings.data.get("theme", "dark")
        
        QtWidgets.QApplication.setStyle("Fusion")
        palette = QtGui.QPalette()

        if theme == "light":
            # Light theme
            base = QtGui.QColor(255, 255, 255)
            alt = QtGui.QColor(242, 242, 247)
            text = QtGui.QColor(0, 0, 0)
            hint = QtGui.QColor(142, 142, 147)
            accent = QtGui.QColor(0, 122, 255)
            button_bg = QtGui.QColor(0, 122, 255)
            button_hover = QtGui.QColor(0, 132, 255)
            button_pressed = QtGui.QColor(0, 96, 214)
        else:
            # Dark theme (default)
            base = QtGui.QColor(28, 28, 30)
            alt = QtGui.QColor(44, 44, 46)
            text = QtGui.QColor(235, 235, 245)
            hint = QtGui.QColor(142, 142, 147)
            accent = QtGui.QColor(10, 132, 255)
            button_bg = QtGui.QColor(10, 132, 255)
            button_hover = QtGui.QColor(43, 149, 255)
            button_pressed = QtGui.QColor(6, 113, 221)

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

        bg_color = base.name()
        text_color = text.name()
        self.setStyleSheet(
            f"""
            QMainWindow {{ background: {bg_color}; }}
            QWidget {{ color: {text_color}; font-size: 14px; }}
            QPushButton {{ 
                background: {button_bg.name()}; 
                color: white;
                border: none; 
                border-radius: 10px; 
                padding: 8px 14px; 
            }}
            QPushButton:hover {{ background: {button_hover.name()}; }}
            QPushButton:pressed {{ background: {button_pressed.name()}; }}
            QLabel {{ font-size: 13px; }}
            QCheckBox {{ font-size: 13px; }}
            QComboBox {{ font-size: 13px; padding: 4px; }}
            QSpinBox {{ font-size: 13px; padding: 4px; }}
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

    # --- Lock logic ---
    def lock(self):
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
            self.tray.showMessage("Mouse Center Lock", "已锁定到屏幕中心", QtWidgets.QSystemTrayIcon.Information, 1500)
            self._apply_recenter_timer()
            self._update_tray_meta()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "锁定失败", str(e))

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
            self.tray.showMessage("Mouse Center Lock", "已解除锁定", QtWidgets.QSystemTrayIcon.Information, 1500)
            self._apply_recenter_timer()
            self._update_tray_meta()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "解锁失败", str(e))

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
            # Stop keyboard listener thread
            try:
                keyboard.unhook_all()
            except Exception:
                pass
            QtWidgets.QApplication.quit()

    def closeEvent(self, event):
        close_behavior = self.settings.data.get("closeBehavior")
        
        # First time: ask user
        if close_behavior is None:
            msg = QtWidgets.QMessageBox(self)
            msg.setWindowTitle(self.i18n.t("close.dialog.title", "Close Behavior"))
            msg.setText(self.i18n.t("close.dialog.message", "How do you want to close the window?"))
            msg.setInformativeText(self.i18n.t("close.dialog.info", "You can change this later in Settings > Advanced."))
            
            btn_quit = msg.addButton(self.i18n.t("close.quit", "Quit"), QtWidgets.QMessageBox.ButtonRole.AcceptRole)
            btn_tray = msg.addButton(self.i18n.t("close.minimize", "Minimize to tray"), QtWidgets.QMessageBox.ButtonRole.RejectRole)
            msg.setDefaultButton(btn_tray)
            
            msg.exec()
            
            if msg.clickedButton() == btn_quit:
                close_behavior = "quit"
            else:
                close_behavior = "tray"
            
            self.settings.data["closeBehavior"] = close_behavior
            self.settings.save()
        
        # Shift+Close = override and quit
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers & QtCore.Qt.ShiftModifier:
            event.accept()
            self._quit()
            return
        
        # Apply configured behavior
        if close_behavior == "quit":
            event.accept()
            self._quit()
        else:  # "tray" or default
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
            
            # 使用按键捕获控件，点击后按任意键即可记录
            keyEdit = HotkeyKeyEdit()
            keyEdit.setPlaceholderText(self.i18n.t("hotkey.capture.hint", "点击后按任意键"))
            keyEdit.setToolTip(self.i18n.t("hotkey.capture.tooltip", "点击此框，然后按下要设置的按键（字母、数字或功能键）"))
            keyEdit.setMinimumWidth(80)
            
            spec = self.settings.data["hotkeys"][spec_key]
            modCtrl.setChecked(bool(spec.get("modCtrl")))
            modAlt.setChecked(bool(spec.get("modAlt")))
            modShift.setChecked(bool(spec.get("modShift")))
            
            # 设置当前按键值
            current_key = str(spec.get("key", "")).upper()
            if current_key:
                keyEdit.setText(current_key)
                keyEdit.setPlaceholderText("")
            
            return title, modCtrl, modAlt, modShift, keyEdit

        t1, c1, a1, s1, k1 = make_hotkey_row(self.i18n.t("hotkey.lock", "Lock hotkey"), "lock")
        t2, c2, a2, s2, k2 = make_hotkey_row(self.i18n.t("hotkey.unlock", "Unlock hotkey"), "unlock")
        t3, c3, a3, s3, k3 = make_hotkey_row(self.i18n.t("hotkey.toggle", "Toggle hotkey"), "toggle")

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

        behaviorLabel = QtWidgets.QLabel(self.i18n.t("section.behavior", "Behavior"))
        behaviorLabel.setStyleSheet("font-weight:600;")
        grid.addWidget(behaviorLabel, row, 0, 1, 4)
        row += 1

        recenterEnabled = QtWidgets.QCheckBox(self.i18n.t("recenter.enabled", "Enable recentering"))
        recenterEnabled.setChecked(bool(self.settings.data["recenter"].get("enabled", True)))
        grid.addWidget(recenterEnabled, row, 0, 1, 2)

        recenterLabel = QtWidgets.QLabel(self.i18n.t("recenter.interval", "Recenter interval (ms)"))
        recenterSpin = QtWidgets.QSpinBox()
        recenterSpin.setRange(16, 5000)
        recenterSpin.setSingleStep(16)
        recenterSpin.setValue(int(self.settings.data["recenter"].get("intervalMs", 250)))
        grid.addWidget(recenterLabel, row, 2)
        grid.addWidget(recenterSpin, row, 3)
        row += 1

        posLabel = QtWidgets.QLabel(self.i18n.t("position.title", "Target position"))
        posCombo = QtWidgets.QComboBox()
        posCombo.addItem(self.i18n.t("position.virtualCenter", "Virtual screen center"), "virtualCenter")
        posCombo.addItem(self.i18n.t("position.primaryCenter", "Primary screen center"), "primaryCenter")
        posCombo.addItem(self.i18n.t("position.custom", "Custom"), "custom")
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

        langLabel = QtWidgets.QLabel(self.i18n.t("language.title", "Language"))
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

        appearanceLabel = QtWidgets.QLabel(self.i18n.t("section.appearance", "Appearance"))
        appearanceLabel.setStyleSheet("font-weight:600;")
        grid.addWidget(appearanceLabel, row, 0, 1, 4)
        row += 1

        themeLabel = QtWidgets.QLabel(self.i18n.t("theme.title", "Theme"))
        themeCombo = QtWidgets.QComboBox()
        themeCombo.addItem(self.i18n.t("theme.dark", "Dark"), "dark")
        themeCombo.addItem(self.i18n.t("theme.light", "Light"), "light")
        current_theme = self.settings.data.get("theme", "dark")
        themes = [themeCombo.itemData(i) for i in range(themeCombo.count())]
        if current_theme in themes:
            themeCombo.setCurrentIndex(themes.index(current_theme))
        grid.addWidget(themeLabel, row, 0)
        grid.addWidget(themeCombo, row, 1)
        row += 1

        closeBehaviorLabel = QtWidgets.QLabel(self.i18n.t("close.title", "Close behavior"))
        closeBehaviorCombo = QtWidgets.QComboBox()
        closeBehaviorCombo.addItem(self.i18n.t("close.minimize", "Minimize to tray"), "tray")
        closeBehaviorCombo.addItem(self.i18n.t("close.quit", "Quit application"), "quit")
        current_close = self.settings.data.get("closeBehavior", "tray")
        if current_close is None:
            current_close = "tray"
        close_behaviors = [closeBehaviorCombo.itemData(i) for i in range(closeBehaviorCombo.count())]
        if current_close in close_behaviors:
            closeBehaviorCombo.setCurrentIndex(close_behaviors.index(current_close))
        grid.addWidget(closeBehaviorLabel, row, 0)
        grid.addWidget(closeBehaviorCombo, row, 1)
        row += 1

        applyBtn = QtWidgets.QPushButton(self.i18n.t("apply", "Apply"))
        applyBtn.setFixedHeight(36)
        grid.addWidget(applyBtn, row, 0, 1, 2)

        # i18n texts - 设置其他控件的文本（已在创建时设置的不需要重复设置）
        hotkeysLabel.setText(self.i18n.t("section.hotkeys", "Hotkeys"))

        def on_apply():
            # 获取按键值（已通过按键捕获控件验证）
            def get_key_value(key_edit):
                text = key_edit.text().strip().upper()
                if not text:
                    return None
                return text
            
            k1_val = get_key_value(k1)
            k2_val = get_key_value(k2)
            k3_val = get_key_value(k3)
            
            # 检查是否有未设置的按键
            if not k1_val:
                QtWidgets.QMessageBox.warning(self, self.i18n.t("error", "Error"), 
                    self.i18n.t("hotkey.missing", "Please set the lock hotkey."))
                return
            if not k2_val:
                QtWidgets.QMessageBox.warning(self, self.i18n.t("error", "Error"), 
                    self.i18n.t("hotkey.missing.unlock", "Please set the unlock hotkey."))
                return
            if not k3_val:
                QtWidgets.QMessageBox.warning(self, self.i18n.t("error", "Error"), 
                    self.i18n.t("hotkey.missing.toggle", "Please set the toggle hotkey."))
                return
            
            hk = self.settings.data["hotkeys"]
            hk["lock"] = {"modCtrl": c1.isChecked(), "modAlt": a1.isChecked(), "modShift": s1.isChecked(), "key": k1_val}
            hk["unlock"] = {"modCtrl": c2.isChecked(), "modAlt": a2.isChecked(), "modShift": s2.isChecked(), "key": k2_val}
            hk["toggle"] = {"modCtrl": c3.isChecked(), "modAlt": a3.isChecked(), "modShift": s3.isChecked(), "key": k3_val}

            self.settings.data["recenter"]["enabled"] = recenterEnabled.isChecked()
            self.settings.data["recenter"]["intervalMs"] = int(recenterSpin.value())
            self.settings.data["position"]["mode"] = posCombo.currentData()
            self.settings.data["position"]["customX"] = int(xSpin.value())
            self.settings.data["position"]["customY"] = int(ySpin.value())
            self.settings.data["language"] = langCombo.currentData()
            
            # Apply theme
            new_theme = themeCombo.currentData()
            if self.settings.data.get("theme") != new_theme:
                self.settings.data["theme"] = new_theme
                self._apply_theme(new_theme)
            
            # Apply close behavior
            self.settings.data["closeBehavior"] = closeBehaviorCombo.currentData()

            self.settings.save()

            try:
                unregister_hotkeys()
                register_hotkeys(self.settings, {
                    "lock": self.lock,
                    "unlock": self.unlock,
                    "toggle": self.toggle_lock
                })
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, self.i18n.t("error", "Error"), 
                    self.i18n.t("hotkey.register.fail", "Failed to register hotkeys") + f": {str(e)}")

            self._update_toggle_button()
            self._update_tray_meta()
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), self.i18n.t("saved", "Saved"), page)

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
        cx, cy = self._resolve_target_position()
        set_cursor_to(cx, cy)
        try:
            clip_cursor_to_point(cx, cy)
        except Exception:
            pass

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


def main():
    app = QtWidgets.QApplication(sys.argv)

    settings = SettingsManager()
    i18n = I18n(settings.data.get("language", "zh-Hans"))

    window = MainWindow(settings, i18n)
    window.show()

    # Register hotkeys with callbacks
    try:
        register_hotkeys(settings, {
            "lock": window.lock,
            "unlock": window.unlock,
            "toggle": window.toggle_lock
        })
    except Exception as e:
        QtWidgets.QMessageBox.critical(None, i18n.t("error","Error"), 
            i18n.t("hotkey.register.fail","Failed to register hotkeys") + f": {str(e)}")

    ret = app.exec()
    try:
        if window.locked:
            unclip_cursor()
    finally:
        unregister_hotkeys()
        try:
            keyboard.unhook_all()
        except Exception:
            pass
    return ret


if __name__ == "__main__":
    sys.exit(main())


