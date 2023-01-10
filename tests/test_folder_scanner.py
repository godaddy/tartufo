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
        folder_path = pathlib.Path(__file__).parent / "data" / "scan_folder"
        recurse = True
        self.global_options.entropy = True
        self.global_options.exclude_signatures = ()
        self.global_options.exclude_path_patterns = [
            {"path-pattern": r"donotscan\.txt", "reason": "Reason to be excluded"}
        ]
        self.global_options.buffer_size = 50000

        test_scanner = scanner.FolderScanner(self.global_options, folder_path, recurse)
        issues = list(test_scanner.scan())

        self.assertEqual(2, len(issues))
        actual_issues = [issue.matched_string for issue in issues]
        self.assertIn("KQ0I97OBuPlGB9yPRxoSxnX52zE=", actual_issues)
        self.assertIn(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",
            actual_issues,
        )
        self.assertEqual(IssueType.Entropy, issues[0].issue_type)

    def test_scan_should_raise_click_error_on_file_permissions_issues(self):
        folder_path = pathlib.Path(__file__).parent / "data" / "scan_folder"
        recurse = True
        self.global_options.entropy = True
        self.global_options.exclude_signatures = ()

        test_scanner = scanner.FolderScanner(self.global_options, folder_path, recurse)

        with patch("pathlib.Path.open", side_effect=OSError()):
            with self.assertRaises(click.FileError):
                list(test_scanner.scan())

    def test_scan_all_the_files_recursively(self):
        folder_path = pathlib.Path(__file__).parent / "data" / "scan_folder"
        recurse = True
        self.global_options.entropy = True
        self.global_options.exclude_signatures = ()
        self.global_options.buffer_size = 50000

        test_scanner = scanner.FolderScanner(self.global_options, folder_path, recurse)
        issues = list(test_scanner.scan())

        self.assertEqual(3, len(issues))
        actual_issues = [issue.matched_string for issue in issues]
        self.assertEqual(2, actual_issues.count("KQ0I97OBuPlGB9yPRxoSxnX52zE="))
        self.assertIn(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",
            actual_issues,
        )

    def test_scan_only_root_level_files(self):
        folder_path = pathlib.Path(__file__).parent / "data" / "scan_folder"
        recurse = False
        self.global_options.entropy = True
        self.global_options.exclude_signatures = ()
        self.global_options.buffer_size = 50000

        test_scanner = scanner.FolderScanner(self.global_options, folder_path, recurse)
        issues = list(test_scanner.scan())

        self.assertEqual(2, len(issues))
        actual_issues = [issue.matched_string for issue in issues]
        self.assertEqual(2, actual_issues.count("KQ0I97OBuPlGB9yPRxoSxnX52zE="))


if __name__ == "__main__":
    unittest.main()
