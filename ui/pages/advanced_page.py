"""
Advanced page builder.
"""
from PySide6 import QtCore, QtWidgets

from widgets import HotkeyCapture
from ui.pages.common import create_section_label
from win_api import is_startup_enabled


def build_advanced_page(window) -> QtWidgets.QWidget:
    """Build the advanced settings page and attach widgets to the window."""
    page = QtWidgets.QWidget()

    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

    content = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(content)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(16)

    layout.addWidget(create_section_label(window.i18n.t("section.hotkeys", "Hotkeys")))

    hotkey_grid = QtWidgets.QGridLayout()
    hotkey_grid.setSpacing(12)

    hotkey_grid.addWidget(QtWidgets.QLabel(window.i18n.t("hotkey.lock", "Lock")), 0, 0)
    window.lockHotkeyCapture = HotkeyCapture(i18n=window.i18n)
    window.lockHotkeyCapture.set_hotkey(window.settings.data["hotkeys"]["lock"])
    window.lockHotkeyCapture.hotkeyChanged.connect(lambda _cfg: window._schedule_live_apply())
    hotkey_grid.addWidget(window.lockHotkeyCapture, 0, 1)

    hotkey_grid.addWidget(QtWidgets.QLabel(window.i18n.t("hotkey.unlock", "Unlock")), 1, 0)
    window.unlockHotkeyCapture = HotkeyCapture(i18n=window.i18n)
    window.unlockHotkeyCapture.set_hotkey(window.settings.data["hotkeys"]["unlock"])
    window.unlockHotkeyCapture.hotkeyChanged.connect(lambda _cfg: window._schedule_live_apply())
    hotkey_grid.addWidget(window.unlockHotkeyCapture, 1, 1)

    hotkey_grid.addWidget(QtWidgets.QLabel(window.i18n.t("hotkey.toggle", "Toggle")), 2, 0)
    window.toggleHotkeyCapture = HotkeyCapture(i18n=window.i18n)
    window.toggleHotkeyCapture.set_hotkey(window.settings.data["hotkeys"]["toggle"])
    window.toggleHotkeyCapture.hotkeyChanged.connect(lambda _cfg: window._schedule_live_apply())
    hotkey_grid.addWidget(window.toggleHotkeyCapture, 2, 1)

    hotkey_hint = QtWidgets.QLabel(
        window.i18n.t("clicker.hotkey.profileHint", "Auto clicker trigger keys are configured per clicker profile below.")
    )
    hotkey_hint.setWordWrap(True)
    hotkey_hint.setStyleSheet("color: rgba(142, 142, 147, 0.95); font-size: 12px;")
    hotkey_grid.addWidget(hotkey_hint, 3, 0, 1, 2)
    layout.addLayout(hotkey_grid)

    layout.addWidget(create_section_label(window.i18n.t("section.behavior", "Behavior")))

    window.recenterCheck = QtWidgets.QCheckBox(window.i18n.t("recenter.enabled", "Enable periodic recentering"))
    window.recenterCheck.setChecked(window.settings.data["recenter"].get("enabled", True))
    window.recenterCheck.toggled.connect(lambda _checked: window._schedule_live_apply())
    layout.addWidget(window.recenterCheck)

    interval_layout = QtWidgets.QHBoxLayout()
    interval_layout.addWidget(QtWidgets.QLabel(window.i18n.t("recenter.interval", "Interval (ms)")))
    window.recenterSpin = QtWidgets.QSpinBox()
    window.recenterSpin.setRange(16, 5000)
    window.recenterSpin.setSingleStep(16)
    window.recenterSpin.setValue(window.settings.data["recenter"].get("intervalMs", 250))
    window.recenterSpin.valueChanged.connect(lambda _value: window._schedule_live_apply())
    interval_layout.addWidget(window.recenterSpin)
    interval_layout.addStretch()
    layout.addLayout(interval_layout)

    layout.addWidget(create_section_label(window.i18n.t("clicker.section", "Auto Clicker")))

    profile_layout = QtWidgets.QHBoxLayout()
    profile_layout.addWidget(QtWidgets.QLabel(window.i18n.t("clicker.profile.select", "Profile")))
    window.clickerProfileCombo = QtWidgets.QComboBox()
    window.clickerProfileCombo.currentIndexChanged.connect(window._on_clicker_profile_selected)
    profile_layout.addWidget(window.clickerProfileCombo)
    layout.addLayout(profile_layout)

    profile_name_layout = QtWidgets.QHBoxLayout()
    profile_name_layout.addWidget(QtWidgets.QLabel(window.i18n.t("clicker.profile.name", "Profile Name")))
    window.clickerProfileNameEdit = QtWidgets.QLineEdit()
    window.clickerProfileNameEdit.setPlaceholderText(window.i18n.t("clicker.profile.placeholder", "Input a profile name"))
    window.clickerProfileNameEdit.textChanged.connect(lambda _text: window._schedule_live_apply())
    profile_name_layout.addWidget(window.clickerProfileNameEdit)
    layout.addLayout(profile_name_layout)

    profile_btn_layout = QtWidgets.QHBoxLayout()
    window.newClickerProfileBtn = QtWidgets.QPushButton(window.i18n.t("clicker.profile.new", "New"))
    window.newClickerProfileBtn.clicked.connect(window._create_clicker_profile)
    profile_btn_layout.addWidget(window.newClickerProfileBtn)
    window.saveClickerProfileBtn = QtWidgets.QPushButton(window.i18n.t("clicker.profile.save", "Save Profile"))
    window.saveClickerProfileBtn.clicked.connect(window._save_clicker_profile)
    profile_btn_layout.addWidget(window.saveClickerProfileBtn)
    window.deleteClickerProfileBtn = QtWidgets.QPushButton(window.i18n.t("clicker.profile.delete", "Delete"))
    window.deleteClickerProfileBtn.clicked.connect(window._delete_clicker_profile)
    profile_btn_layout.addWidget(window.deleteClickerProfileBtn)
    profile_btn_layout.addStretch()
    layout.addLayout(profile_btn_layout)

    window.clickerEnabledCheck = QtWidgets.QCheckBox(window.i18n.t("clicker.enabled", "Enable auto clicker"))
    window.clickerEnabledCheck.toggled.connect(lambda _checked: window._schedule_live_apply())
    layout.addWidget(window.clickerEnabledCheck)

    clicker_button_layout = QtWidgets.QHBoxLayout()
    clicker_button_layout.addWidget(QtWidgets.QLabel(window.i18n.t("clicker.button", "Click Button")))
    window.clickerButtonCombo = QtWidgets.QComboBox()
    window.clickerButtonCombo.addItem(window.i18n.t("clicker.button.left", "Left Click"), "left")
    window.clickerButtonCombo.addItem(window.i18n.t("clicker.button.right", "Right Click"), "right")
    window.clickerButtonCombo.addItem(window.i18n.t("clicker.button.middle", "Middle Click"), "middle")
    window.clickerButtonCombo.currentIndexChanged.connect(lambda _index: window._schedule_live_apply())
    clicker_button_layout.addWidget(window.clickerButtonCombo)
    clicker_button_layout.addStretch()
    layout.addLayout(clicker_button_layout)

    clicker_preset_layout = QtWidgets.QHBoxLayout()
    clicker_preset_layout.addWidget(QtWidgets.QLabel(window.i18n.t("clicker.preset", "Click Speed")))
    window.clickerPresetCombo = QtWidgets.QComboBox()
    window.clickerPresetCombo.addItem(window.i18n.t("clicker.preset.efficient", "Efficient Mode"), "efficient")
    window.clickerPresetCombo.addItem(window.i18n.t("clicker.preset.extreme", "Extreme Mode"), "extreme")
    window.clickerPresetCombo.addItem(window.i18n.t("clicker.preset.custom", "Custom"), "custom")
    window.clickerPresetCombo.currentIndexChanged.connect(window._on_clicker_preset_changed)
    clicker_preset_layout.addWidget(window.clickerPresetCombo)
    clicker_preset_layout.addStretch()
    layout.addLayout(clicker_preset_layout)

    window.clickerPresetHint = QtWidgets.QLabel()
    window.clickerPresetHint.setWordWrap(True)
    window.clickerPresetHint.setStyleSheet("color: rgba(142, 142, 147, 0.95); font-size: 12px;")
    layout.addWidget(window.clickerPresetHint)

    clicker_interval_layout = QtWidgets.QHBoxLayout()
    window.clickerIntervalLabel = QtWidgets.QLabel(window.i18n.t("clicker.interval", "Click Interval (ms)"))
    clicker_interval_layout.addWidget(window.clickerIntervalLabel)
    window.clickerIntervalSpin = QtWidgets.QSpinBox()
    window.clickerIntervalSpin.setRange(1, 5000)
    window.clickerIntervalSpin.setSingleStep(10)
    window.clickerIntervalSpin.setSuffix(" ms")
    window.clickerIntervalSpin.valueChanged.connect(lambda _value: window._schedule_live_apply())
    clicker_interval_layout.addWidget(window.clickerIntervalSpin)
    clicker_interval_layout.addStretch()
    layout.addLayout(clicker_interval_layout)

    trigger_mode_layout = QtWidgets.QHBoxLayout()
    trigger_mode_layout.addWidget(QtWidgets.QLabel(window.i18n.t("clicker.trigger.mode", "Trigger Mode")))
    window.clickerTriggerModeCombo = QtWidgets.QComboBox()
    window.clickerTriggerModeCombo.addItem(window.i18n.t("clicker.trigger.toggle", "Toggle"), "toggle")
    window.clickerTriggerModeCombo.addItem(window.i18n.t("clicker.trigger.holdKey", "Hold Key"), "holdKey")
    window.clickerTriggerModeCombo.addItem(window.i18n.t("clicker.trigger.holdMouseButton", "Hold Mouse Button"), "holdMouseButton")
    window.clickerTriggerModeCombo.currentIndexChanged.connect(window._sync_clicker_trigger_controls)
    window.clickerTriggerModeCombo.currentIndexChanged.connect(lambda _index: window._schedule_live_apply())
    trigger_mode_layout.addWidget(window.clickerTriggerModeCombo)
    trigger_mode_layout.addStretch()
    layout.addLayout(trigger_mode_layout)

    toggle_hotkey_layout = QtWidgets.QHBoxLayout()
    window.clickerToggleHotkeyLabel = QtWidgets.QLabel(window.i18n.t("clicker.hotkey", "Auto Clicker Toggle"))
    toggle_hotkey_layout.addWidget(window.clickerToggleHotkeyLabel)
    window.clickerToggleHotkeyCapture = HotkeyCapture(i18n=window.i18n)
    window.clickerToggleHotkeyCapture.hotkeyChanged.connect(lambda _cfg: window._schedule_live_apply())
    toggle_hotkey_layout.addWidget(window.clickerToggleHotkeyCapture)
    layout.addLayout(toggle_hotkey_layout)

    hold_key_layout = QtWidgets.QHBoxLayout()
    window.clickerHoldKeyLabel = QtWidgets.QLabel(window.i18n.t("clicker.trigger.holdKey.input", "Hold Key"))
    hold_key_layout.addWidget(window.clickerHoldKeyLabel)
    window.clickerHoldKeyCapture = HotkeyCapture(i18n=window.i18n)
    window.clickerHoldKeyCapture.hotkeyChanged.connect(lambda _cfg: window._schedule_live_apply())
    hold_key_layout.addWidget(window.clickerHoldKeyCapture)
    layout.addLayout(hold_key_layout)

    hold_mouse_layout = QtWidgets.QHBoxLayout()
    window.clickerHoldMouseLabel = QtWidgets.QLabel(window.i18n.t("clicker.trigger.holdMouseButton.input", "Hold Mouse Button"))
    hold_mouse_layout.addWidget(window.clickerHoldMouseLabel)
    window.clickerHoldMouseCombo = QtWidgets.QComboBox()
    window.clickerHoldMouseCombo.addItem(window.i18n.t("clicker.mouse.middle", "Middle Button"), "middle")
    window.clickerHoldMouseCombo.addItem(window.i18n.t("clicker.mouse.x1", "Side Button X1 (usually Back)"), "x1")
    window.clickerHoldMouseCombo.addItem(window.i18n.t("clicker.mouse.x2", "Side Button X2 (usually Forward)"), "x2")
    window.clickerHoldMouseCombo.addItem(window.i18n.t("clicker.mouse.left", "Left Button"), "left")
    window.clickerHoldMouseCombo.addItem(window.i18n.t("clicker.mouse.right", "Right Button"), "right")
    window.clickerHoldMouseCombo.currentIndexChanged.connect(lambda _index: window._schedule_live_apply())
    hold_mouse_layout.addWidget(window.clickerHoldMouseCombo)
    hold_mouse_layout.addStretch()
    layout.addLayout(hold_mouse_layout)

    sound_enabled_layout = QtWidgets.QHBoxLayout()
    window.clickerSoundEnabledCheck = QtWidgets.QCheckBox(window.i18n.t("clicker.sound.enabled", "Play start sound"))
    window.clickerSoundEnabledCheck.toggled.connect(window._sync_clicker_sound_controls)
    window.clickerSoundEnabledCheck.toggled.connect(lambda _checked: window._schedule_live_apply())
    sound_enabled_layout.addWidget(window.clickerSoundEnabledCheck)
    sound_enabled_layout.addStretch()
    layout.addLayout(sound_enabled_layout)

    sound_preset_layout = QtWidgets.QHBoxLayout()
    window.clickerSoundPresetLabel = QtWidgets.QLabel(window.i18n.t("clicker.sound.preset", "Start Sound"))
    sound_preset_layout.addWidget(window.clickerSoundPresetLabel)
    window.clickerSoundPresetCombo = QtWidgets.QComboBox()
    window.clickerSoundPresetCombo.addItem(window.i18n.t("clicker.sound.preset.systemAsterisk", "System Asterisk"), "systemAsterisk")
    window.clickerSoundPresetCombo.addItem(window.i18n.t("clicker.sound.preset.systemExclamation", "System Exclamation"), "systemExclamation")
    window.clickerSoundPresetCombo.addItem(window.i18n.t("clicker.sound.preset.systemQuestion", "System Question"), "systemQuestion")
    window.clickerSoundPresetCombo.addItem(window.i18n.t("clicker.sound.preset.systemHand", "System Hand"), "systemHand")
    window.clickerSoundPresetCombo.addItem(window.i18n.t("clicker.sound.preset.custom", "Custom File"), "custom")
    window.clickerSoundPresetCombo.currentIndexChanged.connect(window._sync_clicker_sound_controls)
    window.clickerSoundPresetCombo.currentIndexChanged.connect(lambda _index: window._schedule_live_apply())
    sound_preset_layout.addWidget(window.clickerSoundPresetCombo)
    window.clickerSoundPreviewBtn = QtWidgets.QPushButton(window.i18n.t("clicker.sound.preview", "Preview"))
    window.clickerSoundPreviewBtn.clicked.connect(window._preview_clicker_sound)
    sound_preset_layout.addWidget(window.clickerSoundPreviewBtn)
    sound_preset_layout.addStretch()
    layout.addLayout(sound_preset_layout)

    custom_sound_layout = QtWidgets.QHBoxLayout()
    window.clickerCustomSoundPathEdit = QtWidgets.QLineEdit()
    window.clickerCustomSoundPathEdit.setPlaceholderText(window.i18n.t("clicker.sound.path.placeholder", "Select a local audio file"))
    window.clickerCustomSoundPathEdit.textChanged.connect(lambda _text: window._schedule_live_apply())
    custom_sound_layout.addWidget(window.clickerCustomSoundPathEdit)
    window.clickerCustomSoundBrowseBtn = QtWidgets.QPushButton(window.i18n.t("browse", "Browse"))
    window.clickerCustomSoundBrowseBtn.clicked.connect(window._browse_clicker_sound_file)
    custom_sound_layout.addWidget(window.clickerCustomSoundBrowseBtn)
    layout.addLayout(custom_sound_layout)

    window.clickerConfigHint = QtWidgets.QLabel(
        window.i18n.t(
            "clicker.config.hint",
            "Restore defaults by deleting Mconfig.json. Legacy config.json is still read for compatibility."
        )
    )
    window.clickerConfigHint.setWordWrap(True)
    window.clickerConfigHint.setStyleSheet("color: rgba(142, 142, 147, 0.95); font-size: 12px;")
    layout.addWidget(window.clickerConfigHint)
    window._populate_clicker_profiles()

    layout.addWidget(create_section_label(window.i18n.t("position.title", "Target Position")))
    pos_layout = QtWidgets.QHBoxLayout()
    window.posCombo = QtWidgets.QComboBox()
    window.posCombo.addItem(window.i18n.t("position.virtualCenter", "Virtual screen center"), "virtualCenter")
    window.posCombo.addItem(window.i18n.t("position.primaryCenter", "Primary screen center"), "primaryCenter")
    window.posCombo.addItem(window.i18n.t("position.custom", "Custom"), "custom")
    window.posCombo.currentIndexChanged.connect(lambda _index: window._schedule_live_apply())
    current_mode = window.settings.data["position"].get("mode", "virtualCenter")
    for i in range(window.posCombo.count()):
        if window.posCombo.itemData(i) == current_mode:
            window.posCombo.setCurrentIndex(i)
            break
    pos_layout.addWidget(window.posCombo)
    layout.addLayout(pos_layout)

    custom_layout = QtWidgets.QHBoxLayout()
    custom_layout.addWidget(QtWidgets.QLabel("X:"))
    window.customXSpin = QtWidgets.QSpinBox()
    window.customXSpin.setRange(-10000, 10000)
    window.customXSpin.setValue(window.settings.data["position"].get("customX", 0))
    window.customXSpin.valueChanged.connect(lambda _value: window._schedule_live_apply())
    custom_layout.addWidget(window.customXSpin)
    custom_layout.addWidget(QtWidgets.QLabel("Y:"))
    window.customYSpin = QtWidgets.QSpinBox()
    window.customYSpin.setRange(-10000, 10000)
    window.customYSpin.setValue(window.settings.data["position"].get("customY", 0))
    window.customYSpin.valueChanged.connect(lambda _value: window._schedule_live_apply())
    custom_layout.addWidget(window.customYSpin)
    custom_layout.addStretch()
    layout.addLayout(custom_layout)

    layout.addWidget(create_section_label(window.i18n.t("window.specific.title", "Window-Specific Locking")))
    window.windowSpecificCheck = QtWidgets.QCheckBox(
        window.i18n.t("window.specific.enabled", "Enable window-specific locking")
    )
    window.windowSpecificCheck.setChecked(window.settings.data["windowSpecific"].get("enabled", False))
    window.windowSpecificCheck.toggled.connect(lambda _checked: window._schedule_live_apply())
    layout.addWidget(window.windowSpecificCheck)

    list_layout = QtWidgets.QVBoxLayout()
    list_layout.setSpacing(8)
    list_label = QtWidgets.QLabel(window.i18n.t("window.specific.listLabel", "Target Windows List"))
    list_layout.addWidget(list_label)

    window.targetList = QtWidgets.QListWidget()
    window.targetList.setFixedHeight(120)
    window.targetList.setStyleSheet("""
        QListWidget {
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(128, 128, 128, 0.3);
            border-radius: 6px;
            padding: 4px;
        }
    """)
    for win_title in window.settings.data["windowSpecific"].get("targetWindows", []):
        window.targetList.addItem(win_title)
    list_layout.addWidget(window.targetList)

    input_layout = QtWidgets.QHBoxLayout()
    window.manualInputEdit = QtWidgets.QLineEdit()
    window.manualInputEdit.setPlaceholderText(window.i18n.t("window.specific.placeholder", "Target window title"))
    input_layout.addWidget(window.manualInputEdit)
    window.pickProcessBtn = QtWidgets.QPushButton(window.i18n.t("window.specific.pick", "Pick Process"))
    window.pickProcessBtn.clicked.connect(window._pick_process)
    input_layout.addWidget(window.pickProcessBtn)
    list_layout.addLayout(input_layout)

    btn_layout = QtWidgets.QHBoxLayout()
    window.addBtn = QtWidgets.QPushButton(window.i18n.t("window.specific.add", "Add"))
    window.addBtn.clicked.connect(window._add_target_window)
    btn_layout.addWidget(window.addBtn)
    window.removeBtn = QtWidgets.QPushButton(window.i18n.t("window.specific.remove", "Remove"))
    window.removeBtn.clicked.connect(window._remove_target_window)
    btn_layout.addWidget(window.removeBtn)
    btn_layout.addStretch()
    list_layout.addLayout(btn_layout)
    layout.addLayout(list_layout)

    window.autoLockCheck = QtWidgets.QCheckBox(
        window.i18n.t("window.specific.autoLock", "Auto lock/unlock on window switch")
    )
    window.autoLockCheck.setChecked(window.settings.data["windowSpecific"].get("autoLockOnWindowFocus", False))
    window.autoLockCheck.toggled.connect(lambda _checked: window._schedule_live_apply())
    layout.addWidget(window.autoLockCheck)

    window.resumeAfterSwitchCheck = QtWidgets.QCheckBox(
        window.i18n.t("window.specific.resumeAfterSwitch", "Auto re-lock after leaving and re-entering target window (for manual unlock)")
    )
    window.resumeAfterSwitchCheck.setChecked(window.settings.data["windowSpecific"].get("resumeAfterWindowSwitch", False))
    window.resumeAfterSwitchCheck.toggled.connect(lambda _checked: window._schedule_live_apply())
    layout.addWidget(window.resumeAfterSwitchCheck)

    layout.addWidget(create_section_label(window.i18n.t("section.windowTools", "Window Tools")))
    window.resizeCenterBtn = QtWidgets.QPushButton(window.i18n.t("windowTools.resizeCenter", "Resize & Center Window"))
    window.resizeCenterBtn.setFixedHeight(40)
    window.resizeCenterBtn.setCursor(QtCore.Qt.PointingHandCursor)
    window.resizeCenterBtn.clicked.connect(window._open_window_resize)
    layout.addWidget(window.resizeCenterBtn)

    layout.addWidget(create_section_label(window.i18n.t("section.settings", "Settings")))
    lang_layout = QtWidgets.QHBoxLayout()
    lang_layout.addWidget(QtWidgets.QLabel(window.i18n.t("language.title", "Language")))
    window.langCombo = QtWidgets.QComboBox()
    window.langCombo.addItem("English", "en")
    window.langCombo.addItem("简体中文", "zh-Hans")
    window.langCombo.addItem("繁體中文", "zh-Hant")
    window.langCombo.addItem("日本語", "ja")
    window.langCombo.addItem("한국어", "ko")
    current_lang = window.settings.data.get("language", "zh-Hans")
    for i in range(window.langCombo.count()):
        if window.langCombo.itemData(i) == current_lang:
            window.langCombo.setCurrentIndex(i)
            break
    lang_layout.addWidget(window.langCombo)
    window.langCombo.currentIndexChanged.connect(lambda _index: window._schedule_live_apply())
    lang_layout.addStretch()
    layout.addLayout(lang_layout)

    theme_layout = QtWidgets.QHBoxLayout()
    theme_layout.addWidget(QtWidgets.QLabel(window.i18n.t("theme.title", "Theme")))
    window.themeCombo = QtWidgets.QComboBox()
    window.themeCombo.addItem(window.i18n.t("theme.dark", "Dark"), "dark")
    window.themeCombo.addItem(window.i18n.t("theme.light", "Light"), "light")
    current_theme = window.settings.data.get("theme", "dark")
    for i in range(window.themeCombo.count()):
        if window.themeCombo.itemData(i) == current_theme:
            window.themeCombo.setCurrentIndex(i)
            break
    theme_layout.addWidget(window.themeCombo)
    window.themeCombo.currentIndexChanged.connect(lambda _index: window._schedule_live_apply())
    theme_layout.addStretch()
    layout.addLayout(theme_layout)

    window.restartRequiredHint = QtWidgets.QLabel(
        window.i18n.t(
            "settings.restartRequired",
            "Language and some interface text require restarting the app to fully refresh.",
        )
    )
    window.restartRequiredHint.setWordWrap(True)
    window.restartRequiredHint.setStyleSheet("color: rgba(142, 142, 147, 0.95); font-size: 12px;")
    layout.addWidget(window.restartRequiredHint)

    close_action_layout = QtWidgets.QHBoxLayout()
    close_action_layout.addWidget(QtWidgets.QLabel(window.i18n.t("close.action.title", "Close Behavior")))
    window.resetCloseActionBtn = QtWidgets.QPushButton(window.i18n.t("close.action.reset", "Reset 'Don't ask again'"))
    window.resetCloseActionBtn.clicked.connect(window._reset_close_action)
    close_action_layout.addWidget(window.resetCloseActionBtn)
    close_action_layout.addStretch()
    layout.addLayout(close_action_layout)

    window.startupCheck = QtWidgets.QCheckBox(window.i18n.t("startup.autostart", "Launch on system startup"))
    window.startupCheck.setChecked(is_startup_enabled())
    window.startupCheck.toggled.connect(lambda _checked: window._schedule_live_apply())
    layout.addWidget(window.startupCheck)

    layout.addStretch()
    live_apply_hint = QtWidgets.QLabel(
        window.i18n.t("settings.liveApply", "Settings in this page take effect automatically.")
    )
    live_apply_hint.setWordWrap(True)
    live_apply_hint.setStyleSheet("color: rgba(142, 142, 147, 0.95); font-size: 12px;")
    layout.addWidget(live_apply_hint)

    scroll.setWidget(content)
    page_layout = QtWidgets.QVBoxLayout(page)
    page_layout.setContentsMargins(0, 0, 0, 0)
    page_layout.addWidget(scroll)
    return page
