import pathlib
import re
import unittest

from click.testing import CliRunner
from tartufo import cli

try:
    from unittest import mock
except ImportError:
    import mock  # type: ignore


class CLITests(unittest.TestCase):

    def test_command_exits_gracefully_with_empty_argv(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main)
            self.assertEqual(result.exit_code, 1)

    def test_command_fails_when_no_entropy_or_regex(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["--no-entropy", "--no-regex"])
            self.assertEqual(result.output, "No analysis requested.\n")

    def test_command_fails_when_regex_requested_but_none_available(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main, ["--regex", "--no-default-regexes", "--repo-path", "."]
            )
            self.assertEqual(
                result.output, "Regex checks requested, but no regexes found.\n"
            )

    @mock.patch("tartufo.cli.config.configure_regexes_from_args")
    def test_command_fails_from_invalid_regex(self, mock_config_regex):
        mock_config_regex.side_effect = ValueError("Foo!")
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main, ["--repo-path", "."]
            )
            self.assertEqual(result.output, "Foo!\n")

    @mock.patch("tartufo.cli.scanner.find_staged")
    def test_command_calls_find_staged_for_pre_commit(
            self, mock_find_staged
    ):
        mock_find_staged.return_value = {}
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main, ["--pre-commit", "--repo-path", "/", "--no-regex", "--entropy"]
            )
            mock_find_staged.assert_called_once_with(
                "/",
                False,
                False,
                True,
                custom_regexes={},
                suppress_output=False,
                path_inclusions=[],
                path_exclusions=[]
            )

    @mock.patch("tartufo.cli.scanner.find_strings")
    def test_command_calls_find_strings_by_default(
            self, mock_find_strings
    ):
        mock_find_strings.return_value = {}
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main, ["--no-regex", "--max-depth", "42", "--entropy", "git@github.com:godaddy/tartufo.git"]
            )
            mock_find_strings.assert_called_once_with(
                "git@github.com:godaddy/tartufo.git",
                None,
                42,
                False,
                False,
                True,
                custom_regexes={},
                suppress_output=False,
                branch=None,
                repo_path=None,
                path_inclusions=[],
                path_exclusions=[]
            )

    @mock.patch("tartufo.cli.scanner.find_strings")
    @mock.patch("tartufo.cli.util.clean_outputs")
    def test_command_calls_cleanup_when_requested(
            self, mock_clean, mock_find_strings
    ):
        mock_find_strings.return_value = {"foo": "bar"}
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main,
                ["--cleanup", "--no-regex", "--max-depth", "42", "--entropy", "git@github.com:godaddy/tartufo.git"]
            )
            mock_clean.assert_called_once_with({"foo": "bar"})

    @mock.patch("tartufo.cli.scanner.find_strings")
    def test_path_inclusions(self, mock_find_strings):
        mock_find_strings.return_value = {}
        runner = CliRunner()
        with runner.isolated_filesystem():
            include_files = pathlib.Path(__file__).parent / "data" / "include-files"
            runner.invoke(
                cli.main,
                [
                    "-i",
                    include_files.resolve(),
                    "--no-regex",
                    "--max-depth",
                    "42",
                    "--entropy",
                    "git@github.com:godaddy/tartufo.git"
                ]
            )
            mock_find_strings.assert_called_once_with(
                "git@github.com:godaddy/tartufo.git",
                None,
                42,
                False,
                False,
                True,
                custom_regexes={},
                suppress_output=False,
                branch=None,
                repo_path=None,
                path_inclusions=[re.compile("tartufo/"), re.compile("scripts/")],
                path_exclusions=[]
            )

    @mock.patch("tartufo.cli.scanner.find_strings")
    def test_path_exclusions(self, mock_find_strings):
        mock_find_strings.return_value = {}
        runner = CliRunner()
        with runner.isolated_filesystem():
            exclude_files = pathlib.Path(__file__).parent / "data" / "exclude-files"
            runner.invoke(
                cli.main,
                [
                    "-x",
                    exclude_files.resolve(),
                    "--no-regex",
                    "--max-depth",
                    "42",
                    "--entropy",
                    "git@github.com:godaddy/tartufo.git"
                ]
            )
            mock_find_strings.assert_called_once_with(
                "git@github.com:godaddy/tartufo.git",
                None,
                42,
                False,
                False,
                True,
                custom_regexes={},
                suppress_output=False,
                branch=None,
                repo_path=None,
                path_inclusions=[],
                path_exclusions=[re.compile("tests/"), re.compile(r".*\.egg-info/"), re.compile(r"\.venv/")]
            )

    @mock.patch("tartufo.cli.scanner.find_strings")
    def test_issues_path_is_called_out(self, mock_find_strings):
        mock_find_strings.return_value = {"issues_path": "/foo"}
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main,
                ["git@github.com:godaddy/tartufo.git"]
            )
            self.assertEqual(result.output, "Results have been saved in /foo\n")

    @mock.patch("tartufo.cli.scanner.find_strings")
    def test_command_exits_with_positive_return_code_when_issues_found(self, mock_find_strings):
        mock_find_strings.return_value = {"found_issues": True}
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main,
                ["git@github.com:godaddy/tartufo.git"]
            )
            self.assertGreater(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
