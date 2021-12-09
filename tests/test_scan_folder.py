import pathlib
import unittest
from unittest import mock

import click
from click.testing import CliRunner

from tartufo import cli, types
from tartufo.scanner import FolderScanner
from tartufo.types import GlobalOptions
from tests.helpers import generate_options


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
                f"Error: Invalid value for 'TARGET': Directory '{scan_folder}' does not exist.\n",
                result.output,
            )

    def test_filename_added_to_chunk_when_scan_filename_enabled(self):
        path = pathlib.Path(__file__).parent / "data" / "scan_folder"
        options = generate_options(GlobalOptions, scan_filenames=True)
        scanner = FolderScanner(options, str(path), True)
        for chunk in scanner.chunks:
            file_path = chunk.file_path
            try:
                with pathlib.Path(f"{str(path)}/{file_path}").open("rb") as fhd:
                    data = fhd.read().decode("utf-8")
            except OSError as exc:
                raise click.FileError(filename=str(file_path), hint=str(exc))
            self.assertEqual(chunk.contents, f"{chunk.file_path}\n{data}")

    def test_filename_not_added_to_chunk_when_scan_filename_disabled(self):
        path = pathlib.Path(__file__).parent / "data" / "scan_folder"
        options = generate_options(GlobalOptions, scan_filenames=False)
        scanner = FolderScanner(options, str(path), True)
        for chunk in scanner.chunks:
            file_path = chunk.file_path
            try:
                with pathlib.Path(f"{str(path)}/{file_path}").open("rb") as fhd:
                    data = fhd.read().decode("utf-8")
            except OSError as exc:
                raise click.FileError(filename=str(file_path), hint=str(exc))
            self.assertEqual(chunk.contents, data)
