"""
Controller for applying advanced-page settings to runtime services.
"""
from __future__ import annotations

from typing import Any, Callable, Dict


class SettingsApplyController:
    """Coordinate saving settings, startup registration, and runtime refresh."""

    def __init__(
        self,
        *,
        settings,
        collect_general_form_data: Callable[[], Dict[str, Any]],
        collect_clicker_profile_data: Callable[[], Dict[str, Any]],
        apply_general_form_data: Callable[[Any, Dict[str, Any]], None],
        set_startup: Callable[[bool], bool],
        get_startup_enabled: Callable[[], bool],
        save_settings: Callable[[str], bool],
        sync_lock_runtime: Callable[[], None],
        get_active_clicker_profile: Callable[[], Dict[str, Any]],
        stop_clicker: Callable[..., None],
        sync_clicker_runtime: Callable[[], None],
        unregister_hotkeys: Callable[[], None],
        register_hotkeys: Callable[[Dict[str, Any]], tuple[bool, list[str]]],
        on_hotkey_conflict: Callable[[list[str]], None],
        apply_theme: Callable[[], None],
        refresh_ui: Callable[[], None],
        refresh_profiles: Callable[[], None],
        show_saved_feedback: Callable[[], None],
    ):
        self._settings = settings
        self._collect_general_form_data = collect_general_form_data
        self._collect_clicker_profile_data = collect_clicker_profile_data
        self._apply_general_form_data = apply_general_form_data
        self._set_startup = set_startup
        self._get_startup_enabled = get_startup_enabled
        self._save_settings = save_settings
        self._sync_lock_runtime = sync_lock_runtime
        self._get_active_clicker_profile = get_active_clicker_profile
        self._stop_clicker = stop_clicker
        self._sync_clicker_runtime = sync_clicker_runtime
        self._unregister_hotkeys = unregister_hotkeys
        self._register_hotkeys = register_hotkeys
        self._on_hotkey_conflict = on_hotkey_conflict
        self._apply_theme = apply_theme
        self._refresh_ui = refresh_ui
        self._refresh_profiles = refresh_profiles
        self._show_saved_feedback = show_saved_feedback

    def apply(self, *, show_feedback: bool = True) -> bool:
        """Apply settings from the current form state."""
        form_data = self._collect_general_form_data()
        self._apply_general_form_data(self._settings, form_data)
        self._settings.upsert_clicker_profile(self._collect_clicker_profile_data())

        requested_startup = bool(form_data.get("startup", {}).get("launchOnBoot", False))
        startup_updated = self._set_startup(requested_startup)
        self._settings.data.setdefault("startup", {})
        self._settings.data["startup"]["launchOnBoot"] = self._get_startup_enabled()

        if not self._save_settings("Applying settings from the advanced page"):
            return False

        self._sync_lock_runtime()
        if not self._get_active_clicker_profile().get("enabled", False):
            self._stop_clicker(show_message=False)
        else:
            self._sync_clicker_runtime()

        self._unregister_hotkeys()
        success, errors = self._register_hotkeys(self._settings.data)
        if not success:
            self._on_hotkey_conflict(errors)

        self._apply_theme()
        self._refresh_ui()
        self._refresh_profiles()

        if show_feedback:
            self._show_saved_feedback()
        return startup_updated
