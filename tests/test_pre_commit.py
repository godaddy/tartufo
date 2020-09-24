import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from tartufo import cli, types


class PreCommitTests(unittest.TestCase):
    @mock.patch("tartufo.commands.pre_commit.GitPreCommitScanner")
    def test_scan_is_executed_against_current_working_directory(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = []
        runner = CliRunner()
        with runner.isolated_filesystem() as tempdir:
            runner.invoke(cli.main, ["pre-commit"])
        self.assertEqual(
            Path(mock_scanner.call_args[0][1]).resolve(), Path(tempdir).resolve()
        )

    @mock.patch("tartufo.commands.pre_commit.GitPreCommitScanner")
    def test_scan_fails_on_scan_exception(self, mock_scanner: mock.MagicMock):
        mock_scanner.return_value.scan.side_effect = types.TartufoScanException(
            "Scan failed!"
        )
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["pre-commit"])
        self.assertEqual(result.output, "Scan failed!\n")
