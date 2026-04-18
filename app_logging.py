"""
Minimal runtime logging helpers for MouseCenterLock.
"""
from __future__ import annotations

import datetime as _dt
import os
import sys
import traceback
from pathlib import Path


def get_log_path() -> Path:
    """Return the runtime log path in the app's run directory."""
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent
    return base_dir / "MouseCenterLock.log"


def log_message(message: str) -> None:
    """Append a timestamped message to the runtime log."""
    timestamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = get_log_path()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {message}{os.linesep}")
    except Exception:
        pass


def log_exception(context: str, exc: BaseException) -> None:
    """Append an exception traceback to the runtime log."""
    log_message(f"{context}: {exc}")
    try:
        trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        log_message(trace.rstrip())
    except Exception:
        pass
