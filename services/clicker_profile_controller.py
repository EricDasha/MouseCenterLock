"""
Controller for clicker profile CRUD flows.
"""
from __future__ import annotations

from typing import Any, Callable, Dict


class ClickerProfileController:
    """Coordinate clicker profile selection and CRUD outside MainWindow."""

    def __init__(
        self,
        *,
        settings,
        save_settings: Callable[[str], bool],
        notify: Callable[[str], None],
        stop_clicker: Callable[..., None],
        sync_clicker_runtime: Callable[[], None],
        refresh_form: Callable[[Dict[str, Any]], None],
        refresh_profile_list: Callable[[], None],
        refresh_ui: Callable[[], None],
        tooltip_saved: Callable[[], None],
        i18n,
    ):
        self._settings = settings
        self._save_settings = save_settings
        self._notify = notify
        self._stop_clicker = stop_clicker
        self._sync_clicker_runtime = sync_clicker_runtime
        self._refresh_form = refresh_form
        self._refresh_profile_list = refresh_profile_list
        self._refresh_ui = refresh_ui
        self._tooltip_saved = tooltip_saved
        self._i18n = i18n

    def select_profile(self, profile_id: str, *, clicker_running: bool) -> Dict[str, Any] | None:
        """Switch the active clicker profile."""
        if not profile_id:
            return None
        if clicker_running:
            self._stop_clicker(show_message=False)
        active = self._settings.set_active_clicker_profile(profile_id)
        if not self._save_settings("Switching active clicker profile"):
            return None
        self._refresh_form(active)
        self._refresh_ui()
        self._notify(
            self._i18n.t("clicker.profile.switched", "Switched clicker profile: {0}").format(active.get("name", ""))
        )
        return active

    def save_profile(self, profile: Dict[str, Any]) -> Dict[str, Any] | None:
        """Save the current profile edits."""
        saved = self._settings.upsert_clicker_profile(profile)
        self._refresh_profile_list()
        if not self._save_settings("Saving clicker profile"):
            return None
        self._sync_clicker_runtime()
        self._refresh_ui()
        self._tooltip_saved()
        return saved

    def create_profile(self, name: str, base_profile: Dict[str, Any]) -> Dict[str, Any] | None:
        """Create a new clicker profile from the current form state."""
        profile = self._settings.create_clicker_profile(name, base_profile)
        self._refresh_profile_list()
        if not self._save_settings("Creating clicker profile"):
            return None
        self._notify(
            self._i18n.t("clicker.profile.created", "Created clicker profile: {0}").format(profile.get("name", ""))
        )
        return profile

    def delete_profile(self, profile_id: str, *, clicker_running: bool) -> Dict[str, Any] | None:
        """Delete a clicker profile and keep a valid active profile."""
        if clicker_running:
            self._stop_clicker(show_message=False)
        new_active = self._settings.delete_clicker_profile(profile_id)
        self._refresh_profile_list()
        if not self._save_settings("Deleting clicker profile"):
            return None
        self._refresh_ui()
        self._notify(
            self._i18n.t("clicker.profile.deleted", "Deleted clicker profile. Active profile: {0}").format(
                new_active.get("name", "")
            )
        )
        return new_active
