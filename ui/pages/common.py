"""
Shared UI page helpers.
"""
from __future__ import annotations

import html

from PySide6 import QtCore, QtGui, QtWidgets


class DelayedHelpLabel(QtWidgets.QLabel):
    """Label that shows contextual help after a deliberate hover."""

    def __init__(
        self,
        text: str,
        help_text: str,
        *,
        delay_ms: int = 3000,
        parent=None,
    ):
        super().__init__(text, parent)
        self._help_text = str(help_text or "").strip()
        self._hovering = False
        self._hover_timer = QtCore.QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(max(0, int(delay_ms)))
        self._hover_timer.timeout.connect(self._show_help)
        self.setAccessibleDescription(self._help_text)

    @property
    def help_delay_ms(self) -> int:
        """Return the hover delay, primarily for diagnostics and tests."""
        return self._hover_timer.interval()

    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        self._hovering = True
        if self._help_text:
            self._hover_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._hovering = False
        self._hover_timer.stop()
        QtWidgets.QToolTip.hideText()
        super().leaveEvent(event)

    def _show_help(self) -> None:
        if not self._hovering or not self._help_text:
            return
        safe_text = html.escape(self._help_text).replace("\n", "<br>")
        tooltip = f"<div style='width: 360px; white-space: normal;'>{safe_text}</div>"
        position = self.mapToGlobal(QtCore.QPoint(0, self.height() + 4))
        QtWidgets.QToolTip.showText(position, tooltip, self)


def create_delayed_help_label(
    text: str,
    help_text: str,
    *,
    delay_ms: int = 3000,
) -> DelayedHelpLabel:
    """Create a plain label whose detailed explanation appears after hovering."""
    return DelayedHelpLabel(text, help_text, delay_ms=delay_ms)


def create_section_label(text: str) -> QtWidgets.QLabel:
    """Create a styled section label."""
    label = QtWidgets.QLabel(text)
    label.setStyleSheet("font-weight: 600; font-size: 15px; margin-top: 8px;")
    return label


def create_info_card(title: str) -> QtWidgets.QFrame:
    """Create a styled information card with title."""
    card = QtWidgets.QFrame()
    card.setFrameShape(QtWidgets.QFrame.NoFrame)
    card.setStyleSheet("""
        QFrame {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
        }
    """)
    card_layout = QtWidgets.QVBoxLayout(card)
    card_layout.setContentsMargins(16, 14, 16, 14)
    card_layout.setSpacing(10)

    title_label = QtWidgets.QLabel(title)
    title_label.setStyleSheet("font-weight: 600; font-size: 14px; color: rgba(10, 132, 255, 1.0);")
    card_layout.addWidget(title_label)
    return card
