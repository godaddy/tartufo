import pathlib
import unittest
from unittest import mock

from click.testing import CliRunner
from tartufo import cli, config, scanner


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

    @mock.patch("tartufo.cli.config.configure_regexes")
    def test_command_fails_from_invalid_regex(self, mock_config_regex):
        mock_config_regex.side_effect = ValueError("Foo!")
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["--repo-path", ".", "--regex"])
            self.assertEqual(result.output, "Foo!\n")

    @mock.patch("tartufo.cli.scanner.find_staged")
    def test_command_calls_find_staged_for_pre_commit(self, mock_find_staged):
        mock_find_staged.return_value = {}
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main,
                ["--pre-commit", "--repo-path", "/", "--no-regex", "--entropy"],
            )
            mock_find_staged.assert_called_once_with(
                "/",
                False,
                True,
                custom_regexes={},
                path_inclusions=[],
                path_exclusions=[],
            )

    @mock.patch("tartufo.cli.util.clone_git_repo")
    @mock.patch("tartufo.cli.scanner.scan_repo")
    @mock.patch("tartufo.cli.shutil.rmtree", new=mock.MagicMock())
    def test_command_calls_scan_repo_by_default(self, mock_scan_repo, mock_clone):
        mock_scan_repo.return_value = {}
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main,
                [
                    "--no-regex",
                    "--max-depth",
                    "42",
                    "--entropy",
                    "git@github.com:godaddy/tartufo.git",
                ],
            )
            mock_scan_repo.assert_called_once_with(
                mock_clone.return_value,
                {},
                [],
                [],
                {
                    "config": None,
                    "regex": False,
                    "max_depth": 42,
                    "entropy": True,
                    "git_url": "git@github.com:godaddy/tartufo.git",
                    "json": False,
                    "rules": (),
                    "default_regexes": True,
                    "since_commit": None,
                    "branch": None,
                    "include_paths": None,
                    "exclude_paths": None,
                    "repo_path": None,
                    "cleanup": False,
                    "pre_commit": False,
                    "git_rules_repo": None,
                    "git_rules_files": (),
                },
            )

    @mock.patch("tartufo.cli.util.clone_git_repo")
    @mock.patch("tartufo.cli.scanner.scan_repo")
    @mock.patch("tartufo.cli.shutil.rmtree", new=mock.MagicMock())
    def test_default_regexes_get_used_by_default(self, mock_scan_repo, mock_clone):
        mock_scan_repo.return_value = {}
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main,
                [
                    "--regex",
                    "--max-depth",
                    "42",
                    "--entropy",
                    "git@github.com:godaddy/tartufo.git",
                ],
            )
            mock_scan_repo.assert_called_once_with(
                mock_clone.return_value,
                config.DEFAULT_REGEXES,
                [],
                [],
                {
                    "config": None,
                    "regex": True,
                    "max_depth": 42,
                    "entropy": True,
                    "git_url": "git@github.com:godaddy/tartufo.git",
                    "json": False,
                    "rules": (),
                    "default_regexes": True,
                    "since_commit": None,
                    "branch": None,
                    "include_paths": None,
                    "exclude_paths": None,
                    "repo_path": None,
                    "cleanup": False,
                    "pre_commit": False,
                    "git_rules_repo": None,
                    "git_rules_files": (),
                },
            )

    @mock.patch("tartufo.cli.util.clone_git_repo")
    @mock.patch("tartufo.cli.scanner.scan_repo")
    def test_clone_not_called_when_repo_path_specified(
        self, mock_scan_repo, mock_clone
    ):
        mock_scan_repo.return_value = {}
        runner = CliRunner()
        with runner.isolated_filesystem() as working_dir:
            # Resolve all symlinks etc to give us an absolute path
            working_dir = str(pathlib.Path(working_dir).resolve())
            runner.invoke(
                cli.main,
                ["--no-regex", "--max-depth", "42", "--entropy", "--repo-path", ".",],
            )
            mock_clone.assert_not_called()
            mock_scan_repo.assert_called_once_with(
                working_dir,
                {},
                [],
                [],
                {
                    "config": None,
                    "regex": False,
                    "max_depth": 42,
                    "entropy": True,
                    "git_url": None,
                    "json": False,
                    "rules": (),
                    "default_regexes": True,
                    "since_commit": None,
                    "branch": None,
                    "include_paths": None,
                    "exclude_paths": None,
                    "repo_path": working_dir,
                    "cleanup": False,
                    "pre_commit": False,
                    "git_rules_repo": None,
                    "git_rules_files": (),
                },
            )

    @mock.patch("tartufo.cli.scanner.scan_repo")
    @mock.patch("tartufo.cli.util.clean_outputs")
    @mock.patch("tartufo.cli.util.clone_git_repo", new=mock.MagicMock())
    @mock.patch("tartufo.cli.util.echo_issues", new=mock.MagicMock())
    @mock.patch("tartufo.cli.shutil.rmtree", new=mock.MagicMock())
    def test_command_calls_cleanup_when_requested(self, mock_clean, mock_scan_repo):
        mock_scan_repo.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main,
                [
                    "--cleanup",
                    "--no-regex",
                    "--max-depth",
                    "42",
                    "--entropy",
                    "git@github.com:godaddy/tartufo.git",
                ],
            )
            mock_clean.assert_called_once_with(None)

    @mock.patch("tartufo.cli.config.compile_path_rules")
    @mock.patch("tartufo.cli.util.clone_git_repo", new=mock.MagicMock())
    @mock.patch("tartufo.cli.scanner.scan_repo", new=mock.MagicMock())
    @mock.patch("tartufo.cli.shutil.rmtree", new=mock.MagicMock())
    def test_path_inclusions(self, mock_compile):
        runner = CliRunner()
        with runner.isolated_filesystem():
            include_files = pathlib.Path(__file__).parent / "data" / "include-files"
            runner.invoke(
                cli.main,
                [
                    "-i",
                    str(include_files.resolve()),
                    "--no-regex",
                    "--max-depth",
                    "42",
                    "--entropy",
                    "git@github.com:godaddy/tartufo.git",
                ],
            )
            mock_compile.assert_called_once_with(
                ["# This should be ignored.\n", "tartufo/\n", "scripts/\n"]
            )

    @mock.patch("tartufo.cli.config.compile_path_rules")
    @mock.patch("tartufo.cli.util.clone_git_repo", new=mock.MagicMock())
    @mock.patch("tartufo.cli.scanner.scan_repo", new=mock.MagicMock())
    @mock.patch("tartufo.cli.shutil.rmtree", new=mock.MagicMock())
    def test_path_exclusions(self, mock_compile):
        runner = CliRunner()
        with runner.isolated_filesystem():
            exclude_files = pathlib.Path(__file__).parent / "data" / "exclude-files"
            runner.invoke(
                cli.main,
                [
                    "-x",
                    str(exclude_files.resolve()),
                    "--no-regex",
                    "--max-depth",
                    "42",
                    "--entropy",
                    "git@github.com:godaddy/tartufo.git",
                ],
            )
            mock_compile.assert_called_once_with(
                [
                    "# This should be ignored\n",
                    "tests/\n",
                    "\\.venv/\n",
                    ".*\\.egg-info/\n",
                ]
            )

    @mock.patch("tartufo.cli.mkdtemp")
    @mock.patch("tartufo.cli.scanner.scan_repo")
    @mock.patch("tartufo.cli.util.clone_git_repo", new=mock.MagicMock())
    @mock.patch("tartufo.cli.util.echo_issues", new=mock.MagicMock())
    @mock.patch("tartufo.cli.util.write_outputs", new=mock.MagicMock())
    @mock.patch("tartufo.cli.shutil.rmtree", new=mock.MagicMock())
    def test_issues_path_is_called_out(self, mock_scan_repo, mock_temp):
        mock_scan_repo.return_value = [scanner.Issue(scanner.IssueType.Entropy, [])]
        mock_temp.return_value = "/foo"
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main,
                [
                    "--no-cleanup",
                    "--no-regex",
                    "--entropy",
                    "git@github.com:godaddy/tartufo.git",
                ],
            )
            self.assertEqual(result.output, "Results have been saved in /foo\n")

    @mock.patch("tartufo.cli.scanner.scan_repo")
    @mock.patch("tartufo.cli.util.clone_git_repo", new=mock.MagicMock())
    @mock.patch("tartufo.cli.shutil.rmtree", new=mock.MagicMock())
    def test_command_exits_with_positive_return_code_when_issues_found(
        self, mock_scan_repo
    ):
        mock_scan_repo.return_value = {"found_issues": True}
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["git@github.com:godaddy/tartufo.git"])
            self.assertGreater(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
