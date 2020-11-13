import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from tartufo import cli, types

from tests import helpers


class ScanRemoteRepoTests(unittest.TestCase):
    @mock.patch("tartufo.util.get_repository")
    @mock.patch("tartufo.commands.scan_remote_repo.GitRemoteRepoScanner.scan")
    @mock.patch(
        "tartufo.commands.scan_remote_repo.GitRemoteRepoScanner.load_config",
        new=mock.MagicMock(),
    )
    @mock.patch("tartufo.commands.scan_remote_repo.rmtree", new=mock.MagicMock())
    def test_scan_clones_remote_repo(
        self, mock_scanner: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_scanner.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main, ["scan-remote-repo", "git@github.com:godaddy/tartufo.git"]
            )
        mock_clone.assert_called_once_with("git@github.com:godaddy/tartufo.git")

    @mock.patch("tartufo.commands.scan_remote_repo.GitRemoteRepoScanner")
    @mock.patch("tartufo.commands.scan_remote_repo.rmtree")
    def test_clone_is_deleted_after_scan(
        self, mock_rmtree: mock.MagicMock, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem() as dirname:
            mock_scanner.return_value.clone_path = Path(dirname)
            runner.invoke(
                cli.main, ["scan-remote-repo", "git@github.com:godaddy/tartufo.git"]
            )
            self.assertEqual(mock_rmtree.call_args[0][0], dirname)

    @mock.patch("tartufo.util.get_repository")
    @mock.patch("tartufo.commands.scan_remote_repo.GitRemoteRepoScanner.scan")
    @mock.patch(
        "tartufo.commands.scan_remote_repo.GitRemoteRepoScanner.load_config",
        new=mock.MagicMock(),
    )
    @mock.patch("tartufo.commands.scan_remote_repo.rmtree", new=mock.MagicMock())
    def test_command_fails_on_clone_error(
        self, mock_scan: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_clone.side_effect = types.GitException("stderr: 'Bad repo. Bad.'")
        mock_scan.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main, ["scan-remote-repo", "git@github.com:godaddy/tartufo.git"]
            )
        self.assertEqual(
            result.output, "Error cloning remote repo: stderr: 'Bad repo. Bad.'\n"
        )

    @mock.patch("tartufo.commands.scan_remote_repo.util.get_repository")
    @mock.patch("tartufo.commands.scan_remote_repo.GitRemoteRepoScanner")
    @mock.patch("tartufo.commands.scan_remote_repo.rmtree", new=mock.MagicMock())
    def test_command_fails_on_scan_exception(
        self, mock_scanner: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_clone.return_value = (Path("/foo"), None)
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
    @mock.patch("tartufo.util.get_repository")
    @mock.patch("tartufo.commands.scan_remote_repo.GitRemoteRepoScanner.scan")
    @mock.patch(
        "tartufo.commands.scan_remote_repo.GitRemoteRepoScanner.load_config",
        new=mock.MagicMock(),
    )
    @mock.patch("tartufo.commands.scan_remote_repo.rmtree", new=mock.MagicMock())
    def test_subdir_of_work_dir_is_passed_to_clone_repo(
        self, mock_scanner: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_scanner.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem() as dirname:
            mock_clone.return_value = (Path("/foo"), None)
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
                str(Path(dirname).resolve() / "tartufo.git"),
            )
