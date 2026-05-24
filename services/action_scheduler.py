"""
Action scheduling for macro runtimes.

The rule engine decides what to do; this scheduler owns timing and cancellation.
It is intentionally synchronous for the current Qt-thread macro runtime, but the
interface keeps delay/cancel behavior out of the rule matcher so virtual HID or
hardware HID backends can reuse the same action stream later.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict


class ActionScheduler:
    """Execute a bounded action list with interruptible delay support."""

    def __init__(
        self,
        execute_action: Callable[[Dict[str, Any]], None],
        *,
        should_cancel: Callable[[], bool] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._execute_action = execute_action
        self._should_cancel = should_cancel or (lambda: False)
        self._sleep = sleep

    def run(self, actions: Any) -> None:
        if not isinstance(actions, list):
            return
        for action in actions[:32]:
            if self._should_cancel():
                return
            if not isinstance(action, dict):
                continue
            action_type = str(action.get("type", "") or "")
            if action_type == "delay":
                self._delay(max(0, min(60000, int(action.get("ms", 0)))) / 1000.0)
            else:
                self._execute_action(action)

    def _delay(self, seconds: float) -> None:
        remaining = max(0.0, seconds)
        while remaining > 0 and not self._should_cancel():
            interval = min(0.025, remaining)
            self._sleep(interval)
            remaining -= interval
