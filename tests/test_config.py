from __future__ import unicode_literals

import copy
import os
import re
import unittest

import click
from click.testing import CliRunner

from tartufo import config

try:
    import pathlib
except ImportError:
    import pathlib2 as pathlib  # type: ignore

try:
    from unittest import mock
except ImportError:
    import mock  # type: ignore


class ConfigureRegexTests(unittest.TestCase):
    def test_configure_regexes_rules_files_without_defaults(self):
        rules_path = pathlib.Path(__file__).parent / "data" / "testRules.json"
        rules_files = (rules_path.open(),)
        expected_regexes = {
            "RSA private key 2": re.compile("-----BEGIN EC PRIVATE KEY-----")
        }

        actual_regexes = config.configure_regexes(
            include_default=False, rules_files=rules_files
        )

        self.assertEqual(
            expected_regexes,
            actual_regexes,
            "The regexes dictionary should match the test rules "
            "(expected: {}, actual: {})".format(expected_regexes, actual_regexes),
        )

    def test_configure_regexes_rules_files_with_defaults(self):
        rules_path = pathlib.Path(__file__).parent / "data" / "testRules.json"
        rules_files = (rules_path.open(),)
        expected_regexes = copy.copy(config.DEFAULT_REGEXES)
        expected_regexes["RSA private key 2"] = re.compile(
            "-----BEGIN EC PRIVATE KEY-----"
        )

        actual_regexes = config.configure_regexes(
            include_default=True, rules_files=rules_files
        )

        self.assertEqual(
            expected_regexes,
            actual_regexes,
            "The regexes dictionary should match the test rules "
            "(expected: {}, actual: {})".format(expected_regexes, actual_regexes),
        )

    def test_configure_regexes_returns_just_default_regexes_by_default(self):
        actual_regexes = config.configure_regexes()

        self.assertEqual(
            config.DEFAULT_REGEXES,
            actual_regexes,
            "The regexes dictionary should not have been changed when no rules files are specified",
        )

    @mock.patch("tartufo.config.util.clone_git_repo")
    def test_configure_regexes_does_not_clone_if_local_rules_repo_defined(
        self, mock_clone
    ):
        runner = CliRunner()
        with runner.isolated_filesystem():
            config.configure_regexes(rules_repo=".")
        mock_clone.assert_not_called()

    @mock.patch("tartufo.config.util.clone_git_repo")
    def test_configure_regexes_clones_git_rules_repo(self, mock_clone):
        runner = CliRunner()
        with runner.isolated_filesystem():
            mock_clone.return_value = pathlib.Path(".").resolve()
            config.configure_regexes(rules_repo="git@github.com:godaddy/tartufo.git")
        mock_clone.assert_called_once_with("git@github.com:godaddy/tartufo.git")

    @mock.patch("tartufo.config.pathlib")
    def test_configure_regexes_grabs_all_json_from_rules_repo_by_default(
        self, mock_pathlib
    ):
        runner = CliRunner()
        with runner.isolated_filesystem():
            repo_path = mock_pathlib.Path.return_value.resolve.return_value
            repo_path.is_dir.return_value = True
            repo_path.glob.return_value = []
            config.configure_regexes(rules_repo=".")
            repo_path.glob.assert_called_once_with("*.json")

    @mock.patch("tartufo.config.pathlib")
    def test_configure_regexes_grabs_specified_rules_files_from_repo(
        self, mock_pathlib
    ):
        runner = CliRunner()
        with runner.isolated_filesystem():
            repo_path = mock_pathlib.Path.return_value.resolve.return_value
            repo_path.is_dir.return_value = True
            repo_path.glob.return_value = []
            config.configure_regexes(rules_repo=".", rules_repo_files=("tartufo.json",))
            repo_path.glob.assert_called_once_with("tartufo.json")


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
