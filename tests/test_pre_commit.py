import unittest
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from tartufo import cli, scanner, types

from tests.helpers import generate_options


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
        mock_scanner.return_value.scan.side_effect = types.ScanException("Scan failed!")
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["pre-commit"])
        self.assertEqual(result.output, "Scan failed!\n")


class GitPreCommitScannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.global_options = generate_options(types.GlobalOptions)
        return super().setUp()

    @mock.patch("pygit2.Repository")
    @mock.patch("tartufo.scanner.GitPreCommitScanner.filter_submodules")
    def test_load_repo_filters_submodules_when_specified(
        self, mock_filter: mock.MagicMock, mock_repo: mock.MagicMock
    ):
        scanner.GitPreCommitScanner(self.global_options, ".", include_submodules=False)
        mock_filter.assert_called_once_with(mock_repo.return_value)

    @mock.patch("pygit2.Repository", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.GitPreCommitScanner.filter_submodules")
    def test_load_repo_does_not_filter_submodules_when_requested(
        self, mock_filter: mock.MagicMock
    ):
        scanner.GitPreCommitScanner(self.global_options, ".", include_submodules=True)
        mock_filter.assert_not_called()
