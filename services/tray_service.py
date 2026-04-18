"""
System tray and notification coordination for MouseCenterLock.
"""
from __future__ import annotations

import html
import os
import subprocess
from typing import Callable, Dict, Optional

from PySide6 import QtCore, QtGui, QtWidgets


class NotificationManager:
    """Windows notification helper with native-toast fallback behavior."""

    def __init__(self, tray: QtWidgets.QSystemTrayIcon, app_id: str = "MouseCenterLock"):
        self.tray = tray
        self.app_id = app_id
        self._toast_processes = []

    def show(
        self,
        title: str,
        message: str,
        icon: QtWidgets.QSystemTrayIcon.MessageIcon = QtWidgets.QSystemTrayIcon.Information,
        timeout_ms: int = 2000,
    ) -> None:
        """Try native Windows toast first, then fall back to tray balloons."""
        if not self._show_windows_toast(title, message):
            self.tray.showMessage(title, message, icon, timeout_ms)

    def _show_windows_toast(self, title: str, message: str) -> bool:
        """Best-effort native Windows toast via asynchronous PowerShell WinRT APIs."""
        if os.name != "nt":
            return False

        escaped_title = html.escape(title, quote=False).replace("'", "''")
        escaped_message = html.escape(message, quote=False).replace("'", "''")
        escaped_app_id = self.app_id.replace("'", "''")
        script = (
            "$ErrorActionPreference='Stop';"
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null;"
            "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime] > $null;"
            f"$xml=@\"<toast><visual><binding template='ToastGeneric'><text>{escaped_title}</text>"
            f"<text>{escaped_message}</text></binding></visual></toast>\"@;"
            "$doc=New-Object Windows.Data.Xml.Dom.XmlDocument;"
            "$doc.LoadXml($xml);"
            "$toast=[Windows.UI.Notifications.ToastNotification]::new($doc);"
            f"$notifier=[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{escaped_app_id}');"
            "$notifier.Show($toast);"
        )
        try:
            process = subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._toast_processes.append(process)
            self._toast_processes = [p for p in self._toast_processes if p.poll() is None]
            return True
        except Exception:
            return False


class TrayService(QtCore.QObject):
    """Own the tray icon, menu, and tray-facing status updates."""

    def __init__(
        self,
        *,
        parent,
        base_icon: QtGui.QIcon,
        dynamic_icon_factory: Callable[[bool], QtGui.QIcon],
        i18n,
        get_locked: Callable[[], bool],
        get_clicker_running: Callable[[], bool],
        get_clicker_profile: Callable[[], Dict],
        get_hotkeys: Callable[[], Dict],
        on_toggle_lock: Callable[[], None],
        on_lock: Callable[[], None],
        on_unlock: Callable[[], None],
        on_toggle_clicker: Callable[[], None],
        on_show_window: Callable[[], None],
        on_quit: Callable[[], None],
    ):
        super().__init__(parent)
        self._i18n = i18n
        self._base_icon = base_icon
        self._dynamic_icon_factory = dynamic_icon_factory
        self._get_locked = get_locked
        self._get_clicker_running = get_clicker_running
        self._get_clicker_profile = get_clicker_profile
        self._get_hotkeys = get_hotkeys

        self.tray = QtWidgets.QSystemTrayIcon(base_icon or dynamic_icon_factory(False), parent)
        menu = QtWidgets.QMenu()

        self.state_action = menu.addAction("")
        self.state_action.setEnabled(False)
        menu.addSeparator()

        self.hk_info_action = menu.addAction("")
        self.hk_info_action.setEnabled(False)
        menu.addSeparator()

        menu.addAction(i18n.t("menu.toggle", "Toggle Lock")).triggered.connect(on_toggle_lock)
        menu.addAction(i18n.t("menu.lock", "Lock")).triggered.connect(on_lock)
        menu.addAction(i18n.t("menu.unlock", "Unlock")).triggered.connect(on_unlock)
        self.clicker_action = menu.addAction("")
        self.clicker_action.triggered.connect(on_toggle_clicker)
        menu.addSeparator()
        menu.addAction(i18n.t("menu.show", "Show Window")).triggered.connect(on_show_window)
        menu.addAction(i18n.t("menu.quit", "Quit")).triggered.connect(on_quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        self._show_window_callback = on_show_window
        self.notification_manager = NotificationManager(self.tray)
        self.refresh()
        self.tray.show()

    def _on_activated(self, reason) -> None:
        """Handle tray icon activation."""
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self._show_window_callback()

    def refresh_icon(self) -> None:
        """Refresh tray icon based on current lock state."""
        if self._base_icon.isNull():
            self.tray.setIcon(self._dynamic_icon_factory(self._get_locked()))

    def refresh(self) -> None:
        """Refresh tray icon and metadata."""
        self.refresh_icon()
        state = self._i18n.t("status.locked", "Locked") if self._get_locked() else self._i18n.t("status.unlocked", "Unlocked")
        clicker_state = self._i18n.t("simple.on", "On") if self._get_clicker_running() else self._i18n.t("simple.off", "Off")
        clicker = self._get_clicker_profile()
        self.state_action.setText(
            f"● {state} | {self._i18n.t('simple.clicker', 'Auto Clicker')}: {clicker_state} | {clicker.get('name', '')}"
        )

        hotkeys = self._get_hotkeys()
        trigger_hotkey = clicker.get("triggers", {}).get("toggleHotkey", {})
        from win_api import format_hotkey_display

        self.hk_info_action.setText(
            f"{self._i18n.t('hotkey.toggle', 'Toggle')}: {format_hotkey_display(hotkeys['toggle'])} | "
            f"{self._i18n.t('clicker.hotkey', 'Auto Clicker Toggle')}: {format_hotkey_display(trigger_hotkey)}"
        )
        self.clicker_action.setText(
            self._i18n.t("menu.clicker.stop", "Stop Auto Clicker")
            if self._get_clicker_running()
            else self._i18n.t("menu.clicker.start", "Start Auto Clicker")
        )
        self.clicker_action.setEnabled(clicker.get("enabled", False))

    def show_notification(
        self,
        title: str,
        message: str,
        icon: QtWidgets.QSystemTrayIcon.MessageIcon = QtWidgets.QSystemTrayIcon.Information,
        timeout_ms: int = 2000,
    ) -> None:
        """Show a native notification or tray balloon."""
        self.notification_manager.show(title, message, icon, timeout_ms)
