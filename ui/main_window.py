"""
MouseCenterLock main window.
"""
import os
from typing import Optional, Dict, Any

from PySide6 import QtCore, QtGui, QtWidgets
from app_logging import get_log_path, log_message
from app_paths import ASSETS_DIR, RUN_DIR

from win_api import (
    release_single_instance,
    format_hotkey_display, register_hotkeys, unregister_hotkeys,
    is_startup_enabled, set_startup_enabled, enumerate_visible_windows
)
from services.clicker_service import ClickerService
from services.clicker_profile_controller import ClickerProfileController
from services.lock_service import LockService
from services.settings_apply_controller import SettingsApplyController
from services.theme_service import ThemeService
from services.tray_service import TrayService
from i18n_manager import I18n
from settings_manager import (
    SettingsManager,
    CLICKER_PRESETS,
    CLICKER_SOUND_PRESETS,
    CLICKER_TRIGGER_MODES,
)
from ui.pages.simple_page import build_simple_page
from ui.pages.advanced_page import build_advanced_page
from ui.forms.clicker_profile_form import (
    collect_clicker_profile_form_data,
    load_clicker_profile_into_form,
)
from ui.forms.settings_form import (
    apply_general_settings_form_data,
    collect_general_settings_form_data,
)
from ui.presenters.main_window_presenter import (
    build_clicker_button_presentation,
    build_simple_info_text,
    build_status_badge_presentation,
    build_toggle_button_text,
    describe_clicker_preset,
    resolve_clicker_preset,
)
from widgets import ProcessPickerDialog, CloseActionDialog, WindowResizeDialog


