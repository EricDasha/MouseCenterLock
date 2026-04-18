"""
Helpers for mapping clicker profile data to and from the UI form.
"""
from __future__ import annotations

from typing import Any, Dict


def collect_clicker_profile_form_data(window) -> Dict[str, Any]:
    """Build a clicker profile dict from the current form controls."""
    active = window._get_active_clicker_profile()
    profile_id = window._selected_profile_id or active.get("id", "default")
    profile_name = window.clickerProfileNameEdit.text().strip() or active.get("name", "默认方案")
    preset = window.clickerPresetCombo.currentData() or "custom"
    interval_ms = window.clickerIntervalSpin.value()
    return {
        "id": profile_id,
        "name": profile_name,
        "enabled": window.clickerEnabledCheck.isChecked(),
        "button": window.clickerButtonCombo.currentData(),
        "preset": preset,
        "intervalMs": interval_ms,
        "sound": {
            "enabled": window.clickerSoundEnabledCheck.isChecked(),
            "preset": window.clickerSoundPresetCombo.currentData() or "systemAsterisk",
            "customFile": window.clickerCustomSoundPathEdit.text().strip(),
        },
        "triggers": {
            "mode": window.clickerTriggerModeCombo.currentData() or "toggle",
            "toggleHotkey": window.clickerToggleHotkeyCapture.get_hotkey(),
            "holdKey": window.clickerHoldKeyCapture.get_hotkey(),
            "holdMouseButton": window.clickerHoldMouseCombo.currentData() or "middle",
        },
    }


def load_clicker_profile_into_form(window, profile: Dict[str, Any]) -> None:
    """Populate clicker controls from a profile dict."""
    window._begin_form_update()
    try:
        window._selected_profile_id = profile.get("id", "default")
        window.clickerProfileNameEdit.setText(profile.get("name", "默认方案"))
        window.clickerEnabledCheck.setChecked(profile.get("enabled", False))

        for i in range(window.clickerButtonCombo.count()):
            if window.clickerButtonCombo.itemData(i) == profile.get("button", "left"):
                window.clickerButtonCombo.setCurrentIndex(i)
                break

        preset = profile.get("preset", window._get_clicker_preset_for_interval(profile.get("intervalMs", 100)))
        for i in range(window.clickerPresetCombo.count()):
            if window.clickerPresetCombo.itemData(i) == preset:
                window.clickerPresetCombo.setCurrentIndex(i)
                break
        window.clickerIntervalSpin.setValue(int(profile.get("intervalMs", 100)))

        triggers = profile.get("triggers", {})
        for i in range(window.clickerTriggerModeCombo.count()):
            if window.clickerTriggerModeCombo.itemData(i) == triggers.get("mode", "toggle"):
                window.clickerTriggerModeCombo.setCurrentIndex(i)
                break
        window.clickerToggleHotkeyCapture.set_hotkey(
            triggers.get("toggleHotkey", window.settings.DEFAULT_CLICKER_HOTKEY)
        )
        window.clickerHoldKeyCapture.set_hotkey(
            triggers.get("holdKey", window.settings.DEFAULT_HOLD_KEY)
        )
        for i in range(window.clickerHoldMouseCombo.count()):
            if window.clickerHoldMouseCombo.itemData(i) == triggers.get("holdMouseButton", "middle"):
                window.clickerHoldMouseCombo.setCurrentIndex(i)
                break

        sound = profile.get("sound", {})
        window.clickerSoundEnabledCheck.setChecked(sound.get("enabled", False))
        for i in range(window.clickerSoundPresetCombo.count()):
            if window.clickerSoundPresetCombo.itemData(i) == sound.get("preset", "systemAsterisk"):
                window.clickerSoundPresetCombo.setCurrentIndex(i)
                break
        window.clickerCustomSoundPathEdit.setText(sound.get("customFile", ""))
        window._sync_clicker_interval_controls()
        window._sync_clicker_trigger_controls()
        window._sync_clicker_sound_controls()
        window._profile_dirty = False
    finally:
        window._end_form_update()
