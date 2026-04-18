"""
Shared UI page helpers.
"""
from PySide6 import QtWidgets


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
