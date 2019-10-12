from __future__ import unicode_literals

import os.path
import re
import unittest
from collections import namedtuple

from truffleHogRegexes.regexChecks import regexes as default_regexes

from tartufo import tartufo


class ConfigureRegexTests(unittest.TestCase):

    def test_configure_regexes_from_args_rules_files_without_defaults(self):
        rules_filenames = [os.path.join(os.path.dirname(__file__), "data", "testRules.json")]
        expected_regexes = {"RSA private key 2": re.compile("-----BEGIN EC PRIVATE KEY-----")}

        Args = namedtuple("Args", ("do_regex", "git_rules_repo", "git_rules_filenames", "rules_filenames",
                                   "do_default_regexes"))
        args = Args(True, None, None, rules_filenames, False)
        actual_regexes = tartufo.configure_regexes_from_args(args, default_regexes)

        self.assertEqual(
            expected_regexes, actual_regexes,
            "The regexes dictionary should match the test rules "
            "(expected: {}, actual: {})".format(expected_regexes, actual_regexes)
        )

    def test_configure_regexes_from_args_rules_files_with_defaults(self):
        rules_filenames = [os.path.join(os.path.dirname(__file__), "data", "testRules.json")]
        expected_regexes = dict(default_regexes)
        expected_regexes["RSA private key 2"] = re.compile("-----BEGIN EC PRIVATE KEY-----")

        Args = namedtuple("Args", ("do_regex", "git_rules_repo", "git_rules_filenames", "rules_filenames",
                                   "do_default_regexes"))
        args = Args(True, None, None, rules_filenames, True)
        actual_regexes = tartufo.configure_regexes_from_args(args, default_regexes)

        self.assertEqual(
            expected_regexes, actual_regexes,
            "The regexes dictionary should match the test rules "
            "(expected: {}, actual: {})".format(expected_regexes, actual_regexes)
        )

    def test_configure_regexes_from_args_no_do_regex(self):
        rules_filenames = ["testRules.json"]

        Args = namedtuple("Args", ("do_regex", "git_rules_repo", "git_rules_filenames", "rules_filenames",
                                   "do_default_regexes"))
        args = Args(False, None, None, rules_filenames, True)
        actual_regexes = tartufo.configure_regexes_from_args(args, default_regexes)

        self.assertEqual({}, actual_regexes, "The regexes dictionary should be empty when do_regex is False")

    def test_configure_regexes_from_args_no_rules(self):
        rules_filenames = []
        expected_regexes = dict(default_regexes)

        Args = namedtuple("Args", ("do_regex", "git_rules_repo", "git_rules_filenames", "rules_filenames",
                                   "do_default_regexes"))
        args = Args(True, None, None, rules_filenames, False)
        actual_regexes = tartufo.configure_regexes_from_args(args, default_regexes)

        self.assertEqual(
            expected_regexes, actual_regexes,
            "The regexes dictionary should not have been changed when no rules files are specified"
        )


if __name__ == "__main__":
    unittest.main()
