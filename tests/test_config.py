from __future__ import unicode_literals

import re
import unittest

from truffleHogRegexes.regexChecks import regexes as default_regexes

from tartufo import config

try:
    import pathlib
except ImportError:
    import pathlib2 as pathlib  # type: ignore


class ConfigureRegexTests(unittest.TestCase):
    def test_configure_regexes_from_args_rules_files_without_defaults(self):
        rules_path = pathlib.Path(__file__).parent / "data" / "testRules.json"
        rules_files = (rules_path.open(),)
        expected_regexes = {
            "RSA private key 2": re.compile("-----BEGIN EC PRIVATE KEY-----")
        }

        args = {"regex": True, "default_regexes": False, "rules": rules_files}
        actual_regexes = config.configure_regexes_from_args(args, default_regexes)

        self.assertEqual(
            expected_regexes,
            actual_regexes,
            "The regexes dictionary should match the test rules "
            "(expected: {}, actual: {})".format(expected_regexes, actual_regexes),
        )

    def test_configure_regexes_from_args_rules_files_with_defaults(self):
        rules_path = pathlib.Path(__file__).parent / "data" / "testRules.json"
        rules_files = (rules_path.open(),)
        expected_regexes = dict(default_regexes)
        expected_regexes["RSA private key 2"] = re.compile(
            "-----BEGIN EC PRIVATE KEY-----"
        )

        args = {"regex": True, "default_regexes": True, "rules": rules_files}
        actual_regexes = config.configure_regexes_from_args(args, default_regexes)

        self.assertEqual(
            expected_regexes,
            actual_regexes,
            "The regexes dictionary should match the test rules "
            "(expected: {}, actual: {})".format(expected_regexes, actual_regexes),
        )

    def test_configure_regexes_from_args_no_do_regex(self):
        rules_path = pathlib.Path(__file__).parent / "data" / "testRules.json"
        rules_files = (rules_path.open(),)
        args = {"regex": False, "default_regexes": True, "rules": rules_files}
        actual_regexes = config.configure_regexes_from_args(args, default_regexes)

        self.assertEqual(
            {},
            actual_regexes,
            "The regexes dictionary should be empty when do_regex is False",
        )

    def test_configure_regexes_from_args_no_rules(self):
        expected_regexes = dict(default_regexes)

        args = {"regex": True, "default_regexes": True, "rules": ()}
        actual_regexes = config.configure_regexes_from_args(args, default_regexes)

        self.assertEqual(
            expected_regexes,
            actual_regexes,
            "The regexes dictionary should not have been changed when no rules files are specified",
        )


if __name__ == "__main__":
    unittest.main()
