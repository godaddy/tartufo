import unittest
from unittest import mock

from click.testing import CliRunner

from tartufo import cli, types


class ScanFolderTests(unittest.TestCase):
    @mock.patch("tartufo.commands.scan_folder.FolderScanner")
    def test_scan_exits_gracefully_on_scan_exception(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.side_effect = types.ScanException("Scan failed!")
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["scan-folder", "."])
        self.assertGreater(result.exit_code, 0)
        self.assertEqual(result.output, "Scan failed!\n")

    def test_scan_exits_gracefully_when_folder_does_not_exist(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            scan_folder = "./bad-path"
            result = runner.invoke(cli.main, ["scan-folder", scan_folder])
            self.assertGreater(result.exit_code, 0)
            self.assertIn(
                f"Error: Invalid value for 'FOLDER_PATH': Directory '{scan_folder}' does not exist.\n",
                result.output,
            )
