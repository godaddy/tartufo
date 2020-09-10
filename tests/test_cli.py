import pathlib
import unittest
from unittest import mock

from click.testing import CliRunner
from tartufo import cli, scanner, types


class CLITests(unittest.TestCase):
    repo_path: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_path = str(pathlib.Path(__file__).parent.parent)

    def test_command_exits_gracefully_with_empty_argv(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main)
            self.assertEqual(result.exit_code, 1)

    def test_command_fails_when_no_entropy_or_regex(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main, ["--no-entropy", "--no-regex", "--repo-path", self.repo_path]
            )
            self.assertEqual(result.output, "No analysis requested.\n")

    def test_command_fails_when_regex_requested_but_none_available(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main,
                ["--regex", "--no-default-regexes", "--repo-path", self.repo_path],
            )
            self.assertEqual(
                result.output, "Regex checks requested, but no regexes found.\n"
            )

    @mock.patch("tartufo.cli.config.configure_regexes")
    def test_command_fails_from_invalid_regex(self, mock_config_regex: mock.MagicMock):
        mock_config_regex.side_effect = ValueError("Foo!")
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["--repo-path", self.repo_path, "--regex"])
            self.assertEqual(result.output, "Foo!\n")

    @mock.patch("tartufo.scanner.GitPreCommitScanner")
    def test_command_uses_git_pre_commit_scanner_for_pre_commit(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main,
                [
                    "--pre-commit",
                    "--repo-path",
                    self.repo_path,
                    "--no-regex",
                    "--entropy",
                ],
            )
            mock_scanner.assert_called_once()

    @mock.patch("tartufo.util.clone_git_repo", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.GitRepoScanner")
    @mock.patch("tartufo.cli.shutil.rmtree", new=mock.MagicMock())
    def test_command_uses_git_repo_scanner_by_default(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = []
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
            mock_scanner.assert_called_once()

    @mock.patch("tartufo.util.clone_git_repo", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.GitRepoScanner")
    @mock.patch("tartufo.cli.shutil.rmtree", new=mock.MagicMock())
    def test_default_regexes_get_used_by_default(self, mock_scanner: mock.MagicMock):
        mock_scanner.return_value.scan.return_value = []
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
            options: types.GitOptions = mock_scanner.call_args[0][0]
            self.assertTrue(options.default_regexes)

    @mock.patch("tartufo.util.clone_git_repo")
    @mock.patch("tartufo.scanner.GitRepoScanner")
    def test_clone_not_called_when_repo_path_specified(
        self, mock_scanner: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem() as working_dir:
            # Resolve all symlinks etc to give us an absolute path
            working_dir = str(pathlib.Path(working_dir).resolve())
            runner.invoke(
                cli.main,
                ["--no-regex", "--max-depth", "42", "--entropy", "--repo-path", ".",],
            )
            mock_clone.assert_not_called()
            mock_scanner.assert_called_once()

    @mock.patch("tartufo.scanner.GitRepoScanner")
    @mock.patch("tartufo.util.clean_outputs")
    @mock.patch("tartufo.util.clone_git_repo", new=mock.MagicMock())
    @mock.patch("tartufo.util.echo_issues", new=mock.MagicMock())
    @mock.patch("tartufo.cli.shutil.rmtree", new=mock.MagicMock())
    def test_command_calls_cleanup_when_requested(
        self, mock_clean: mock.MagicMock, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = []
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

    @mock.patch("tartufo.cli.mkdtemp")
    @mock.patch("tartufo.scanner.GitRepoScanner")
    @mock.patch("tartufo.util.clone_git_repo", new=mock.MagicMock())
    @mock.patch("tartufo.util.echo_issues", new=mock.MagicMock())
    @mock.patch("tartufo.util.write_outputs", new=mock.MagicMock())
    @mock.patch("tartufo.cli.shutil.rmtree", new=mock.MagicMock())
    def test_issues_path_is_called_out(
        self, mock_scanner: mock.MagicMock, mock_temp: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = [
            scanner.Issue(types.IssueType.Entropy, "", types.Chunk("foo", "/bar"))
        ]
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

    @mock.patch("tartufo.scanner.GitRepoScanner")
    @mock.patch("tartufo.util.clone_git_repo", new=mock.MagicMock())
    @mock.patch("tartufo.cli.shutil.rmtree", new=mock.MagicMock())
    def test_command_exits_with_positive_return_code_when_issues_found(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = [
            scanner.Issue(types.IssueType.Entropy, "", types.Chunk("foo", "/bar"))
        ]
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["git@github.com:godaddy/tartufo.git"])
            self.assertGreater(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
