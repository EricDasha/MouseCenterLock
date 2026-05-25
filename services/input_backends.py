"""
Input backend registry and availability diagnostics.

This module is the stage-2 seam for virtual HID and hardware HID.  The current
virtual-hid implementation is detection-only: it reports an unavailable state
instead of pretending to send input.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Any, Dict

from services import native_input


BACKEND_AUTO = "auto"
BACKEND_NATIVE_SENDINPUT = "native-sendinput"
BACKEND_PYTHON_SENDINPUT = "python-sendinput"
BACKEND_WINDOW_MESSAGE = "window-message"
BACKEND_VIRTUAL_HID = "virtual-hid"
BACKEND_HARDWARE_HID = "hardware-hid"
BACKEND_SENDINPUT = "sendinput"  # legacy alias
BACKEND_NATIVE_SCANCODE = "native-scancode"  # legacy alias
BACKEND_PYTHON_FALLBACK = "python-fallback"  # legacy alias

BACKEND_ALIASES = {
    BACKEND_SENDINPUT: BACKEND_NATIVE_SENDINPUT,
    BACKEND_NATIVE_SCANCODE: BACKEND_NATIVE_SENDINPUT,
    BACKEND_PYTHON_FALLBACK: BACKEND_PYTHON_SENDINPUT,
}

VALID_BACKENDS = {
    BACKEND_AUTO,
    BACKEND_NATIVE_SENDINPUT,
    BACKEND_PYTHON_SENDINPUT,
    BACKEND_WINDOW_MESSAGE,
    BACKEND_VIRTUAL_HID,
    BACKEND_HARDWARE_HID,
    *BACKEND_ALIASES.keys(),
}
INPUT_BACKENDS = {
    BACKEND_AUTO,
    BACKEND_NATIVE_SENDINPUT,
    BACKEND_PYTHON_SENDINPUT,
    BACKEND_WINDOW_MESSAGE,
    BACKEND_VIRTUAL_HID,
    BACKEND_HARDWARE_HID,
}
INPUT_BACKEND_ALIASES = BACKEND_ALIASES

VALID_FALLBACK_POLICIES = {"auto", "error", "disabled"}


@dataclass(frozen=True)
class BackendCapabilities:
    supportsKeyboard: bool
    supportsMouse: bool
    supportsUnicode: bool
    supportsWindowMessage: bool

    def to_dict(self) -> Dict[str, bool]:
        return asdict(self)


@dataclass(frozen=True)
class BackendStatus:
    name: str
    available: bool
    state: str
    reason: str | None
    capabilities: BackendCapabilities

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["capabilities"] = self.capabilities.to_dict()
        return payload


class InputBackend:
    """Backend metadata and future output interface."""

    name = ""
    capabilities = BackendCapabilities(False, False, False, False)

    def status(self) -> BackendStatus:
        return BackendStatus(
            name=self.name,
            available=True,
            state="ready",
            reason=None,
            capabilities=self.capabilities,
        )

    def send_key(self, *_args, **_kwargs) -> bool:
        return False

    def send_mouse(self, *_args, **_kwargs) -> bool:
        return False

    def send_text(self, *_args, **_kwargs) -> bool:
        return False

    def get_capabilities(self) -> Dict[str, bool]:
        return self.capabilities.to_dict()


class NativeSendInputBackend(InputBackend):
    name = BACKEND_NATIVE_SENDINPUT
    capabilities = BackendCapabilities(True, True, True, False)

    def status(self) -> BackendStatus:
        return BackendStatus(
            name=self.name,
            available=native_input.AVAILABLE,
            state="ready" if native_input.AVAILABLE else "unavailable",
            reason=None if native_input.AVAILABLE else "native_dll_not_loaded",
            capabilities=self.capabilities,
        )


class PythonSendInputBackend(InputBackend):
    name = BACKEND_PYTHON_SENDINPUT
    capabilities = BackendCapabilities(True, True, False, False)


class WindowMessageBackend(InputBackend):
    name = BACKEND_WINDOW_MESSAGE
    capabilities = BackendCapabilities(True, True, False, True)


class VirtualHidBackend(InputBackend):
    name = BACKEND_VIRTUAL_HID
    capabilities = BackendCapabilities(True, True, False, False)

    def status(self) -> BackendStatus:
        if os.name != "nt":
            return BackendStatus(self.name, False, "unavailable", "unsupported_os", self.capabilities)
        # Detection-only placeholder. A later installer/detector can replace
        # this with service/device checks without changing InputService callers.
        return BackendStatus(self.name, False, "unavailable", "driver_not_installed", self.capabilities)


class HardwareHidBackend(InputBackend):
    name = BACKEND_HARDWARE_HID
    capabilities = BackendCapabilities(True, True, False, False)

    def status(self) -> BackendStatus:
        return BackendStatus(self.name, False, "unavailable", "device_not_connected", self.capabilities)


_BACKENDS: Dict[str, InputBackend] = {
    BACKEND_NATIVE_SENDINPUT: NativeSendInputBackend(),
    BACKEND_PYTHON_SENDINPUT: PythonSendInputBackend(),
    BACKEND_WINDOW_MESSAGE: WindowMessageBackend(),
    BACKEND_VIRTUAL_HID: VirtualHidBackend(),
    BACKEND_HARDWARE_HID: HardwareHidBackend(),
}


def normalize_backend(value: str | None) -> str:
    backend = str(value or BACKEND_AUTO).strip().lower()
    if backend not in VALID_BACKENDS:
        return BACKEND_AUTO
    return BACKEND_ALIASES.get(backend, backend)


def normalize_fallback_policy(value: str | None) -> str:
    policy = str(value or "auto").strip().lower()
    return policy if policy in VALID_FALLBACK_POLICIES else "auto"


def get_backend_status(name: str) -> BackendStatus:
    backend_name = normalize_backend(name)
    if backend_name == BACKEND_AUTO:
        backend_name = BACKEND_NATIVE_SENDINPUT
    backend = _BACKENDS.get(backend_name) or _BACKENDS[BACKEND_NATIVE_SENDINPUT]
    return backend.status()


def all_backend_statuses() -> Dict[str, Dict[str, Any]]:
    return {name: backend.status().to_dict() for name, backend in _BACKENDS.items()}
