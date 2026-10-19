import unittest

from smoothscroll.models import AppConfig
from smoothscroll.utils.winapi import resolve_scroll_config


class RuleResolutionTests(unittest.TestCase):
    def setUp(self):
        self.global_config = object()
        self.special_config = object()

    def test_enabled_global_is_used_without_custom_match(self):
        rules = [AppConfig(regexp=r'.*', enabled=True, scroll_config=self.global_config)]
        self.assertIs(resolve_scroll_config(rules, r'C:/Apps/example.exe'), self.global_config)

    def test_disabled_global_disables_scroll(self):
        rules = [AppConfig(regexp=r'.*', enabled=False, scroll_config=self.global_config)]
        self.assertIsNone(resolve_scroll_config(rules, r'C:/Apps/example.exe'))

    def test_active_exception_disables_scroll(self):
        rules = [
            AppConfig(regexp=r'.*', enabled=True, scroll_config=self.global_config),
            AppConfig(regexp=r'example\.exe', exception_active=True, scroll_config=self.special_config),
        ]
        self.assertIsNone(resolve_scroll_config(rules, r'C:/Apps/example.exe'))

    def test_last_matching_exception_state_wins(self):
        rules = [
            AppConfig(regexp=r'.*', enabled=True, scroll_config=self.global_config),
            AppConfig(regexp=r'example\.exe', exception_active=True),
            AppConfig(regexp=r'example\.exe', exception_active=False),
        ]
        self.assertIs(resolve_scroll_config(rules, r'C:/Apps/example.exe'), self.global_config)

    def test_inactive_exception_falls_back_to_global(self):
        rules = [
            AppConfig(regexp=r'.*', enabled=True, scroll_config=self.global_config),
            AppConfig(regexp=r'example\.exe', exception_active=False),
        ]
        self.assertIs(resolve_scroll_config(rules, r'C:/Apps/example.exe'), self.global_config)

    def test_exception_state_is_independent_of_global_fallback_state(self):
        rules = [
            AppConfig(regexp=r'.*', enabled=False, scroll_config=self.global_config),
            AppConfig(regexp=r'example\.exe', exception_active=False),
        ]
        self.assertIsNone(resolve_scroll_config(rules, r'C:/Apps/example.exe'))


if __name__ == '__main__':
    unittest.main()
