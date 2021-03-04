import copy
import os
import pathlib
import re
import unittest
from unittest import mock

import click
import toml
from click.testing import CliRunner

from tartufo import config, types
from tartufo.types import Rule

from tests import helpers


class ConfigureRegexTests(unittest.TestCase):
    def test_configure_regexes_rules_files_without_defaults(self):
        rules_path = pathlib.Path(__file__).parent / "data" / "testRules.json"
        rules_files = (rules_path.open(),)
        expected_regexes = {
            "RSA private key 2": Rule(
                name="RSA private key 2",
                pattern=re.compile("-----BEGIN EC PRIVATE KEY-----"),
                path_pattern=None,
            ),
            "Complex Rule": Rule(
                name="Complex Rule",
                pattern=re.compile("complex-rule"),
                path_pattern=re.compile("/tmp/[a-z0-9A-Z]+\\.(py|js|json)"),
            ),
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
        expected_regexes["RSA private key 2"] = Rule(
            name="RSA private key 2",
            pattern=re.compile("-----BEGIN EC PRIVATE KEY-----"),
            path_pattern=None,
        )
        expected_regexes["Complex Rule"] = Rule(
            name="Complex Rule",
            pattern=re.compile("complex-rule"),
            path_pattern=re.compile("/tmp/[a-z0-9A-Z]+\\.(py|js|json)"),
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

    @unittest.skipIf(
        helpers.WINDOWS,
        "Avoiding a race condition/permission error in Windows",
    )
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
            repo_path = mock_pathlib.Path.return_value
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
            repo_path = mock_pathlib.Path.return_value
            repo_path.is_dir.return_value = True
            repo_path.glob.return_value = []
            config.configure_regexes(rules_repo=".", rules_repo_files=("tartufo.json",))
            repo_path.glob.assert_called_once_with("tartufo.json")

    def test_configure_regexes_includes_rules_from_rules_repo(self):
        rules_path = pathlib.Path(__file__).parent / "data"
        actual_regexes = config.configure_regexes(
            include_default=False,
            rules_repo=str(rules_path),
            rules_repo_files=["testRules.json"],
        )
        expected_regexes = {
            "RSA private key 2": Rule(
                name="RSA private key 2",
                pattern=re.compile("-----BEGIN EC PRIVATE KEY-----"),
                path_pattern=None,
            ),
            "Complex Rule": Rule(
                name="Complex Rule",
                pattern=re.compile("complex-rule"),
                path_pattern=re.compile("/tmp/[a-z0-9A-Z]+\\.(py|js|json)"),
            ),
        }

        self.assertEqual(
            expected_regexes,
            actual_regexes,
            "The regexes dictionary should match the test rules "
            "(expected: {}, actual: {})".format(expected_regexes, actual_regexes),
        )


class LoadConfigFromPathTests(unittest.TestCase):
    def setUp(self):
        self.data_dir = pathlib.Path(__file__).parent / "data"
        self.ctx = click.Context(click.Command("foo"))
        self.param = click.Option(["--config"])
        return super().setUp()

    def test_pyproject_toml_is_discovered_if_present(self):
        (config_path, _) = config.load_config_from_path(self.data_dir)
        self.assertEqual(config_path, self.data_dir / "pyproject.toml")

    def test_tartufo_toml_is_discovered_if_present(self):
        (config_path, _) = config.load_config_from_path(self.data_dir / "config")
        self.assertEqual(config_path, self.data_dir / "config" / "tartufo.toml")

    def test_prefer_tartufo_toml_config_if_both_are_present(self):
        (config_path, _) = config.load_config_from_path(self.data_dir / "multiConfig")
        self.assertEqual(config_path, self.data_dir / "multiConfig" / "tartufo.toml")

    def test_specified_file_gets_read(self):
        (config_path, _) = config.load_config_from_path(
            self.data_dir / "config", "other_config.toml"
        )
        self.assertEqual(config_path, self.data_dir / "config" / "other_config.toml")

    @mock.patch("toml.load")
    def test_config_exception_is_raised_if_trouble_reading_file(
        self, mock_toml: mock.MagicMock
    ):
        mock_toml.side_effect = toml.TomlDecodeError("Bad TOML!", "foo", 42)
        with self.assertRaisesRegex(
            types.ConfigException, "Error reading configuration file: Bad TOML!"
        ):
            config.load_config_from_path(self.data_dir)

    def test_parent_directory_not_checked_if_traverse_is_false(self):
        with self.assertRaisesRegex(
            FileNotFoundError,
            f"Could not find config file in {self.data_dir / 'config'}.".replace(
                "\\", "\\\\"
            ),
        ):
            config.load_config_from_path(
                self.data_dir / "config", "pyproject.toml", False
            )

    @mock.patch("toml.load")
    def test_config_keys_are_normalized(self, mock_load: mock.MagicMock):
        mock_load.return_value = {"tool": {"tartufo": {"--repo-path": "."}}}
        (_, data) = config.load_config_from_path(self.data_dir)
        self.assertEqual(data, {"repo_path": "."})


class ReadPyprojectTomlTests(unittest.TestCase):
    def setUp(self):
        self.data_dir = pathlib.Path(__file__).parent / "data"
        self.ctx = click.Context(click.Command("foo"))
        self.param = click.Option(["--config"])
        return super().setUp()

    @mock.patch("tartufo.config.load_config_from_path")
    def test_scan_target_is_searched_for_config_if_found(
        self, mock_load: mock.MagicMock
    ):
        mock_load.return_value = (self.data_dir / "config" / "tartufo.toml", {})
        self.ctx.params["repo_path"] = str(self.data_dir / "config")
        config.read_pyproject_toml(self.ctx, self.param, "")
        mock_load.assert_called_once_with(self.data_dir / "config", "")

    @mock.patch("tartufo.config.load_config_from_path")
    def test_file_error_is_raised_if_specified_file_not_found(
        self, mock_load: mock.MagicMock
    ):
        mock_load.side_effect = FileNotFoundError("No file for you!")
        with self.assertRaisesRegex(click.FileError, "No file for you!"):
            config.read_pyproject_toml(self.ctx, self.param, "foobar.toml")

    @mock.patch("tartufo.config.load_config_from_path")
    def test_none_is_returned_if_file_not_found_and_none_specified(
        self, mock_load: mock.MagicMock
    ):
        mock_load.side_effect = FileNotFoundError("No file for you!")
        self.assertIsNone(config.read_pyproject_toml(self.ctx, self.param, ""))

    @mock.patch("tartufo.config.load_config_from_path")
    def test_file_error_is_raised_if_specified_config_file_cant_be_read(
        self, mock_load: mock.MagicMock
    ):
        cur_dir = pathlib.Path()
        os.chdir(str(self.data_dir))
        mock_load.side_effect = types.ConfigException("Bad TOML!")
        with self.assertRaisesRegex(click.FileError, "Bad TOML!") as exc:
            config.read_pyproject_toml(self.ctx, self.param, "foobar.toml")
            self.assertEqual(exc.exception.filename, str(self.data_dir / "foobar.toml"))
        os.chdir(str(cur_dir))

    @mock.patch("tartufo.config.load_config_from_path")
    def test_file_error_is_raised_if_non_specified_config_file_cant_be_read(
        self, mock_load: mock.MagicMock
    ):
        cur_dir = pathlib.Path()
        os.chdir(str(self.data_dir))
        mock_load.side_effect = types.ConfigException("Bad TOML!")
        with self.assertRaisesRegex(click.FileError, "Bad TOML!") as exc:
            config.read_pyproject_toml(self.ctx, self.param, "")
            self.assertEqual(
                exc.exception.filename, str(self.data_dir / "tartufo.toml")
            )
        os.chdir(str(cur_dir))

    def test_fully_resolved_filename_is_returned(self):
        cur_dir = pathlib.Path()
        os.chdir(str(self.data_dir / "config"))
        result = config.read_pyproject_toml(self.ctx, self.param, "")
        os.chdir(str(cur_dir))
        self.assertEqual(result, str(self.data_dir / "config" / "tartufo.toml"))


class CompilePathRulesTests(unittest.TestCase):
    def test_commented_lines_are_ignored(self):
        rules = config.compile_path_rules(["# Poetry lock file", r"poetry\.lock"])
        self.assertEqual(rules, [re.compile(r"poetry\.lock")])

    def test_whitespace_lines_are_ignored(self):
        rules = config.compile_path_rules(
            [
                "# Poetry lock file",
                r"poetry\.lock",
                "",
                "\t\n",
                "# NPM files",
                r"package-lock\.json",
            ]
        )
        self.assertEqual(
            rules, [re.compile(r"poetry\.lock"), re.compile(r"package-lock\.json")]
        )


if __name__ == "__main__":
    unittest.main()
