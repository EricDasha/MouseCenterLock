"""
Optional Rust input backend.

The DLL exports a tiny C ABI over Windows SendInput. Python remains the
orchestrator for JSON/state-machine logic; Rust owns the hot-path input
injection batch when the native artifact is present.
"""
from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

from app_logging import log_exception, log_message

try:
    from app_paths import APP_DIR
except Exception:  # pragma: no cover - import guard for isolated tests
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DLL_NAME = "mcl_input_backend.dll"
VERSION_NAME = "mcl_input_backend.version"

_BUTTON_CODES = {
    "left": 0,
    "right": 1,
    "middle": 2,
    "x1": 3,
    "back": 3,
    "xbutton1": 3,
    "button4": 3,
    "x2": 4,
    "forward": 4,
    "xbutton2": 4,
    "button5": 4,
}


def _candidate_paths() -> list[Path]:
    base_dir = Path(getattr(sys, "_MEIPASS", APP_DIR))
    module_root = Path(__file__).resolve().parent.parent
    paths = [
        base_dir / "native" / DLL_NAME,
        module_root / "native" / DLL_NAME,
        Path.cwd() / "native" / DLL_NAME,
    ]
    return list(dict.fromkeys(paths))


_LOADED_PATH: Path | None = None
_VERSION_TEXT = ""


def _version_text_for(path: Path) -> str:
    version_path = path.with_name(VERSION_NAME)
    try:
        return version_path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _load_library():
    global _LOADED_PATH, _VERSION_TEXT
    if os.name != "nt":
        return None
    for path in _candidate_paths():
        if not path.exists():
            continue
        try:
            lib = ctypes.WinDLL(str(path))
            lib.mcl_native_version.argtypes = ()
            lib.mcl_native_version.restype = ctypes.c_uint32
            lib.mcl_click_mouse.argtypes = (ctypes.c_uint32,)
            lib.mcl_click_mouse.restype = ctypes.c_int
            lib.mcl_key_down_vk.argtypes = (ctypes.c_uint16,)
            lib.mcl_key_down_vk.restype = ctypes.c_int
            lib.mcl_key_up_vk.argtypes = (ctypes.c_uint16,)
            lib.mcl_key_up_vk.restype = ctypes.c_int
            lib.mcl_press_vk.argtypes = (ctypes.c_uint16,)
            lib.mcl_press_vk.restype = ctypes.c_int
            lib.mcl_type_utf16.argtypes = (ctypes.POINTER(ctypes.c_uint16), ctypes.c_size_t)
            lib.mcl_type_utf16.restype = ctypes.c_int
            _LOADED_PATH = path
            _VERSION_TEXT = _version_text_for(path)
            version_suffix = f" version={_VERSION_TEXT.replace(chr(10), '; ')}" if _VERSION_TEXT else ""
            log_message(f"Rust input backend loaded: path={path}{version_suffix}")
            return lib
        except Exception as exc:
            log_exception(f"Rust input backend load failed: {path}", exc)
    return None


_LIB = _load_library()
AVAILABLE = _LIB is not None


def status() -> str:
    """Return a compact runtime status string for diagnostics."""
    if not AVAILABLE:
        return "unavailable"
    version = _VERSION_TEXT.replace("\n", "; ") if _VERSION_TEXT else "version=unknown"
    return f"loaded path={_LOADED_PATH} {version}"


def click_mouse(button: str = "left") -> bool:
    if not _LIB:
        return False
    code = _BUTTON_CODES.get(str(button or "left").lower(), 0)
    return int(_LIB.mcl_click_mouse(code)) > 0


def key_down_vk(vk: int) -> bool:
    return bool(_LIB and int(_LIB.mcl_key_down_vk(int(vk) & 0xFFFF)) > 0)


def key_up_vk(vk: int) -> bool:
    return bool(_LIB and int(_LIB.mcl_key_up_vk(int(vk) & 0xFFFF)) > 0)


def press_vk(vk: int) -> bool:
    return bool(_LIB and int(_LIB.mcl_press_vk(int(vk) & 0xFFFF)) > 0)


def type_text(text: str) -> bool:
    if not _LIB:
        return False
    encoded = str(text or "")[:1024].encode("utf-16-le", errors="ignore")
    if not encoded:
        return True
    units = (ctypes.c_uint16 * (len(encoded) // 2)).from_buffer_copy(encoded)
    return int(_LIB.mcl_type_utf16(units, len(units))) > 0
