"""
Windows taskbar progress/status indicator helper.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass


TBPF_NOPROGRESS = 0x0
TBPF_INDETERMINATE = 0x1
TBPF_NORMAL = 0x2
TBPF_ERROR = 0x4
TBPF_PAUSED = 0x8


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_string(cls, value: str) -> "GUID":
        from uuid import UUID

        u = UUID(value)
        data4 = (ctypes.c_ubyte * 8)(*u.bytes[8:])
        return cls(u.time_low, u.time_mid, u.time_hi_version, data4)


CLSID_TaskbarList = GUID.from_string("56FDF344-FD6D-11d0-958A-006097C9A090")
IID_ITaskbarList3 = GUID.from_string("EA1AFB91-9E28-4B86-90E9-9E9F8A5EEA84")


class _ITaskbarList3(ctypes.Structure):
    pass


LPITaskbarList3 = ctypes.POINTER(_ITaskbarList3)


class _ITaskbarList3VTable(ctypes.Structure):
    _fields_ = [("entries", ctypes.c_void_p * 21)]


_ITaskbarList3._fields_ = [("lpVtbl", ctypes.POINTER(_ITaskbarList3VTable))]


HRESULT = ctypes.c_long
SetProgressStateProto = ctypes.WINFUNCTYPE(HRESULT, LPITaskbarList3, wintypes.HWND, wintypes.DWORD)
SetProgressValueProto = ctypes.WINFUNCTYPE(HRESULT, LPITaskbarList3, wintypes.HWND, ctypes.c_ulonglong, ctypes.c_ulonglong)
HrInitProto = ctypes.WINFUNCTYPE(HRESULT, LPITaskbarList3)


@dataclass
class _TaskbarState:
    flag: int
    value: int
    max_value: int


class TaskbarStatusService:
    """Best-effort Windows taskbar progress wrapper."""

    def __init__(self) -> None:
        self._com_initialized = False
        self._taskbar = None
        self._available = False
        self._init()

    def _init(self) -> None:
        if ctypes.windll is None or getattr(ctypes.windll, "ole32", None) is None:
            return
        try:
            hr = ctypes.windll.ole32.CoInitialize(None)
            self._com_initialized = hr in (0, 1)
            obj = ctypes.c_void_p()
            hr = ctypes.windll.ole32.CoCreateInstance(
                ctypes.byref(CLSID_TaskbarList),
                None,
                1,
                ctypes.byref(IID_ITaskbarList3),
                ctypes.byref(obj),
            )
            if hr != 0 or not obj.value:
                return
            self._taskbar = ctypes.cast(obj, LPITaskbarList3)
            if self._call_hr_init() == 0:
                self._available = True
        except Exception:
            self._available = False

    def _call_hr_init(self) -> int:
        if not self._taskbar:
            return -1
        fn = HrInitProto(self._taskbar.contents.lpVtbl.contents.entries[3])
        return fn(self._taskbar)

    def close(self) -> None:
        if self._com_initialized:
            try:
                ctypes.windll.ole32.CoUninitialize()
            except Exception:
                pass
            self._com_initialized = False

    def available(self) -> bool:
        return self._available and self._taskbar is not None

    def _set_progress(self, hwnd: int, flag: int) -> None:
        if not self.available() or not hwnd:
            return
        try:
            set_state = SetProgressStateProto(self._taskbar.contents.lpVtbl.contents.entries[10])
            set_value = SetProgressValueProto(self._taskbar.contents.lpVtbl.contents.entries[9])
            set_state(self._taskbar, hwnd, flag)
            if flag != TBPF_NOPROGRESS:
                set_value(self._taskbar, hwnd, 100, 100)
        except Exception:
            self._available = False

    def set_state(self, hwnd: int, state: str) -> None:
        mapping = {
            "macro": TBPF_ERROR,
            "lock": TBPF_PAUSED,
            "clicker": TBPF_PAUSED,
            "unlocked": TBPF_NORMAL,
        }
        self._set_progress(hwnd, mapping.get(state, TBPF_NOPROGRESS))
