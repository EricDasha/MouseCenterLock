"""
Presentation helpers for tray text and state summaries.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from win_api import format_hotkey_display


def build_tray_state_text(i18n, *, locked: bool, clicker_running: bool, clicker_profile: Dict[str, Any]) -> str:
    """Build the primary tray state line."""
    state = i18n.t("status.locked", "Locked") if locked else i18n.t("status.unlocked", "Unlocked")
    clicker_state = i18n.t("simple.on", "On") if clicker_running else i18n.t("simple.off", "Off")
    return (
        f"● {state} | {i18n.t('simple.clicker', 'Auto Clicker')}: "
        f"{clicker_state} | {clicker_profile.get('name', '')}"
    )


def build_tray_hotkey_text(i18n, *, hotkeys: Dict[str, Any], clicker_profile: Dict[str, Any]) -> str:
    """Build the tray hotkey summary line."""
    trigger_hotkey = clicker_profile.get("triggers", {}).get("toggleHotkey", {})
    return (
        f"{i18n.t('hotkey.toggle', 'Toggle')}: {format_hotkey_display(hotkeys['toggle'])} | "
        f"{i18n.t('clicker.hotkey', 'Auto Clicker Toggle')}: {format_hotkey_display(trigger_hotkey)}"
    )


def build_tray_clicker_action(i18n, *, clicker_running: bool, clicker_profile: Dict[str, Any]) -> Tuple[str, bool]:
    """Build the tray clicker action label and enabled state."""
    text = (
        i18n.t("menu.clicker.stop", "Stop Auto Clicker")
        if clicker_running
        else i18n.t("menu.clicker.start", "Start Auto Clicker")
    )
    return text, bool(clicker_profile.get("enabled", False))
