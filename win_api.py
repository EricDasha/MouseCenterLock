"""
Windows API helpers for MouseCenterLock.
Provides cursor control, hotkey management, window information, and single instance detection.
"""
import ctypes
import os
import sys
from ctypes import wintypes
from typing import Optional, Tuple, List, Dict, Any

# --- Windows DLL references ---
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# --- Constants ---
WM_HOTKEY = 0x0312

# Modifier keys
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

# Hotkey IDs
HOTKEY_ID_LOCK = 1
HOTKEY_ID_UNLOCK = 2
HOTKEY_ID_TOGGLE = 4

# System metrics
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_CXSCREEN = 0
SM_CYSCREEN = 1

# Process access flags
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010


# --- Structures ---
class RECT(ctypes.Structure):
    """Windows RECT structure for cursor clipping."""
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MSG(ctypes.Structure):
    """Windows MSG structure for message handling."""
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


# --- Single Instance Detection ---
_mutex_handle: Optional[int] = None
MUTEX_NAME = "Global\\MouseCenterLock_SingleInstance"


def acquire_single_instance() -> bool:
    """
    Attempt to acquire a mutex to ensure only one instance runs.
    Returns True if this is the first instance, False if another instance exists.
    """
    global _mutex_handle
    
    # Create or open the mutex
    _mutex_handle = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    
    if _mutex_handle:
        # Check if another instance already has the mutex
        last_error = kernel32.GetLastError()
        ERROR_ALREADY_EXISTS = 183
        if last_error == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(_mutex_handle)
            _mutex_handle = None
            return False
        return True
    return False


def release_single_instance() -> None:
    """Release the single instance mutex."""
    global _mutex_handle
    if _mutex_handle:
        kernel32.ReleaseMutex(_mutex_handle)
        kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None


def bring_existing_instance_to_front() -> bool:
    """
    Find and bring the existing instance window to front.
    Returns True if successful.
    """
    window_title = "Mouse Center Lock"
    hwnd = user32.FindWindowW(None, window_title)
    if hwnd:
        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        return True
    return False


# --- Cursor Control ---
def get_virtual_screen_center() -> Tuple[int, int]:
    """Get the center point of the virtual screen (all monitors combined)."""
    x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return x + w // 2, y + h // 2


def get_primary_screen_center() -> Tuple[int, int]:
    """Get the center point of the primary screen."""
    w = user32.GetSystemMetrics(SM_CXSCREEN)
    h = user32.GetSystemMetrics(SM_CYSCREEN)
    return w // 2, h // 2


def set_cursor_to(x: int, y: int) -> None:
    """Move the cursor to the specified position."""
    user32.SetCursorPos(int(x), int(y))


def clip_cursor_to_point(x: int, y: int) -> None:
    """Confine the cursor to a single pixel at (x, y)."""
    rect = RECT(x, y, x, y)
    if not user32.ClipCursor(ctypes.byref(rect)):
        raise ctypes.WinError()


def unclip_cursor() -> None:
    """Remove cursor clipping, allowing free movement."""
    if not user32.ClipCursor(None):
        raise ctypes.WinError()


# --- Window Information ---
def get_active_window_info() -> Tuple[Optional[int], Optional[str]]:
    """
    Get the handle and title of the currently active window.
    Returns (hwnd, title) or (None, None) if no window is active.
    """
    hwnd = user32.GetForegroundWindow()
    if hwnd == 0:
        return None, None
    
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return hwnd, ""
    
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return hwnd, buffer.value


def get_window_process_name(hwnd: int) -> Optional[str]:
    """Get the process name for a given window handle."""
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    
    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        return None
    
    try:
        filename_buffer = ctypes.create_unicode_buffer(260)
        size = wintypes.DWORD(260)
        if kernel32.QueryFullProcessImageNameW(handle, 0, filename_buffer, ctypes.byref(size)):
            return os.path.basename(filename_buffer.value)
    finally:
        kernel32.CloseHandle(handle)
    
    return None


