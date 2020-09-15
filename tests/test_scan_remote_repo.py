import unittest
from unittest import mock

from git.exc import GitCommandError
from click.testing import CliRunner

from tartufo import cli, types


class ScanRemoteRepoTests(unittest.TestCase):
    @mock.patch("tartufo.commands.scan_remote_repo.util.clone_git_repo")
    @mock.patch("tartufo.commands.scan_remote_repo.GitRepoScanner")
    @mock.patch("tartufo.commands.scan_remote_repo.rmtree", new=mock.MagicMock())
    def test_scan_clones_remote_repo(
        self, mock_scanner: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main, ["scan-remote-repo", "git@github.com:godaddy/tartufo.git"]
            )
        mock_clone.assert_called_once_with("git@github.com:godaddy/tartufo.git")

    @mock.patch("tartufo.commands.scan_remote_repo.util.clone_git_repo")
    @mock.patch("tartufo.commands.scan_remote_repo.GitRepoScanner")
    @mock.patch("tartufo.commands.scan_remote_repo.rmtree", new=mock.MagicMock())
    def test_cloned_path_is_scanned(
        self, mock_scanner: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_clone.return_value = "/foo"
        mock_scanner.return_value.scan.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main, ["scan-remote-repo", "git@github.com:godaddy/tartufo.git"]
            )
        self.assertEqual(mock_scanner.call_args[0][2], "/foo")

    @mock.patch("tartufo.commands.scan_remote_repo.util.clone_git_repo")
    @mock.patch("tartufo.commands.scan_remote_repo.GitRepoScanner")
    @mock.patch("tartufo.commands.scan_remote_repo.Path")
    @mock.patch("tartufo.commands.scan_remote_repo.rmtree")
    def test_clone_is_deleted_after_scan(
        self,
        mock_rmtree: mock.MagicMock,
        mock_path: mock.MagicMock,
        mock_scanner: mock.MagicMock,
        mock_clone: mock.MagicMock,
    ):
        mock_clone.return_value = "/foo"
        mock_scanner.return_value.scan.return_value = []
        mock_path.return_value.exists.return_value = True
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main, ["scan-remote-repo", "git@github.com:godaddy/tartufo.git"]
            )
        self.assertEqual(mock_rmtree.call_args[0][0], "/foo")

    @mock.patch("tartufo.commands.scan_remote_repo.util.clone_git_repo")
    @mock.patch("tartufo.commands.scan_remote_repo.GitRepoScanner")
    @mock.patch("tartufo.commands.scan_remote_repo.rmtree", new=mock.MagicMock())
    def test_command_fails_on_clone_error(
        self, mock_scanner: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_clone.side_effect = GitCommandError(
            command="git clone", status=42, stderr="Bad repo. Bad."
        )
        mock_scanner.return_value.scan.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main, ["scan-remote-repo", "git@github.com:godaddy/tartufo.git"]
            )
        self.assertEqual(
            result.output, "Error cloning remote repo: stderr: 'Bad repo. Bad.'\n"
        )

    @mock.patch("tartufo.commands.scan_remote_repo.util.clone_git_repo")
    @mock.patch("tartufo.commands.scan_remote_repo.GitRepoScanner")
    @mock.patch("tartufo.commands.scan_remote_repo.rmtree", new=mock.MagicMock())
    def test_command_fails_on_scan_exception(
        self, mock_scanner: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_clone.return_value = "/foo"
        mock_scanner.return_value.scan.side_effect = types.TartufoScanException(
            "Scan failed!"
        )
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main, ["scan-remote-repo", "git@github.com:godaddy/tartufo.git"]
            )
        self.assertEqual(result.output, "Scan failed!\n")
