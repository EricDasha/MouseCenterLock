"""
Helpers for mapping general application settings to and from the UI form.
"""
from __future__ import annotations

from typing import Any, Dict


def _collect_target_windows(window) -> list[str]:
    """Collect target-window entries from the list widget."""
    return [window.targetList.item(i).text() for i in range(window.targetList.count())]


def _collect_mouse_macro_settings(window) -> Dict[str, Any]:
    """Collect mouse macro settings from the advanced page."""
    if not hasattr(window, "mouseMacroEnabledCheck"):
        settings = getattr(window, "settings", None)
        return getattr(settings, "data", {}).get("mouseMacros", {})

    action_type = window.mouseMacroActionTypeCombo.currentData() or "hotkey"
    action: Dict[str, Any] = {"type": action_type}
    if action_type == "mouseClick":
        action["button"] = window.mouseMacroActionMouseCombo.currentData() or "left"
    elif action_type == "text":
        action["text"] = window.mouseMacroActionTextEdit.text()
    elif action_type == "delay":
        action["ms"] = window.mouseMacroDelaySpin.value()
    else:
        action.update(window.mouseMacroActionHotkeyCapture.get_hotkey())
        if action_type == "key":
            action = {"type": "key", "key": action.get("key", "")}

    return {
        "enabled": window.mouseMacroEnabledCheck.isChecked(),
        "source": window.mouseMacroSourceCombo.currentData() or "builder",
        "configFile": window.mouseMacroConfigFileEdit.text().strip(),
        "rules": [
            {
                "id": "builder-rule-1",
                "name": window.mouseMacroNameEdit.text().strip() or "Mouse Macro",
                "enabled": window.mouseMacroRuleEnabledCheck.isChecked(),
                "holdMouseButton": window.mouseMacroHoldCombo.currentData() or "x2",
                "pressMouseButton": window.mouseMacroPressCombo.currentData() or "left",
                "actions": [action],
            }
        ],
    }


def collect_general_settings_form_data(window) -> Dict[str, Any]:
    """Build a settings payload from the non-clicker controls."""
    return {
        "hotkeys": {
            "lock": window.lockHotkeyCapture.get_hotkey(),
            "unlock": window.unlockHotkeyCapture.get_hotkey(),
            "toggle": window.toggleHotkeyCapture.get_hotkey(),
        },
        "recenter": {
            "enabled": window.recenterCheck.isChecked(),
            "intervalMs": window.recenterSpin.value(),
        },
        "position": {
            "mode": window.posCombo.currentData(),
            "customX": window.customXSpin.value(),
            "customY": window.customYSpin.value(),
        },
        "windowSpecific": {
            "enabled": window.windowSpecificCheck.isChecked(),
            "targetWindows": _collect_target_windows(window),
            "autoLockOnWindowFocus": window.autoLockCheck.isChecked(),
            "resumeAfterWindowSwitch": window.resumeAfterSwitchCheck.isChecked(),
        },
        "language": window.langCombo.currentData(),
        "theme": window.themeCombo.currentData(),
        "startup": {
            "launchOnBoot": window.startupCheck.isChecked(),
        },
        "mouseMacros": _collect_mouse_macro_settings(window),
    }


def apply_general_settings_form_data(settings, form_data: Dict[str, Any]) -> None:
    """Write a collected general-settings payload into SettingsManager.data."""
    settings.data.setdefault("hotkeys", {})
    for key in ("lock", "unlock", "toggle"):
        settings.data["hotkeys"][key] = form_data["hotkeys"][key]

    settings.data.setdefault("recenter", {})
    settings.data["recenter"]["enabled"] = form_data["recenter"]["enabled"]
    settings.data["recenter"]["intervalMs"] = form_data["recenter"]["intervalMs"]

    settings.data.setdefault("position", {})
    settings.data["position"]["mode"] = form_data["position"]["mode"]
    settings.data["position"]["customX"] = form_data["position"]["customX"]
    settings.data["position"]["customY"] = form_data["position"]["customY"]

    settings.data.setdefault("windowSpecific", {})
    settings.data["windowSpecific"]["enabled"] = form_data["windowSpecific"]["enabled"]
    settings.data["windowSpecific"]["targetWindows"] = form_data["windowSpecific"]["targetWindows"]
    settings.data["windowSpecific"]["autoLockOnWindowFocus"] = form_data["windowSpecific"]["autoLockOnWindowFocus"]
    settings.data["windowSpecific"]["resumeAfterWindowSwitch"] = form_data["windowSpecific"]["resumeAfterWindowSwitch"]

    settings.data["language"] = form_data["language"]
    settings.data["theme"] = form_data["theme"]
    settings.data.setdefault("startup", {})
    settings.data["startup"]["launchOnBoot"] = form_data["startup"]["launchOnBoot"]

    if "mouseMacros" in form_data:
        settings.data["mouseMacros"] = form_data["mouseMacros"]
        if hasattr(settings, "_ensure_mouse_macros"):
            settings._ensure_mouse_macros()
