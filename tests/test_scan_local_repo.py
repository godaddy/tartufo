import unittest
from unittest import mock

from click.testing import CliRunner

from tartufo import cli, types


class ScanLocalRepoTests(unittest.TestCase):
    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    def test_scan_exits_gracefully_on_scan_exception(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.side_effect = types.TartufoScanException(
            "Scan failed!"
        )
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
                result.output, f"{dirname} is not a valid git repository.\n"
            )
