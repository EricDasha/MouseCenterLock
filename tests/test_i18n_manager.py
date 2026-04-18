import unittest

import i18n_manager


class I18nManagerTests(unittest.TestCase):
    def test_unknown_language_falls_back_to_english(self):
        i18n = i18n_manager.I18n("xx-Unknown")
        self.assertEqual(i18n.lang_code, "en")

    def test_missing_key_uses_explicit_fallback(self):
        i18n = i18n_manager.I18n("en")
        self.assertEqual(i18n.t("missing.translation.key", "Fallback"), "Fallback")


if __name__ == "__main__":
    unittest.main()
