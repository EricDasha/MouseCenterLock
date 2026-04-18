"""
Simple page builder.
"""
from PySide6 import QtCore, QtWidgets

from ui.pages.common import create_info_card


def build_simple_page(window) -> QtWidgets.QWidget:
    """Build the simple mode page and attach widgets to the window."""
    page = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(page)
    layout.setContentsMargins(8, 16, 8, 16)
    layout.setSpacing(16)

    window.statusBadge = QtWidgets.QLabel()
    window.statusBadge.setAlignment(QtCore.Qt.AlignCenter)
    window.statusBadge.setFixedHeight(56)
    window._update_status_badge()
    layout.addWidget(window.statusBadge)

    window.configCard = create_info_card(
        window.i18n.t("simple.config.title", "Current Configuration")
    )
    window.configLabel = QtWidgets.QLabel()
    window.configLabel.setWordWrap(True)
    window.configLabel.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
    window.configLabel.setStyleSheet("color: rgba(235, 235, 245, 0.90); font-size: 13px; line-height: 1.6;")
    window.configCard.layout().addWidget(window.configLabel)
    layout.addWidget(window.configCard)

    window.hotkeysCard = create_info_card(
        window.i18n.t("simple.hotkeys.title", "Hotkeys")
    )
    window.hotkeysLabel = QtWidgets.QLabel()
    window.hotkeysLabel.setWordWrap(True)
    window.hotkeysLabel.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
    window.hotkeysLabel.setStyleSheet(
        "color: rgba(235, 235, 245, 0.90); font-size: 13px; "
        "font-family: 'Consolas', 'Courier New', monospace; line-height: 1.8;"
    )
    window.hotkeysCard.layout().addWidget(window.hotkeysLabel)
    layout.addWidget(window.hotkeysCard)

    window._update_simple_info()
    layout.addStretch(1)

    window.toggleBtn = QtWidgets.QPushButton()
    window.toggleBtn.setFixedHeight(56)
    window.toggleBtn.setCursor(QtCore.Qt.PointingHandCursor)
    window.toggleBtn.clicked.connect(window.toggle_lock)
    window._update_toggle_button()
    layout.addWidget(window.toggleBtn)

    window.clickerBtn = QtWidgets.QPushButton()
    window.clickerBtn.setFixedHeight(48)
    window.clickerBtn.setCursor(QtCore.Qt.PointingHandCursor)
    window.clickerBtn.clicked.connect(window.toggle_clicker)
    window._update_clicker_button()
    layout.addWidget(window.clickerBtn)

    hint = QtWidgets.QLabel(window.i18n.t("simple.hint", "Use hotkeys for quick access ⌨️"))
    hint.setAlignment(QtCore.Qt.AlignCenter)
    hint.setStyleSheet("color: rgba(142, 142, 147, 0.95); font-size: 12px;")
    layout.addWidget(hint)
    return page
