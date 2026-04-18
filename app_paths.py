"""
Shared application path helpers.
"""
from __future__ import annotations

import os
import sys


if getattr(sys, "frozen", False):
    _BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    _RUN_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _RUN_DIR = _BASE_DIR

APP_DIR = _BASE_DIR
RUN_DIR = _RUN_DIR
ASSETS_DIR = os.path.join(APP_DIR, "pythonProject", "assets")
if not os.path.exists(ASSETS_DIR):
    ASSETS_DIR = os.path.join(APP_DIR, "assets")

INSTANCE_SERVER_NAME = "MouseCenterLockActivation"
