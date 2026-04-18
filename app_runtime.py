"""
Application runtime bridges for native hotkeys and single-instance activation.
"""
from __future__ import annotations

import ctypes

from PySide6 import QtCore, QtNetwork

from app_paths import INSTANCE_SERVER_NAME
from win_api import MSG, WM_HOTKEY


class HotkeyEmitter(QtCore.QObject):
    """Emits signals when global hotkeys are pressed."""

    hotkeyPressed = QtCore.Signal(int)


class NativeEventFilter(QtCore.QAbstractNativeEventFilter):
    """Filters native Windows messages to detect registered hotkeys."""

    def __init__(self, emitter: HotkeyEmitter):
        super().__init__()
        self._emitter = emitter

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
            if msg.message == WM_HOTKEY:
                self._emitter.hotkeyPressed.emit(msg.wParam)
        return False


def send_activation_request(timeout_ms: int = 1000) -> bool:
    """Ask an already-running instance to bring itself to the foreground."""
    socket = QtNetwork.QLocalSocket()
    socket.connectToServer(INSTANCE_SERVER_NAME)
    if not socket.waitForConnected(timeout_ms):
        return False
    socket.write(b"activate")
    socket.flush()
    socket.waitForBytesWritten(timeout_ms)
    socket.disconnectFromServer()
    return True


def install_activation_server(window) -> QtNetwork.QLocalServer:
    """Install a local server used to wake the existing instance."""
    QtNetwork.QLocalServer.removeServer(INSTANCE_SERVER_NAME)
    server = QtNetwork.QLocalServer(window)

    def on_new_connection() -> None:
        while server.hasPendingConnections():
            socket = server.nextPendingConnection()
            if socket is None:
                return
            socket.readAll()
            socket.write(b"ok")
            socket.flush()
            socket.disconnectFromServer()
            socket.deleteLater()
            QtCore.QTimer.singleShot(0, window.activate_from_external_request)

    server.newConnection.connect(on_new_connection)
    if not server.listen(INSTANCE_SERVER_NAME):
        raise RuntimeError(server.errorString())
    return server