class MainWindow(QtWidgets.QMainWindow):
    """Main application window."""
    
    def __init__(self, settings: SettingsManager, i18n: I18n):
        super().__init__()
        self.settings = settings
        self.i18n = i18n
        
        self._custom_icon: Optional[QtGui.QIcon] = None
        self._tray_service: Optional[TrayService] = None
        self._selected_profile_id = self.settings.data.get("activeClickerProfileId", "default")
        self._profile_dirty = False
        self._suspend_live_apply = 0
        self._live_apply_timer = QtCore.QTimer(self)
        self._live_apply_timer.setSingleShot(True)
        self._live_apply_timer.timeout.connect(self._apply_live_settings)
        self._clicker_service = ClickerService(
            get_profile=self._get_active_clicker_profile,
            on_state_changed=self._on_clicker_runtime_changed,
            on_notify_started=self._notify_clicker_started,
            on_notify_stopped=self._notify_clicker_stopped,
            sound_presets=CLICKER_SOUND_PRESETS,
            parent=self,
        )
        self._lock_service = LockService(
            get_settings=lambda: self.settings.data,
            on_state_changed=self._on_lock_state_changed,
            on_notify_locked=self._notify_locked,
            on_notify_unlocked=self._notify_unlocked,
            on_error=self._handle_lock_service_error,
            parent=self,
        )
        self._theme_service = ThemeService()
        self._clicker_profile_controller = ClickerProfileController(
            settings=self.settings,
            save_settings=self._save_settings_or_warn,
            notify=self._notify,
            stop_clicker=self.stop_clicker,
            sync_clicker_runtime=self._clicker_service.sync_runtime,
            refresh_form=self._load_profile_into_form,
            refresh_profile_list=self._populate_clicker_profiles,
            refresh_ui=self._refresh_clicker_ui,
            tooltip_saved=self._show_saved_tooltip,
            i18n=self.i18n,
        )
        self._settings_apply_controller = SettingsApplyController(
            settings=self.settings,
            collect_general_form_data=self._current_general_settings_form_data,
            collect_clicker_profile_data=self._current_profile_form_data,
            apply_general_form_data=apply_general_settings_form_data,
            set_startup=self._set_startup_or_warn,
            get_startup_enabled=is_startup_enabled,
            save_settings=self._save_settings_or_warn,
            sync_lock_runtime=self._lock_service.sync_runtime,
            get_active_clicker_profile=self._get_active_clicker_profile,
            stop_clicker=self.stop_clicker,
            sync_clicker_runtime=self._clicker_service.sync_runtime,
            unregister_hotkeys=unregister_hotkeys,
            register_hotkeys=register_hotkeys,
            on_hotkey_conflict=self._register_hotkeys_or_warn,
            apply_theme=self._apply_theme,
            refresh_ui=self._refresh_all_runtime_ui,
            refresh_profiles=self._populate_clicker_profiles,
            show_saved_feedback=self._show_saved_tooltip,
        )
        
        self._setup_window()
        self._setup_timers()
        self._build_ui()
        self._apply_theme()
        self._create_tray()
    
    @property
    def locked(self) -> bool:
        return self._lock_service.is_locked
    
    @locked.setter
    def locked(self, value: bool):
        if value:
            self._lock_service.lock(manual=False)
        else:
            self._lock_service.unlock(manual=False)

    @property
    def clicker_running(self) -> bool:
        return self._clicker_service.is_running

    def _get_active_clicker_profile(self) -> Dict[str, Any]:
        """Return the active clicker profile from settings."""
        return self.settings.get_active_clicker_profile()

    def _on_clicker_runtime_changed(self) -> None:
        """Refresh UI elements affected by clicker runtime state."""
        self._update_simple_info()
        self._update_clicker_button()
        self._update_tray_meta()

    def _notify_clicker_started(self, profile: Dict[str, Any]) -> None:
        """Show the clicker-started notification."""
        mode_text = self.i18n.t(
            CLICKER_TRIGGER_MODES.get(profile.get("triggers", {}).get("mode", "toggle"), ""),
            profile.get("triggers", {}).get("mode", "toggle"),
        )
        self._notify(
            self.i18n.t("clicker.started.detail", "Auto clicker started: {0} ({1})").format(
                profile.get("name", ""),
                mode_text,
            )
        )

    def _notify_clicker_stopped(self, profile: Dict[str, Any]) -> None:
        """Show the clicker-stopped notification."""
        self._notify(
            self.i18n.t("clicker.stopped.detail", "Auto clicker stopped: {0}").format(
                profile.get("name", "")
            )
        )

    def _notify_locked(self) -> None:
        """Show the locked notification."""
        self._notify(self.i18n.t("locked.message", "Locked to screen center"))

    def _notify_unlocked(self) -> None:
        """Show the unlocked notification."""
        self._notify(self.i18n.t("unlocked.message", "Unlocked"))

    def _handle_lock_service_error(self, operation: str, exc: BaseException) -> None:
        """Surface lock-service errors through the GUI."""
        title = self.i18n.t("error", "Error")
        if operation == "lock":
            message = self.i18n.t("lock.failed", "Failed to lock: {}").format(str(exc))
        else:
            message = self.i18n.t("unlock.failed", "Failed to unlock: {}").format(str(exc))
        QtWidgets.QMessageBox.critical(self, title, message)

    def _build_hotkey_conflict_details(self, errors: list[str]) -> str:
        """Build a diagnostic message for hotkey registration conflicts."""
        lines = [
            self.i18n.t("hotkey.register.fail", "Some hotkeys could not be registered:"),
            self.i18n.t(
                "hotkey.conflict.which",
                "The following hotkeys are conflicting:"
            ),
        ]
        lines.extend(errors)
        lines.append("")
        lines.append(self.i18n.t(
            "hotkey.conflict.help",
            "Windows cannot directly tell which app owns a conflicting global hotkey. The list below shows visible apps you can try closing or changing hotkeys for:"
        ))

        seen_processes = set()
        for _hwnd, title, process_name in enumerate_visible_windows():
            key = (process_name or "", title or "")
            if key in seen_processes:
                continue
            seen_processes.add(key)
            if len(seen_processes) > 30:
                break
            lines.append(f"- {process_name or 'unknown.exe'} | {title or '(untitled)'}")
        return "\n".join(lines)

    def _notify(self, message: str, timeout_ms: int = 2000) -> None:
        """Show a Windows notification using the configured fallback chain."""
        if self._tray_service is not None:
            self._tray_service.show_notification(
                self.i18n.t("app.title", "Mouse Center Lock"),
                message,
                QtWidgets.QSystemTrayIcon.Information,
                timeout_ms,
            )
        elif hasattr(self, "_tray_service") and self._tray_service is not None:
            self._tray_service.tray.showMessage(
                self.i18n.t("app.title", "Mouse Center Lock"),
                message,
                QtWidgets.QSystemTrayIcon.Information,
                timeout_ms,
            )

    def _show_operation_error(self, title: str, message: str, details: Optional[str] = None) -> None:
        """Show a visible error dialog and append the details to the runtime log."""
        full_message = message if not details else f"{message}\n\n{details}"
        log_message(f"{title}: {full_message}")
        QtWidgets.QMessageBox.critical(self, title, full_message)

    def _save_settings_or_warn(self, context: str) -> bool:
        """Persist settings and show/log a clear error if writing fails."""
        if self.settings.save():
            return True
        details = self.settings.last_error or self.i18n.t("error.unknown", "Unknown error")
        self._show_operation_error(
            self.i18n.t("error", "Error"),
            self.i18n.t("settings.save.failed", "Failed to save settings."),
            f"{context}\n{details}\n{get_log_path()}",
        )
        return False

    def _set_startup_or_warn(self, enabled: bool) -> bool:
        """Apply startup registration and surface failures immediately."""
        success, error = set_startup_enabled(enabled)
        if success:
            return True
        self._show_operation_error(
            self.i18n.t("error", "Error"),
            self.i18n.t("startup.update.failed", "Failed to update startup registration."),
            f"{error or self.i18n.t('error.unknown', 'Unknown error')}\n{get_log_path()}",
        )
        return False

    def _register_hotkeys_or_warn(self, errors: list[str]) -> None:
        """Show and log hotkey registration failures."""
        detail = self._build_hotkey_conflict_details(errors)
        log_message(f"Hotkey registration failed:\n{detail}")
        QtWidgets.QMessageBox.warning(
            self,
            self.i18n.t("hotkey.conflict", "Hotkey Conflict"),
            detail,
        )

    def activate_from_external_request(self) -> None:
        """Bring the existing window to the front when another instance requests activation."""
        if self.isMinimized():
            self.showNormal()
        if not self.isVisible():
            self.show()
        self.raise_()
        self.activateWindow()
        self.setWindowState((self.windowState() & ~QtCore.Qt.WindowMinimized) | QtCore.Qt.WindowActive)

    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle(self.i18n.t("app.title", "Mouse Center Lock"))
        self.setMinimumSize(450, 500)
        self.resize(550, 700)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        
        # Load window icon
        self._custom_icon = self._load_external_icon()
        icon = self._custom_icon or self._make_icon(False)
        QtWidgets.QApplication.setWindowIcon(icon)
        self.setWindowIcon(icon)
    
    def _setup_timers(self):
        """Setup timers for recentering and window focus checking."""
        pass

    def _schedule_live_apply(self):
        """Debounce settings persistence so advanced-page edits take effect immediately."""
        if self._suspend_live_apply > 0:
            return
        self._live_apply_timer.start(120)

    def _apply_live_settings(self):
        """Apply settings after the debounce window."""
        if self._suspend_live_apply > 0:
            return
        self._on_apply(show_feedback=False)

    def _begin_form_update(self):
        """Prevent live-apply recursion while populating widgets."""
        self._suspend_live_apply += 1

    def _end_form_update(self):
        """Resume live apply after populating widgets."""
        if self._suspend_live_apply > 0:
            self._suspend_live_apply -= 1
    
    def _build_ui(self):
        """Build the main UI."""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Mode tabs
        self.modeTabs = QtWidgets.QTabBar()
        self.modeTabs.addTab(self.i18n.t("mode.simple", "Simple"))
        self.modeTabs.addTab(self.i18n.t("mode.advanced", "Advanced"))
        self.modeTabs.currentChanged.connect(self._on_mode_changed)
        layout.addWidget(self.modeTabs)
        
        # Stacked pages
        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self._build_simple_page())
        self.stack.addWidget(self._build_advanced_page())
        layout.addWidget(self.stack)
    
    def _build_simple_page(self) -> QtWidgets.QWidget:
        """Build the simple mode page."""
        return build_simple_page(self)
    
    def _build_advanced_page(self) -> QtWidgets.QWidget:
        """Build the advanced settings page."""
        return build_advanced_page(self)
    
    def _section_label(self, text: str) -> QtWidgets.QLabel:
        """Backward-compatible wrapper for shared section labels."""
        from ui.pages.common import create_section_label
        return create_section_label(text)
    
    def _build_info_card(self, title: str) -> QtWidgets.QFrame:
        """Backward-compatible wrapper for shared info cards."""
        from ui.pages.common import create_info_card
        return create_info_card(title)
    
    def _pick_process(self):
        """Open process picker dialog."""
        dialog = ProcessPickerDialog(self, self.i18n)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            selected = dialog.get_selected_process()
            if selected:
                self.manualInputEdit.setText(selected)

    def _open_window_resize(self):
        """Open window resize & center dialog."""
        dialog = WindowResizeDialog(self, self.i18n)
        dialog.exec()

    def _add_target_window(self):
        """Add current input to target list."""
        text = self.manualInputEdit.text().strip()
        if not text:
            return
            
        # Check for duplicates
        items = [self.targetList.item(i).text() for i in range(self.targetList.count())]
        if text in items:
            return
            
        self.targetList.addItem(text)
        self.manualInputEdit.clear()
        self._schedule_live_apply()

    def _remove_target_window(self):
        """Remove selected item from target list."""
        row = self.targetList.currentRow()
        if row >= 0:
            self.targetList.takeItem(row)
            self._schedule_live_apply()

    def _current_profile_form_data(self) -> Dict[str, Any]:
        """Build a clicker profile from the current form controls."""
        return collect_clicker_profile_form_data(self)

    def _current_general_settings_form_data(self) -> Dict[str, Any]:
        """Build a general settings payload from the current form controls."""
        return collect_general_settings_form_data(self)

    def _load_profile_into_form(self, profile: Dict[str, Any]) -> None:
        """Populate clicker controls from a profile."""
        load_clicker_profile_into_form(self, profile)

    def _refresh_clicker_ui(self) -> None:
        """Refresh UI fragments that depend on clicker profile state."""
        self._update_clicker_button()
        self._update_simple_info()
        self._update_tray_meta()

    def _show_saved_tooltip(self) -> None:
        """Show the standard saved tooltip near the cursor."""
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), self.i18n.t("saved", "Settings saved"), self)

    def _reregister_hotkeys(self) -> None:
        """Re-register global hotkeys after profile-affecting changes."""
        unregister_hotkeys()
        success, errors = register_hotkeys(self.settings.data)
        if not success:
            self._register_hotkeys_or_warn(errors)

    def _refresh_all_runtime_ui(self) -> None:
        """Refresh UI fragments affected by settings apply."""
        self._update_toggle_button()
        self._update_clicker_button()
        self._update_simple_info()
        self._update_tray_meta()

    def _populate_clicker_profiles(self) -> None:
        """Refresh the profile combo box from settings."""
        if not hasattr(self, "clickerProfileCombo"):
            return

        current_id = self.settings.data.get("activeClickerProfileId", self._selected_profile_id)
        self.clickerProfileCombo.blockSignals(True)
        self.clickerProfileCombo.clear()
        profiles = self.settings.get_clicker_profiles()
        target_index = 0
        for profile in profiles:
            self.clickerProfileCombo.addItem(
                profile.get("name", self.i18n.t("clicker.profile.defaultName", "Default Profile")),
                profile.get("id"),
            )
        for i in range(self.clickerProfileCombo.count()):
            if self.clickerProfileCombo.itemData(i) == current_id:
                target_index = i
                break
        self.clickerProfileCombo.setCurrentIndex(target_index)
        self.clickerProfileCombo.blockSignals(False)
        active = self.settings.set_active_clicker_profile(current_id)
        self._load_profile_into_form(active)

    def _on_clicker_profile_selected(self, _index: int) -> None:
        """Switch the active clicker profile."""
        if self._suspend_live_apply > 0:
            return
        profile_id = self.clickerProfileCombo.currentData()
        active = self._clicker_profile_controller.select_profile(
            profile_id,
            clicker_running=self.clicker_running,
        )
        if active is None:
            return
        self._reregister_hotkeys()

    def _save_clicker_profile(self) -> None:
        """Save the currently edited clicker profile."""
        profile = self._clicker_profile_controller.save_profile(self._current_profile_form_data())
        if profile is None:
            return
        self._selected_profile_id = profile.get("id", "default")
        self._profile_dirty = False
        self._reregister_hotkeys()

    def _create_clicker_profile(self) -> None:
        """Create a new clicker profile based on the current editor state."""
        profile = self._clicker_profile_controller.create_profile(
            self.clickerProfileNameEdit.text().strip(),
            self._current_profile_form_data(),
        )
        if profile is None:
            return
        self._selected_profile_id = profile.get("id", "default")
        self._reregister_hotkeys()

    def _delete_clicker_profile(self) -> None:
        """Delete the currently selected clicker profile."""
        active = self._get_active_clicker_profile()
        new_active = self._clicker_profile_controller.delete_profile(
            active.get("id", "default"),
            clicker_running=self.clicker_running,
        )
        if new_active is None:
            return
        self._selected_profile_id = new_active.get("id", "default")
        self._reregister_hotkeys()

    def _browse_clicker_sound_file(self) -> None:
        """Select a custom start-sound file."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.i18n.t("clicker.sound.path.title", "Select Audio File"),
            "",
            self.i18n.t("clicker.sound.path.filter", "Audio Files (*.wav *.mp3 *.ogg *.flac);;All Files (*.*)"),
        )
        if path:
            self.clickerCustomSoundPathEdit.setText(path)
            for i in range(self.clickerSoundPresetCombo.count()):
                if self.clickerSoundPresetCombo.itemData(i) == "custom":
                    self.clickerSoundPresetCombo.setCurrentIndex(i)
                    break
            self._sync_clicker_sound_controls()
            self._schedule_live_apply()

    def _preview_clicker_sound(self) -> None:
        """Preview the currently selected clicker start sound."""
        sound_config = {
            "enabled": True,
            "preset": self.clickerSoundPresetCombo.currentData() or "systemAsterisk",
            "customFile": self.clickerCustomSoundPathEdit.text().strip(),
        }
        self._clicker_service.play_sound_preview(sound_config)

    def _sync_clicker_trigger_controls(self):
        """Only show trigger inputs relevant to the selected trigger mode."""
        mode = self.clickerTriggerModeCombo.currentData() or "toggle"
        toggle_visible = mode == "toggle"
        hold_key_visible = mode == "holdKey"
        hold_mouse_visible = mode == "holdMouseButton"
        self.clickerToggleHotkeyLabel.setVisible(toggle_visible)
        self.clickerToggleHotkeyCapture.setVisible(toggle_visible)
        self.clickerHoldKeyLabel.setVisible(hold_key_visible)
        self.clickerHoldKeyCapture.setVisible(hold_key_visible)
        self.clickerHoldMouseLabel.setVisible(hold_mouse_visible)
        self.clickerHoldMouseCombo.setVisible(hold_mouse_visible)
        self._update_clicker_button()
        self._update_simple_info()

    def _sync_clicker_sound_controls(self):
        """Show the custom sound path only for custom-file mode."""
        preset = self.clickerSoundPresetCombo.currentData() or "systemAsterisk"
        use_custom = preset == "custom"
        enabled = self.clickerSoundEnabledCheck.isChecked()
        self.clickerSoundPresetLabel.setEnabled(enabled)
        self.clickerSoundPresetCombo.setEnabled(enabled)
        self.clickerSoundPreviewBtn.setEnabled(enabled)
        self.clickerCustomSoundPathEdit.setVisible(enabled and use_custom)
        self.clickerCustomSoundBrowseBtn.setVisible(enabled and use_custom)
    
    def _on_apply(self, show_feedback: bool = True):
        """Apply and save settings."""
        startup_updated = self._settings_apply_controller.apply(show_feedback=show_feedback)
        if not startup_updated:
            self.startupCheck.blockSignals(True)
            self.startupCheck.setChecked(is_startup_enabled())
            self.startupCheck.blockSignals(False)

    def _on_mode_changed(self, idx: int):
        """Handle mode tab change."""
        self.stack.setCurrentIndex(idx)
    
    # --- Lock/Unlock Logic ---
    def lock(self, manual: bool = False):
        """Lock the cursor to target position."""
        self._lock_service.lock(manual=manual)

    def unlock(self, manual: bool = False):
        """Unlock the cursor."""
        self._lock_service.unlock(manual=manual)
    
    def toggle_lock(self):
        """Toggle lock state."""
        self._lock_service.toggle()
    
    def _on_lock_state_changed(self):
        """Called when lock state changes."""
        self._update_status_badge()
        self._update_simple_info()
        self._update_toggle_button()
        self._update_clicker_button()
        self._update_tray_icon()
        self._update_tray_meta()

    def _apply_clicker_timer(self):
        """Compatibility wrapper for clicker runtime updates."""
        self._clicker_service.sync_runtime()

    def start_clicker(self, show_message: bool = True, immediate_click: bool = False):
        """Start the auto clicker."""
        self._clicker_service.start(show_message=show_message, immediate_click=immediate_click)

    def stop_clicker(self, show_message: bool = True):
        """Stop the auto clicker."""
        self._clicker_service.stop(show_message=show_message)

    def toggle_clicker(self):
        """Toggle the auto clicker."""
        self._clicker_service.toggle()
    
    # --- UI Updates ---
    def _update_status_badge(self):
        """Update the status badge appearance."""
        text, style = build_status_badge_presentation(
            self.i18n,
            locked=self.locked,
            is_force_lock=self._lock_service.is_force_lock,
            auto_lock_suspended=self._lock_service.auto_lock_suspended,
            window_specific=self.settings.data.get("windowSpecific", {}),
        )
        self.statusBadge.setText(text)
        self.statusBadge.setStyleSheet(style)

    def _update_simple_info(self):
        """Update simple mode information cards."""
        if not hasattr(self, "configLabel") or not hasattr(self, "hotkeysLabel"):
            return

        config_text, hotkeys_text = build_simple_info_text(
            self.i18n,
            settings_data=self.settings.data,
            clicker=self._get_active_clicker_profile(),
            clicker_running=self.clicker_running,
            clicker_presets=CLICKER_PRESETS,
            clicker_trigger_modes=CLICKER_TRIGGER_MODES,
        )
        self.configLabel.setText(config_text)
        self.hotkeysLabel.setText(hotkeys_text)
    
    def _update_toggle_button(self):
        """Update the toggle button text."""
        self.toggleBtn.setText(
            build_toggle_button_text(
                self.i18n,
                locked=self.locked,
                hotkeys=self.settings.data["hotkeys"],
            )
        )

    def _get_clicker_preset_for_interval(self, interval_ms: int) -> str:
        """Resolve the current interval to a preset key when possible."""
        return resolve_clicker_preset(interval_ms, CLICKER_PRESETS)

    def _describe_clicker_preset(self, preset_key: str, interval_ms: int) -> str:
        """Return a short descriptive label for the clicker preset."""
        return describe_clicker_preset(self.i18n, preset_key)

    def _sync_clicker_interval_controls(self):
        """Show the custom interval editor only for the custom preset."""
        if not hasattr(self, "clickerPresetCombo"):
            return

        preset_key = self.clickerPresetCombo.currentData() or "custom"
        interval_ms = self.clickerIntervalSpin.value() if hasattr(self, "clickerIntervalSpin") else 100
        is_custom = preset_key == "custom"

        if hasattr(self, "clickerIntervalLabel"):
            self.clickerIntervalLabel.setVisible(is_custom)
        if hasattr(self, "clickerIntervalSpin"):
            self.clickerIntervalSpin.setVisible(is_custom)
            self.clickerIntervalSpin.setEnabled(is_custom)
        if hasattr(self, "clickerPresetHint"):
            self.clickerPresetHint.setText(self._describe_clicker_preset(preset_key, interval_ms))

    def _on_clicker_preset_changed(self, _index: int = -1):
        """Apply preset interval values and refresh the UI."""
        preset_key = self.clickerPresetCombo.currentData() or "custom"
        preset_interval = CLICKER_PRESETS.get(preset_key)
        if preset_interval is not None:
            self.clickerIntervalSpin.setValue(preset_interval)
        self._sync_clicker_interval_controls()
        self._schedule_live_apply()

    def _update_clicker_button(self):
        """Update the auto clicker button text and enabled state."""
        if not hasattr(self, "clickerBtn"):
            return

        text, enabled = build_clicker_button_presentation(
            self.i18n,
            clicker=self._get_active_clicker_profile(),
            clicker_running=self.clicker_running,
        )
        self.clickerBtn.setText(text)
        self.clickerBtn.setEnabled(enabled)
    
    # --- Theme ---
    def _apply_theme(self):
        """Apply the current theme."""
        theme = self.settings.data.get("theme", "dark")
        self._theme_service.apply(self, theme)
    
    # --- System Tray ---
    def _create_tray(self):
        """Create system tray icon and menu."""
        base_icon = self._custom_icon or QtGui.QIcon()
        self._tray_service = TrayService(
            parent=self,
            base_icon=base_icon,
            dynamic_icon_factory=self._make_icon,
            i18n=self.i18n,
            get_locked=lambda: self.locked,
            get_clicker_running=lambda: self.clicker_running,
            get_clicker_profile=self._get_active_clicker_profile,
            get_hotkeys=lambda: self.settings.data["hotkeys"],
            on_toggle_lock=self.toggle_lock,
            on_lock=lambda: self.lock(manual=True),
            on_unlock=lambda: self.unlock(manual=True),
            on_toggle_clicker=self.toggle_clicker,
            on_show_window=self._show_from_tray,
            on_quit=self._quit,
        )
    
    def _make_icon(self, locked: bool) -> QtGui.QIcon:
        """Create a programmatic icon."""
        size = 128
        pm = QtGui.QPixmap(size, size)
        pm.fill(QtCore.Qt.transparent)
        
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # Background circle
        color = QtGui.QColor(46, 204, 113) if locked else QtGui.QColor(10, 132, 255)
        p.setBrush(color)
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(0, 0, size, size)
        
        # Lock body
        pad = 28
        body = QtCore.QRect(pad, pad + 18, size - 2*pad, size - 2*pad - 18)
        p.setBrush(QtGui.QColor(255, 255, 255))
        p.drawRoundedRect(body, 14, 14)
        
        # Shackle
        pen = QtGui.QPen(QtGui.QColor(255, 255, 255))
        pen.setWidth(14)
        p.setPen(pen)
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawArc(size//2 - 30, pad - 6, 60, 48, 0, 180*16)
        
        p.end()
        return QtGui.QIcon(pm)
    
    def _load_external_icon(self) -> Optional[QtGui.QIcon]:
        """Try to load external icon file."""
        candidates = [
            os.path.join(ASSETS_DIR, "app.ico"),
            os.path.join(ASSETS_DIR, "icon.ico"),
            os.path.join(ASSETS_DIR, "app.png"),
            os.path.join(RUN_DIR, "app.ico"),
        ]
        
        for path in candidates:
            if os.path.exists(path):
                icon = QtGui.QIcon(path)
                if not icon.isNull():
                    return icon
        return None
    
    def _update_tray_icon(self):
        """Update tray icon based on lock state."""
        if self._tray_service is not None:
            self._tray_service.refresh_icon()
    
    def _update_tray_meta(self):
        """Update tray menu information."""
        if self._tray_service is not None:
            self._tray_service.refresh()
    
    def _show_from_tray(self):
        """Show window from tray."""
        self.activate_from_external_request()
    
    def _quit(self):
        """Quit the application."""
        try:
            self.stop_clicker(show_message=False)
            self._lock_service.release_cursor()
        finally:
            unregister_hotkeys()
            release_single_instance()
            QtWidgets.QApplication.quit()
    
    def _reset_close_action(self):
        """Reset the close action to 'ask'."""
        self.settings.data["closeAction"] = "ask"
        if not self._save_settings_or_warn("Resetting close action"):
            return
        QtWidgets.QMessageBox.information(
            self,
            self.i18n.t("settings.reset", "Settings Reset"),
            self.i18n.t("close.action.reset.done", "Close behavior has been reset to 'Ask every time'.")
        )

    def closeEvent(self, event):
        """Handle window close - minimize to tray or quit."""
        # Shift+Close always quits
        if QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier:
            event.accept()
            self._quit()
            return

        action = self.settings.data.get("closeAction", "ask")
        
        if action == "ask":
            dialog = CloseActionDialog(self, self.i18n)
            if dialog.exec() == QtWidgets.QDialog.Accepted:
                if dialog.action == "minimize":
                    event.ignore()
                    self.hide()
                    self._notify(self.i18n.t("tray.minimized", "Minimized to tray."))
                elif dialog.action == "quit":
                    event.accept()
                    self._quit()
                
                if dialog.dont_ask_again and dialog.action:
                    self.settings.data["closeAction"] = dialog.action
                    if not self._save_settings_or_warn("Saving close action preference"):
                        self.settings.data["closeAction"] = "ask"
            else:
                # Cancelled
                event.ignore()
        elif action == "minimize":
            event.ignore()
            self.hide()
        elif action == "quit":
            event.accept()
            self._quit()
