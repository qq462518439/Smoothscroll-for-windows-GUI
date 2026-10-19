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

    def test_disabled_custom_rule_does_not_fall_back_to_global(self):
        rules = [
            AppConfig(regexp=r'.*', enabled=True, scroll_config=self.global_config),
            AppConfig(regexp=r'example\.exe', enabled=False, scroll_config=self.special_config),
        ]
        self.assertIsNone(resolve_scroll_config(rules, r'C:/Apps/example.exe'))

    def test_last_matching_custom_rule_wins(self):
        later_config = object()
        rules = [
            AppConfig(regexp=r'.*', enabled=True, scroll_config=self.global_config),
            AppConfig(regexp=r'example\.exe', enabled=True, scroll_config=self.special_config),
            AppConfig(regexp=r'example\.exe', enabled=True, scroll_config=later_config),
        ]
        self.assertIs(resolve_scroll_config(rules, r'C:/Apps/example.exe'), later_config)


if __name__ == '__main__':
    unittest.main()
