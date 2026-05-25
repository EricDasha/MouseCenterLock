"""
Internationalization helpers for MCL.
"""
from __future__ import annotations

from typing import Dict

import os

from app_paths import I18N_DIR
from settings_manager import load_json


class I18n:
    """Internationalization helper for loading and accessing translations."""

    SUPPORTED_LANGUAGES = ["en", "zh-Hans", "zh-Hant", "ja", "ko"]

    def __init__(self, lang_code: str):
        self.lang_code = lang_code if lang_code in self.SUPPORTED_LANGUAGES else "en"
        self.strings: Dict[str, str] = load_json(
            os.path.join(I18N_DIR, f"{self.lang_code}.json"), {}
        )
        if self.lang_code != "en":
            self._fallback = load_json(os.path.join(I18N_DIR, "en.json"), {})
        else:
            self._fallback = {}

    def t(self, key: str, fallback: str = "") -> str:
        """Get translation for key, with fallback chain."""
        if key in self.strings:
            return self.strings[key]
        if key in self._fallback:
            return self._fallback[key]
        return fallback if fallback else key
