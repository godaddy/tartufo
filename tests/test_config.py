from __future__ import unicode_literals

import os
import re
import unittest

import click
from click.testing import CliRunner
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


class ConfigFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = pathlib.Path(__file__).parent / "data"
        return super(ConfigFileTests, cls).setUpClass()

    def setUp(self):
        self.ctx = click.Context(click.Command("foo"))
        self.param = click.Option(["--config"])
        return super(ConfigFileTests, self).setUp()

    def test_pyproject_toml_gets_read_if_no_file_specified(self):
        cur_dir = pathlib.Path()
        os.chdir(str(self.data_dir))
        config.read_pyproject_toml(self.ctx, self.param, "")
        os.chdir(str(cur_dir))
        self.assertEqual(self.ctx.default_map, {"json": True})

    def test_tartufo_toml_gets_read_if_no_pyproject_toml(self):
        cur_dir = pathlib.Path()
        os.chdir(str(self.data_dir / "config"))
        config.read_pyproject_toml(self.ctx, self.param, "")
        os.chdir(str(cur_dir))
        self.assertEqual(self.ctx.default_map, {"regex": True})

    def test_specified_file_gets_read(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            toml_file = self.data_dir / "config" / "tartufo.toml"
            config.read_pyproject_toml(self.ctx, self.param, str(toml_file))
        self.assertEqual(self.ctx.default_map, {"regex": True})

    def test_fully_resolved_filename_is_returned(self):
        cur_dir = pathlib.Path()
        os.chdir(str(self.data_dir / "config"))
        result = config.read_pyproject_toml(self.ctx, self.param, "")
        os.chdir(str(cur_dir))
        self.assertEqual(result, str(self.data_dir / "config" / "tartufo.toml"))


if __name__ == "__main__":
    unittest.main()
