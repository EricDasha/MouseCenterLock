"""
Custom widgets for MouseCenterLock.
Includes Minecraft-style hotkey capture input and enhanced process picker.
"""
from PySide6 import QtCore, QtGui, QtWidgets
from typing import Optional, Dict, Any, Callable


class HotkeyCapture(QtWidgets.QLineEdit):
    """
    Minecraft-style hotkey capture input.
    Click to focus, then press any key combination to capture it.
    """
    
    hotkeyChanged = QtCore.Signal(dict)  # Emits the new hotkey config
    
    def __init__(self, parent=None, i18n=None):
        super().__init__(parent)
        self.i18n = i18n
        self._hotkey_config: Dict[str, Any] = {
            "modCtrl": False,
            "modAlt": False,
            "modShift": False,
            "modWin": False,
            "key": ""
        }
        self._is_capturing = False
        
        self.setReadOnly(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._update_display()
        self._apply_style(False)
    
    def _get_text(self, key: str, fallback: str) -> str:
        """Get translated text or fallback."""
        if self.i18n:
            return self.i18n.t(key, fallback)
        return fallback
    
    def _apply_style(self, capturing: bool):
        """Apply visual style based on capture state."""
        if capturing:
            self.setStyleSheet("""
                QLineEdit {
                    background: #3a3a4a;
                    border: 2px solid #0a84ff;
                    border-radius: 6px;
                    padding: 8px 12px;
                    color: #ffd700;
                    font-weight: bold;
                }
            """)
        else:
            self.setStyleSheet("""
                QLineEdit {
                    background: #2c2c2e;
                    border: 2px solid #48484a;
                    border-radius: 6px;
                    padding: 8px 12px;
                    color: #ebebf5;
                }
                QLineEdit:hover {
                    border-color: #0a84ff;
                }
            """)
    
    def set_hotkey(self, config: Dict[str, Any]):
        """Set the current hotkey configuration."""
        self._hotkey_config = {
            "modCtrl": config.get("modCtrl", False),
            "modAlt": config.get("modAlt", False),
            "modShift": config.get("modShift", False),
            "modWin": config.get("modWin", False),
            "key": config.get("key", "")
        }
        self._update_display()
    
    def get_hotkey(self) -> Dict[str, Any]:
        """Get the current hotkey configuration."""
        return self._hotkey_config.copy()
    
    def _update_display(self):
        """Update the displayed text based on current config."""
        if self._is_capturing:
            self.setText(self._get_text("hotkey.capture.hint", "Press keys..."))
            return
        
        parts = []
        if self._hotkey_config.get("modCtrl"):
            parts.append("Ctrl")
        if self._hotkey_config.get("modAlt"):
            parts.append("Alt")
        if self._hotkey_config.get("modShift"):
            parts.append("Shift")
        if self._hotkey_config.get("modWin"):
            parts.append("Win")
        
        key = self._hotkey_config.get("key", "")
        if key:
            parts.append(key)
        
        if parts:
            self.setText(" + ".join(parts))
        else:
            self.setText(self._get_text("hotkey.capture.click", "Click to set..."))
    
    def mousePressEvent(self, event):
        """Start capturing when clicked."""
        if event.button() == QtCore.Qt.LeftButton:
            self._start_capture()
        super().mousePressEvent(event)
    
    def _start_capture(self):
        """Enter capture mode."""
        self._is_capturing = True
        self._apply_style(True)
        self._update_display()
        self.setFocus()
    
    def _stop_capture(self):
        """Exit capture mode."""
        self._is_capturing = False
        self._apply_style(False)
        self._update_display()
    
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Capture key press events."""
        if not self._is_capturing:
            return
        
        key = event.key()
        modifiers = event.modifiers()
        
        # Ignore if only modifier keys are pressed
        modifier_keys = {
            QtCore.Qt.Key_Control, QtCore.Qt.Key_Alt, 
            QtCore.Qt.Key_Shift, QtCore.Qt.Key_Meta
        }
        if key in modifier_keys:
            # Update display with current modifiers but don't finalize
            temp_config = {
                "modCtrl": bool(modifiers & QtCore.Qt.ControlModifier),
                "modAlt": bool(modifiers & QtCore.Qt.AltModifier),
                "modShift": bool(modifiers & QtCore.Qt.ShiftModifier),
                "modWin": bool(modifiers & QtCore.Qt.MetaModifier),
                "key": "..."
            }
            self._show_temp_config(temp_config)
            return
        
        # Escape cancels capture
        if key == QtCore.Qt.Key_Escape:
            self._stop_capture()
            return
        
        # Convert Qt key to our key string
        key_str = self._qt_key_to_string(key)
        if not key_str:
            return  # Unsupported key
        
        # Build the new config
        new_config = {
            "modCtrl": bool(modifiers & QtCore.Qt.ControlModifier),
            "modAlt": bool(modifiers & QtCore.Qt.AltModifier),
            "modShift": bool(modifiers & QtCore.Qt.ShiftModifier),
            "modWin": bool(modifiers & QtCore.Qt.MetaModifier),
            "key": key_str
        }
        
        # Check if hotkey is too simple (no modifier)
        has_modifier = any([
            new_config["modCtrl"], new_config["modAlt"],
            new_config["modShift"], new_config["modWin"]
        ])
        
        if not has_modifier:
            # Show warning dialog but still allow the setting
            reply = QtWidgets.QMessageBox.warning(
                self.window() if self.window() else None,
                self._get_text("hotkey.simple.title", "Simple Hotkey Warning"),
                self._get_text("hotkey.simple.message", 
                    "Setting a hotkey without Ctrl/Alt/Shift/Win may interfere with normal keyboard use.\n\n"
                    "Are you sure you want to use this hotkey?"),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                self._stop_capture()
                return
        
        self._hotkey_config = new_config
        self._stop_capture()
        self.hotkeyChanged.emit(new_config)
    
    def _show_temp_config(self, config: Dict[str, Any]):
        """Show temporary config while capturing."""
        parts = []
        if config.get("modCtrl"):
            parts.append("Ctrl")
        if config.get("modAlt"):
            parts.append("Alt")
        if config.get("modShift"):
            parts.append("Shift")
        if config.get("modWin"):
            parts.append("Win")
        parts.append(config.get("key", "..."))
        self.setText(" + ".join(parts))
    
    def _qt_key_to_string(self, key: int) -> Optional[str]:
        """Convert Qt key code to our key string format."""
        # Letters A-Z
        if QtCore.Qt.Key_A <= key <= QtCore.Qt.Key_Z:
            return chr(key)
        
        # Numbers 0-9
        if QtCore.Qt.Key_0 <= key <= QtCore.Qt.Key_9:
            return chr(key)
        
        # Function keys F1-F24
        if QtCore.Qt.Key_F1 <= key <= QtCore.Qt.Key_F24:
            return f"F{key - QtCore.Qt.Key_F1 + 1}"
        
        # Other common keys
        key_map = {
            QtCore.Qt.Key_Space: "Space",
            QtCore.Qt.Key_Tab: "Tab",
            QtCore.Qt.Key_Return: "Enter",
            QtCore.Qt.Key_Backspace: "Backspace",
            QtCore.Qt.Key_Delete: "Delete",
            QtCore.Qt.Key_Insert: "Insert",
            QtCore.Qt.Key_Home: "Home",
            QtCore.Qt.Key_End: "End",
            QtCore.Qt.Key_PageUp: "PageUp",
            QtCore.Qt.Key_PageDown: "PageDown",
            QtCore.Qt.Key_Up: "Up",
            QtCore.Qt.Key_Down: "Down",
            QtCore.Qt.Key_Left: "Left",
            QtCore.Qt.Key_Right: "Right",
        }
        
        return key_map.get(key)
    
    def focusOutEvent(self, event):
        """Stop capturing when focus is lost."""
        if self._is_capturing:
            self._stop_capture()
        super().focusOutEvent(event)


class ProcessPickerDialog(QtWidgets.QDialog):
    """
    Enhanced process picker dialog with search functionality.
    Similar to Cheat Engine's process list.
    """
    
    def __init__(self, parent=None, i18n=None):
        super().__init__(parent)
        self.i18n = i18n
        self.selected_process: Optional[str] = None
        self._all_processes = []
        
        self._setup_ui()
        self._apply_style()
        self.refresh_processes()
    
    def _t(self, key: str, fallback: str) -> str:
        """Get translated text."""
        if self.i18n:
            return self.i18n.t(key, fallback)
        return fallback
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle(self._t("process.picker.title", "Select Process"))
        self.setMinimumSize(500, 400)
        self.resize(550, 450)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header label
        header = QtWidgets.QLabel(self._t("process.picker.label", "Select a process to lock the mouse to:"))
        header.setStyleSheet("font-size: 14px; font-weight: 500;")
        layout.addWidget(header)
        
        # Search box
        search_layout = QtWidgets.QHBoxLayout()
        self.searchBox = QtWidgets.QLineEdit()
        self.searchBox.setPlaceholderText(self._t("process.picker.search", "Search..."))
        self.searchBox.textChanged.connect(self._filter_list)
        self.searchBox.setClearButtonEnabled(True)
        search_layout.addWidget(self.searchBox)
        
        self.refreshBtn = QtWidgets.QPushButton(self._t("process.picker.refresh", "Refresh"))
        self.refreshBtn.clicked.connect(self.refresh_processes)
        self.refreshBtn.setFixedWidth(80)
        search_layout.addWidget(self.refreshBtn)
        layout.addLayout(search_layout)
        
        # Process list
        self.processList = QtWidgets.QListWidget()
        self.processList.setAlternatingRowColors(True)
        self.processList.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.processList)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        self.okBtn = QtWidgets.QPushButton(self._t("process.picker.ok", "OK"))
        self.okBtn.setFixedWidth(80)
        self.okBtn.clicked.connect(self.accept)
        
        self.cancelBtn = QtWidgets.QPushButton(self._t("process.picker.cancel", "Cancel"))
        self.cancelBtn.setFixedWidth(80)
        self.cancelBtn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.okBtn)
        button_layout.addWidget(self.cancelBtn)
        layout.addLayout(button_layout)
    
    def _apply_style(self):
        """Apply dialog styling."""
        self.setStyleSheet("""
            QDialog {
                background: #1c1c1e;
            }
            QLabel {
                color: #ebebf5;
            }
            QLineEdit {
                background: #2c2c2e;
                border: 1px solid #48484a;
                border-radius: 6px;
                padding: 8px;
                color: #ebebf5;
            }
            QLineEdit:focus {
                border-color: #0a84ff;
            }
            QListWidget {
                background: #2c2c2e;
                border: 1px solid #48484a;
                border-radius: 6px;
                color: #ebebf5;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3a3a3c;
            }
            QListWidget::item:selected {
                background: #0a84ff;
            }
            QListWidget::item:alternate {
                background: #252527;
            }
            QPushButton {
                background: #0a84ff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
            }
            QPushButton:hover {
                background: #2b95ff;
            }
            QPushButton:pressed {
                background: #0671dd;
            }
        """)
    
    def refresh_processes(self):
        """Refresh the process list."""
        self.processList.clear()
        self._all_processes = []
        
        try:
            from win_api import enumerate_visible_windows
            windows = enumerate_visible_windows()
            
            for hwnd, title, proc_name in windows:
                self._all_processes.append({
                    "hwnd": hwnd,
                    "title": title,
                    "process": proc_name
                })
                
                item = QtWidgets.QListWidgetItem(f"{title}")
                item.setToolTip(f"{proc_name}\n{title}")
                item.setData(QtCore.Qt.UserRole, title)
                item.setData(QtCore.Qt.UserRole + 1, hwnd)
                self.processList.addItem(item)
        except Exception as e:
            error_item = QtWidgets.QListWidgetItem(f"Error loading processes: {e}")
            self.processList.addItem(error_item)
    
    def _filter_list(self, text: str):
        """Filter the process list based on search text."""
        search_lower = text.lower()
        
        for i in range(self.processList.count()):
            item = self.processList.item(i)
            if search_lower:
                # Check both title and tooltip (which contains process name)
                visible = (search_lower in item.text().lower() or 
                          search_lower in (item.toolTip() or "").lower())
                item.setHidden(not visible)
            else:
                item.setHidden(False)
    
    def get_selected_process(self) -> Optional[str]:
        """Get the selected window title."""
        item = self.processList.currentItem()
        if item:
            return item.data(QtCore.Qt.UserRole)
        return None
    
    def get_selected_hwnd(self) -> Optional[int]:
        """Get the selected window handle."""
        item = self.processList.currentItem()
        if item:
            return item.data(QtCore.Qt.UserRole + 1)
        return None
    
    def accept(self):
        """Handle OK button."""
        self.selected_process = self.get_selected_process()
        if self.selected_process:
            super().accept()
