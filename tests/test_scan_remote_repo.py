import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from tartufo import cli, types

from tests import helpers


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
        mock_clone.assert_called_once_with("git@github.com:godaddy/tartufo.git", None)

    @mock.patch("tartufo.commands.scan_remote_repo.util.clone_git_repo")
    @mock.patch("tartufo.commands.scan_remote_repo.GitRepoScanner")
    @mock.patch("tartufo.commands.scan_remote_repo.rmtree", new=mock.MagicMock())
    def test_cloned_path_is_scanned(
        self, mock_scanner: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem() as dirname:
            mock_clone.return_value = (Path(dirname), "origin")
            runner.invoke(
                cli.main, ["scan-remote-repo", "git@github.com:godaddy/tartufo.git"]
            )
        self.assertEqual(mock_scanner.call_args[0][2], dirname)

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
        mock_scanner.return_value.scan.return_value = []
        mock_path.return_value.exists.return_value = True
        runner = CliRunner()
        with runner.isolated_filesystem() as dirname:
            mock_clone.return_value = (Path(dirname), "origin")
            runner.invoke(
                cli.main, ["scan-remote-repo", "git@github.com:godaddy/tartufo.git"]
            )
            self.assertEqual(mock_rmtree.call_args[0][0], dirname)

    @mock.patch("tartufo.commands.scan_remote_repo.util.clone_git_repo")
    @mock.patch("tartufo.commands.scan_remote_repo.GitRepoScanner")
    @mock.patch("tartufo.commands.scan_remote_repo.rmtree", new=mock.MagicMock())
    def test_command_fails_on_clone_error(
        self, mock_scanner: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_clone.side_effect = types.GitException("stderr: 'Bad repo. Bad.'")
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
        mock_clone.return_value = (Path("/foo"), "origin")
        mock_scanner.return_value.scan.side_effect = types.ScanException("Scan failed!")
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main, ["scan-remote-repo", "git@github.com:godaddy/tartufo.git"]
            )
        self.assertEqual(result.output, "Scan failed!\n")

    @unittest.skipIf(
        helpers.BROKEN_USER_PATHS, "Skipping due to truncated Windows usernames"
    )
    @mock.patch("tartufo.commands.scan_remote_repo.util.clone_git_repo")
    @mock.patch("tartufo.commands.scan_remote_repo.GitRepoScanner")
    @mock.patch("tartufo.commands.scan_remote_repo.rmtree", new=mock.MagicMock())
    def test_subdir_of_work_dir_is_passed_to_clone_repo(
        self, mock_scanner: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem() as dirname:
            mock_clone.return_value = Path("/foo")
            runner.invoke(
                cli.main,
                [
                    "scan-remote-repo",
                    "--work-dir",
                    dirname,
                    "git@github.com:godaddy/tartufo.git",
                ],
            )
            mock_clone.assert_called_once_with(
                "git@github.com:godaddy/tartufo.git",
                Path(dirname).resolve() / "tartufo.git",
            )
