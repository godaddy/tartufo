# pylint: disable=protected-access
import pathlib
import unittest
from unittest.mock import patch

import click

from tartufo import scanner
from tartufo.types import GlobalOptions, IssueType
from tests.helpers import generate_options


class FolderScannerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.global_options = generate_options(GlobalOptions)

    def test_scan_should_detect_entropy_and_not_binary(self):
        folder_path = pathlib.Path(__file__).parent / "data/scan_folder"
        self.global_options.entropy = True
        self.global_options.b64_entropy_score = 4.5
        self.global_options.hex_entropy_score = 3
        self.global_options.exclude_signatures = []
        self.global_options.exclude_path_patterns = [r"donotscan\.txt"]

        test_scanner = scanner.FolderScanner(self.global_options, folder_path)
        issues = test_scanner.scan()

        self.assertEqual(1, len(issues))
        self.assertEqual("KQ0I97OBuPlGB9yPRxoSxnX52zE=", issues[0].matched_string)
        self.assertEqual(IssueType.Entropy, issues[0].issue_type)

    def test_scan_should_raise_click_error_on_file_permissions_issues(self):
        folder_path = pathlib.Path(__file__).parent / "data/scan_folder"
        self.global_options.entropy = True
        self.global_options.exclude_signatures = []

        test_scanner = scanner.FolderScanner(self.global_options, folder_path)

        with patch("pathlib.Path.open", side_effect=OSError()):
            self.assertRaises(click.FileError, test_scanner.scan)


if __name__ == "__main__":
    unittest.main()
