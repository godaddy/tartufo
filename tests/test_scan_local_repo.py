import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from tartufo import cli, types


class ScanLocalRepoTests(unittest.TestCase):
    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    def test_scan_exits_gracefully_on_scan_exception(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.side_effect = types.ScanException("Scan failed!")
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["scan-local-repo", "."])
        self.assertGreater(result.exit_code, 0)
        self.assertEqual(result.output, "Scan failed!\n")

    def test_scan_exits_gracefully_when_target_is_not_git_repo(self):
        runner = CliRunner()
        with runner.isolated_filesystem() as dirname:
            result = runner.invoke(cli.main, ["scan-local-repo", "."])
            self.assertEqual(
                result.output,
                f"{Path(dirname).resolve()} is not a valid git repository.\n",
            )

    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    def test_scan_exits_gracefully_when_remote_fetch_fails(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.side_effect = types.GitRemoteException(
            "Fetch failed!"
        )
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["scan-local-repo", "."])
        self.assertGreater(result.exit_code, 0)
        self.assertEqual(
            result.output,
            "There was an error fetching from the remote repository: Fetch failed!\n",
        )
