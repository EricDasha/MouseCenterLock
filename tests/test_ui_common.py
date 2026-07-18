import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from ui.pages.common import DelayedHelpLabel, create_delayed_help_label


class DelayedHelpLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_factory_uses_three_second_delay_and_accessible_description(self):
        label = create_delayed_help_label("Clicker Backend", "Backend explanation")

        self.assertIsInstance(label, DelayedHelpLabel)
        self.assertEqual(label.help_delay_ms, 3000)
        self.assertEqual(label.accessibleDescription(), "Backend explanation")

    def test_tooltip_only_shows_while_hovering_and_hides_on_leave(self):
        label = DelayedHelpLabel("Mouse down hold", "Down -> hold -> up")
        label.resize(120, 24)

        with mock.patch.object(QtWidgets.QToolTip, "showText") as show_text, \
             mock.patch.object(QtWidgets.QToolTip, "hideText") as hide_text:
            label._show_help()
            show_text.assert_not_called()

            label._hovering = True
            label._show_help()
            show_text.assert_called_once()

            QtWidgets.QApplication.sendEvent(label, QtCore.QEvent(QtCore.QEvent.Type.Leave))
            hide_text.assert_called_once()
            self.assertFalse(label._hovering)
            self.assertFalse(label._hover_timer.isActive())

    def test_enter_event_starts_delay_before_showing_tooltip(self):
        label = DelayedHelpLabel("Click interval", "Interval explanation", delay_ms=10)
        enter = QtGui.QEnterEvent(
            QtCore.QPointF(1, 1),
            QtCore.QPointF(1, 1),
            QtCore.QPointF(1, 1),
        )

        with mock.patch.object(QtWidgets.QToolTip, "showText") as show_text:
            QtWidgets.QApplication.sendEvent(label, enter)
            show_text.assert_not_called()
            QtTest.QTest.qWait(30)
            show_text.assert_called_once()

        QtWidgets.QApplication.sendEvent(label, QtCore.QEvent(QtCore.QEvent.Type.Leave))


if __name__ == "__main__":
    unittest.main()