def enumerate_visible_windows() -> List[Tuple[int, str, str]]:
    """
    Enumerate all visible windows with titles.
    Returns list of (hwnd, title, process_name) tuples.
    """
    windows = []
    
    def enum_callback(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value
                proc_name = get_window_process_name(hwnd) or "unknown.exe"
                windows.append((hwnd, title, proc_name))
        return True
    
    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(enum_proc(enum_callback), 0)
    
    windows.sort(key=lambda x: x[1].lower())
    return windows


# --- Hotkey Management ---
def build_mod_flags(cfg: Dict[str, Any]) -> int:
    """Build modifier flags from a hotkey configuration dict."""
    mods = 0
    if cfg.get("modCtrl"):
        mods |= MOD_CONTROL
    if cfg.get("modAlt"):
        mods |= MOD_ALT
    if cfg.get("modShift"):
        mods |= MOD_SHIFT
    if cfg.get("modWin"):
        mods |= MOD_WIN
    return mods


def key_to_vk(key_str: str) -> Optional[int]:
    """
    Convert a key string to a virtual key code.
    Supports: A-Z, 0-9, F1-F24
    """
    s = (key_str or "").upper().strip()
    if not s:
        return None
    
    # Single letter A-Z
    if len(s) == 1 and 'A' <= s <= 'Z':
        return ord(s)
    
    # Single digit 0-9
    if len(s) == 1 and '0' <= s <= '9':
        return ord(s)
    
    # Function keys F1-F24
    if s.startswith('F') and s[1:].isdigit():
        n = int(s[1:])
        if 1 <= n <= 24:
            return 0x70 + (n - 1)
    
    return None


def vk_to_key(vk: int) -> Optional[str]:
    """Convert a virtual key code back to a key string."""
    # A-Z
    if 0x41 <= vk <= 0x5A:
        return chr(vk)
    # 0-9
    if 0x30 <= vk <= 0x39:
        return chr(vk)
    # F1-F24
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x70 + 1}"
    return None


def format_hotkey_display(cfg: Dict[str, Any]) -> str:
    """Format a hotkey configuration for display (e.g., 'Ctrl+Alt+L')."""
    parts = []
    if cfg.get("modCtrl"):
        parts.append("Ctrl")
    if cfg.get("modAlt"):
        parts.append("Alt")
    if cfg.get("modShift"):
        parts.append("Shift")
    if cfg.get("modWin"):
        parts.append("Win")
    parts.append(cfg.get("key", "?"))
    return "+".join(parts)


def try_register_hotkey(hotkey_id: int, mod_flags: int, vk: int) -> Tuple[bool, Optional[str]]:
    """
    Try to register a hotkey.
    Returns (success, error_message).
    """
    if not vk:
        return False, "Invalid key"
    
    if user32.RegisterHotKey(None, hotkey_id, mod_flags, vk):
        return True, None
    
    error_code = kernel32.GetLastError()
    if error_code == 1409:  # ERROR_HOTKEY_ALREADY_REGISTERED
        return False, "Hotkey already in use by another application"
    return False, f"Failed to register hotkey (error {error_code})"


def register_hotkeys(settings_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Register all hotkeys from settings.
    Returns (all_success, list_of_errors).
    """
    hk = settings_data.get("hotkeys", {})
    errors = []
    
    specs = [
        (HOTKEY_ID_LOCK, hk.get("lock", {})),
        (HOTKEY_ID_UNLOCK, hk.get("unlock", {})),
        (HOTKEY_ID_TOGGLE, hk.get("toggle", {})),
    ]
    
    for hotkey_id, spec in specs:
        mods = build_mod_flags(spec)
        vk = key_to_vk(spec.get("key", ""))
        success, error = try_register_hotkey(hotkey_id, mods, vk)
        if not success:
            errors.append(f"{format_hotkey_display(spec)}: {error}")
    
    return len(errors) == 0, errors


def unregister_hotkeys() -> None:
    """Unregister all hotkeys."""
    user32.UnregisterHotKey(None, HOTKEY_ID_LOCK)
    user32.UnregisterHotKey(None, HOTKEY_ID_UNLOCK)
    user32.UnregisterHotKey(None, HOTKEY_ID_TOGGLE)


# --- Startup Management ---
def get_startup_registry_key():
    """Get the Windows registry key for startup programs."""
    import winreg
    return winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_ALL_ACCESS
    )


def is_startup_enabled() -> bool:
    """Check if the application is set to run at startup."""
    import winreg
    try:
        key = get_startup_registry_key()
        try:
            winreg.QueryValueEx(key, "MouseCenterLock")
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def set_startup_enabled(enabled: bool) -> bool:
    """
    Enable or disable running at startup.
    Returns True if successful.
    """
    import winreg
    
    try:
        key = get_startup_registry_key()
        try:
            if enabled:
                # Get the executable path
                if getattr(sys, 'frozen', False):
                    exe_path = sys.executable
                else:
                    exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
                
                winreg.SetValueEx(key, "MouseCenterLock", 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, "MouseCenterLock")
                except FileNotFoundError:
                    pass  # Already deleted
            return True
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False
