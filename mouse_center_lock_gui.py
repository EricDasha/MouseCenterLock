"""
MouseCenterLock application entry point.
"""
from __future__ import annotations

import sys

from PySide6 import QtWidgets

from app_logging import get_log_path, log_exception, log_message
from app_runtime import HotkeyEmitter, NativeEventFilter, install_activation_server, send_activation_request
from i18n_manager import I18n
from settings_manager import SettingsManager
from ui.main_window import MainWindow
from win_api import (
    HOTKEY_ID_CLICKER_TOGGLE,
    HOTKEY_ID_LOCK,
    HOTKEY_ID_TOGGLE,
    HOTKEY_ID_UNLOCK,
    acquire_single_instance,
    register_hotkeys,
    release_single_instance,
    unregister_hotkeys,
)


def _register_startup_hotkeys(settings: SettingsManager, i18n: I18n) -> None:
    """Register startup hotkeys and warn if conflicts occur."""
    unregister_hotkeys()
    success, errors = register_hotkeys(settings.data)
    if success:
        return

    detail = "\n".join([
        i18n.t("hotkey.register.fail", "Some hotkeys could not be registered:"),
        *errors,
        "",
        i18n.t(
            "hotkey.conflict.help",
            "Windows cannot directly tell which app owns a conflicting global hotkey. Try closing other apps or changing the hotkey.",
        ),
        "",
        str(get_log_path()),
    ])
    log_message(f"Startup hotkey registration failed:\n{detail}")
    QtWidgets.QMessageBox.warning(None, i18n.t("error", "Error"), detail)


def _wire_hotkeys(app: QtWidgets.QApplication, window: MainWindow) -> None:
    """Bridge native hotkeys into the main window actions."""
    emitter = HotkeyEmitter()
    event_filter = NativeEventFilter(emitter)
    app.installNativeEventFilter(event_filter)
    app._hotkey_emitter = emitter
    app._hotkey_event_filter = event_filter

    def on_hotkey(hid: int) -> None:
        if hid == HOTKEY_ID_LOCK:
            window.lock(manual=True)
        elif hid == HOTKEY_ID_UNLOCK:
            window.unlock(manual=True)
        elif hid == HOTKEY_ID_TOGGLE:
            window.toggle_lock()
        elif hid == HOTKEY_ID_CLICKER_TOGGLE:
            window.toggle_clicker()

    emitter.hotkeyPressed.connect(on_hotkey)


def main() -> int:
    """Application entry point."""
    app = QtWidgets.QApplication(sys.argv)
    settings = SettingsManager()
    i18n = I18n(settings.data.get("language", "zh-Hans"))

    if not acquire_single_instance():
        activated = send_activation_request()
        if activated:
            return 0
        log_message("A second instance started, but activation request could not reach the running instance.")
        QtWidgets.QMessageBox.information(
            None,
            i18n.t("app.title", "Mouse Center Lock"),
            i18n.t("single_instance.running", "Application is already running.\nCheck the system tray."),
        )
        return 0

    _register_startup_hotkeys(settings, i18n)
    window = MainWindow(settings, i18n)

    try:
        app._activation_server = install_activation_server(window)
    except Exception as exc:
        log_exception("Failed to start single-instance activation server", exc)
        QtWidgets.QMessageBox.warning(
            window,
            i18n.t("error", "Error"),
            f"{i18n.t('single_instance.server.failed', 'Failed to start the single-instance activation server.')}\n\n{exc}\n{get_log_path()}",
        )

    _wire_hotkeys(app, window)
    window.show()

    ret = app.exec()
    try:
        window.stop_clicker(show_message=False)
        window._lock_service.release_cursor()
    finally:
        unregister_hotkeys()
        release_single_instance()
    return ret


if __name__ == "__main__":
    sys.exit(main())
