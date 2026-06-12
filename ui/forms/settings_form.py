"""
Helpers for mapping general application settings to and from the UI form.
"""
from __future__ import annotations

from typing import Any, Dict

VALID_INPUT_BACKENDS = {"auto", "native-sendinput", "python-sendinput", "window-message", "virtual-hid", "hardware-hid"}
INPUT_BACKEND_ALIASES = {"sendinput": "native-sendinput", "native-scancode": "native-sendinput", "python-fallback": "python-sendinput"}


def _collect_target_windows(window) -> list[str]:
    """Collect target-window entries from the list widget."""
    return [window.targetList.item(i).text() for i in range(window.targetList.count())]


def _collect_list_widget_items(widget) -> list[str]:
    """Collect text entries from a QListWidget-like object."""
    return [widget.item(i).text() for i in range(widget.count())]


def _collect_window_size(window) -> Dict[str, int]:
    """Collect the current window size with test-double fallback support."""
    width = 0
    height = 0
    if hasattr(window, "width") and callable(window.width):
        width = int(window.width())
    elif hasattr(window, "size") and callable(window.size):
        size = window.size()
        if hasattr(size, "width") and callable(size.width):
            width = int(size.width())
        elif hasattr(size, "width"):
            width = int(size.width)
    if hasattr(window, "height") and callable(window.height):
        height = int(window.height())
    elif hasattr(window, "size") and callable(window.size):
        size = window.size()
        if hasattr(size, "height") and callable(size.height):
            height = int(size.height())
        elif hasattr(size, "height"):
            height = int(size.height)
    return {"width": width, "height": height}


def _collect_mouse_macro_settings(window) -> Dict[str, Any]:
    """Collect mouse macro settings from the advanced page."""
    if not hasattr(window, "mouseMacroEnabledCheck"):
        settings = getattr(window, "settings", None)
        return getattr(settings, "data", {}).get("mouseMacros", {})

    settings = getattr(window, "settings", None)
    current_macro_cfg = getattr(settings, "data", {}).get("mouseMacros", {}) if settings else {}
    current_rules = current_macro_cfg.get("rules", []) if isinstance(current_macro_cfg, dict) else []
    current_rule = current_rules[0] if isinstance(current_rules, list) and current_rules and isinstance(current_rules[0], dict) else {}

    action_type = window.mouseMacroActionTypeCombo.currentData() or "hotkey"
    action: Dict[str, Any] = {"type": action_type}
    if action_type in ("mouseDown", "mouseUp", "mouseClick"):
        action["button"] = window.mouseMacroActionMouseCombo.currentData() or "left"
    elif action_type == "text":
        action["text"] = window.mouseMacroActionTextEdit.text()
    elif action_type == "delay":
        action["ms"] = window.mouseMacroDelaySpin.value()
    else:
        action.update(window.mouseMacroActionHotkeyCapture.get_hotkey())
        if action_type in ("key", "keyDown", "keyUp"):
            action = {"type": action_type, "key": action.get("key", "")}

    builder_rule: Dict[str, Any] = {
        "id": "builder-rule-1",
        "name": window.mouseMacroNameEdit.text().strip() or "Macro",
        "enabled": window.mouseMacroRuleEnabledCheck.isChecked(),
        "triggerMode": window.mouseMacroTriggerModeCombo.currentData() or "hold",
        "holdMouseButton": window.mouseMacroHoldCombo.currentData() or "x2",
        "pressMouseButton": window.mouseMacroPressCombo.currentData() or "left",
        "actions": [action],
    }
    for field in (
        "holdKey",
        "pressKey",
        "toggleOnKey",
        "toggleOffKey",
        "toggleOnMouseButton",
        "toggleOffMouseButton",
        "loopIntervalMs",
        "loopWhilePressHeld",
    ):
        if field in current_rule:
            builder_rule[field] = current_rule[field]

    return {
        "enabled": window.mouseMacroEnabledCheck.isChecked(),
        "source": window.mouseMacroSourceCombo.currentData() or "builder",
        "configFile": window.mouseMacroConfigFileEdit.text().strip(),
        "panicHotkey": window.mouseMacroPanicHotkeyCapture.get_hotkey()
        if hasattr(window, "mouseMacroPanicHotkeyCapture")
        else {"modCtrl": False, "modAlt": False, "modShift": False, "modWin": False, "key": "F12"},
        "sound": {
            "start": {
                "enabled": window.mouseMacroStartSoundEnabledCheck.isChecked(),
                "preset": window.mouseMacroStartSoundPresetCombo.currentData() or "systemAsterisk",
                "customFile": window.mouseMacroStartCustomSoundPathEdit.text().strip(),
            },
            "stop": {
                "enabled": window.mouseMacroStopSoundEnabledCheck.isChecked(),
                "preset": window.mouseMacroStopSoundPresetCombo.currentData() or "systemHand",
                "customFile": window.mouseMacroStopCustomSoundPathEdit.text().strip(),
            },
        },
        "rules": [builder_rule],
    }


