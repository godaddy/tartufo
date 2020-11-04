import unittest
from unittest import mock

from click.testing import CliRunner

from tartufo import cli, types

from tests import helpers


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

    @unittest.skipIf(
        helpers.BROKEN_USER_PATHS, "Skipping due to truncated Windows usernames"
    )
    def test_scan_exits_gracefully_when_target_is_not_git_repo(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["scan-local-repo", "."])
            self.assertRegex(result.output, "is not a valid git repository")

    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    def test_scan_exits_gracefully_when_remote_fetch_fails(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.side_effect = types.GitRemoteException(
            "Could not locate working ssh credentials"
        )
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["scan-local-repo", "."])
        self.assertGreater(result.exit_code, 0)
        self.assertEqual(
            result.output,
            "There was an error fetching from the remote repository: Could not locate working ssh credentials\n",
        )
