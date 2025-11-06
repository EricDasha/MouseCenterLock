import ctypes
import sys
from ctypes import wintypes


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


# Constants
WM_HOTKEY = 0x0312

# Modifiers
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

# IDs for our hotkeys
HOTKEY_ID_LOCK = 1
HOTKEY_ID_UNLOCK = 2
HOTKEY_ID_QUIT = 3


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

    center_x = x + w // 2
    center_y = y + h // 2
    return center_x, center_y


def set_cursor_to(x, y):
    user32.SetCursorPos(int(x), int(y))


def clip_cursor_to_point(x, y):
    # Confine the cursor to a single pixel at (x, y)
    rect = RECT(x, y, x, y)
    if not user32.ClipCursor(ctypes.byref(rect)):
        raise ctypes.WinError()


def unclip_cursor():
    # Pass NULL to remove any cursor clipping
    if not user32.ClipCursor(None):
        raise ctypes.WinError()


def register_hotkeys():
    # Ctrl + Alt + L => Lock
    if not user32.RegisterHotKey(None, HOTKEY_ID_LOCK, MOD_CONTROL | MOD_ALT, ord('L')):
        raise ctypes.WinError()

    # Ctrl + Alt + U => Unlock
    if not user32.RegisterHotKey(None, HOTKEY_ID_UNLOCK, MOD_CONTROL | MOD_ALT, ord('U')):
        raise ctypes.WinError()

    # Ctrl + Alt + Q => Quit
    if not user32.RegisterHotKey(None, HOTKEY_ID_QUIT, MOD_CONTROL | MOD_ALT, ord('Q')):
        raise ctypes.WinError()


def unregister_hotkeys():
    user32.UnregisterHotKey(None, HOTKEY_ID_LOCK)
    user32.UnregisterHotKey(None, HOTKEY_ID_UNLOCK)
    user32.UnregisterHotKey(None, HOTKEY_ID_QUIT)


def message_loop():
    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wParam", wintypes.WPARAM),
            ("lParam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt", wintypes.POINT),
        ]

    msg = MSG()
    locked = False

    try:
        while True:
            res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res == 0:  # WM_QUIT
                break
            if res == -1:
                raise ctypes.WinError()

            if msg.message == WM_HOTKEY:
                hotkey_id = msg.wParam
                if hotkey_id == HOTKEY_ID_LOCK:
                    cx, cy = get_virtual_screen_center()
                    set_cursor_to(cx, cy)
                    clip_cursor_to_point(cx, cy)
                    locked = True
                    # Optional: notify via console
                    print("[锁定] 鼠标已锁定到屏幕中心 (Ctrl+Alt+U 解锁, Ctrl+Alt+Q 退出)")
                elif hotkey_id == HOTKEY_ID_UNLOCK:
                    unclip_cursor()
                    locked = False
                    print("[解锁] 鼠标已解除锁定 (Ctrl+Alt+L 重新锁定)")
                elif hotkey_id == HOTKEY_ID_QUIT:
                    # Ensure cursor is unclipped before exit
                    if locked:
                        try:
                            unclip_cursor()
                        except Exception:
                            pass
                    break

            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    finally:
        try:
            unclip_cursor()
        except Exception:
            pass
        unregister_hotkeys()


def main():
    try:
        register_hotkeys()
    except Exception as e:
        print("注册热键失败:", e)
        sys.exit(1)

    print("鼠标中心锁定工具已启动：")
    print("- Ctrl+Alt+L 锁定到屏幕中心")
    print("- Ctrl+Alt+U 解锁")
    print("- Ctrl+Alt+Q 退出\n")

    message_loop()
    print("已退出。")


if __name__ == "__main__":
    main()