def collect_general_settings_form_data(window) -> Dict[str, Any]:
    """Build a settings payload from the non-clicker controls."""
    existing_binding = getattr(getattr(window, "settings", None), "data", {}).get("profileListBinding", {})
    if not isinstance(existing_binding, dict):
        existing_binding = {}
    follow_profile_lists = (
        window.profileListFollowCheck.isChecked()
        if hasattr(window, "profileListFollowCheck")
        else bool(existing_binding.get("followProfile", True))
    )
    frozen_process_blacklist = existing_binding.get("processBlacklist", [])
    frozen_window_specific = existing_binding.get("windowSpecific", {})
    if not follow_profile_lists:
        if hasattr(window, "clickerProcessBlacklist"):
            frozen_process_blacklist = _collect_list_widget_items(window.clickerProcessBlacklist)
        frozen_window_specific = {
            "enabled": window.windowSpecificCheck.isChecked(),
            "targetWindows": _collect_target_windows(window),
            "targetWindowHandle": 0,
            "autoLockOnWindowFocus": window.autoLockCheck.isChecked(),
            "resumeAfterWindowSwitch": window.resumeAfterSwitchCheck.isChecked(),
        }
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
        "ui": {
            "rememberWindowSize": window.rememberWindowSizeCheck.isChecked() if hasattr(window, "rememberWindowSizeCheck") else False,
            "windowSize": _collect_window_size(window),
        },
        "taskbar": {
            "stateFlashEnabled": window.taskbarStateFlashCheck.isChecked() if hasattr(window, "taskbarStateFlashCheck") else True,
            "stateFlashMs": window.taskbarStateFlashSpin.value() if hasattr(window, "taskbarStateFlashSpin") else 1000,
        },
        "profileListBinding": {
            "followProfile": follow_profile_lists,
            "processBlacklist": frozen_process_blacklist if isinstance(frozen_process_blacklist, list) else [],
            "windowSpecific": frozen_window_specific if isinstance(frozen_window_specific, dict) else {},
        },
        "inputBackend": window.inputBackendCombo.currentData() if hasattr(window, "inputBackendCombo") else "auto",
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

    ui_data = form_data.get("ui", {})
    if isinstance(ui_data, dict):
        settings.data.setdefault("ui", {})
        remember_window_size = bool(ui_data.get("rememberWindowSize", False))
        settings.data["ui"]["rememberWindowSize"] = remember_window_size
        if remember_window_size:
            window_size = ui_data.get("windowSize", {})
            if not isinstance(window_size, dict):
                window_size = {}
            try:
                width = max(0, int(window_size.get("width", 0) or 0))
                height = max(0, int(window_size.get("height", 0) or 0))
            except Exception:
                width = 0
                height = 0
            settings.data["ui"]["windowSize"] = {"width": width, "height": height}

    if "inputBackend" in form_data:
        backend = str(form_data.get("inputBackend") or "auto").strip().lower()
        backend = INPUT_BACKEND_ALIASES.get(backend, backend)
        settings.data["inputBackend"] = backend if backend in VALID_INPUT_BACKENDS else "auto"

    if "taskbar" in form_data:
        taskbar_data = form_data.get("taskbar", {})
        if isinstance(taskbar_data, dict):
            settings.data.setdefault("taskbar", {})
            settings.data["taskbar"]["stateFlashEnabled"] = bool(taskbar_data.get("stateFlashEnabled", True))
            settings.data["taskbar"]["stateFlashMs"] = max(100, min(10000, int(taskbar_data.get("stateFlashMs", 1000) or 1000)))

    if "profileListBinding" in form_data:
        binding = form_data.get("profileListBinding", {})
        if isinstance(binding, dict):
            frozen_process_blacklist = binding.get("processBlacklist", [])
            if not isinstance(frozen_process_blacklist, list):
                frozen_process_blacklist = []
            frozen_window_specific = binding.get("windowSpecific", {})
            if not isinstance(frozen_window_specific, dict):
                frozen_window_specific = {}
            settings.data["profileListBinding"] = {
                "followProfile": bool(binding.get("followProfile", True)),
                "processBlacklist": [
                    str(item).strip()
                    for item in frozen_process_blacklist
                    if str(item).strip()
                ],
                "windowSpecific": {
                    "enabled": bool(frozen_window_specific.get("enabled", form_data["windowSpecific"]["enabled"])),
                    "targetWindows": [
                        str(item).strip()
                        for item in frozen_window_specific.get("targetWindows", form_data["windowSpecific"]["targetWindows"])
                        if str(item).strip()
                    ],
                    "targetWindowHandle": 0,
                    "autoLockOnWindowFocus": bool(
                        frozen_window_specific.get("autoLockOnWindowFocus", form_data["windowSpecific"]["autoLockOnWindowFocus"])
                    ),
                    "resumeAfterWindowSwitch": bool(
                        frozen_window_specific.get("resumeAfterWindowSwitch", form_data["windowSpecific"]["resumeAfterWindowSwitch"])
                    ),
                },
            }

    if "mouseMacros" in form_data:
        settings.data["mouseMacros"] = form_data["mouseMacros"]
        if hasattr(settings, "_ensure_mouse_macros"):
            settings._ensure_mouse_macros()
