# pylint: disable=protected-access
import pathlib
import unittest

from tartufo import scanner
from tartufo.types import GlobalOptions, FolderOptions, IssueType
from tests.helpers import generate_options


class FolderScannerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.global_options = generate_options(GlobalOptions)
        self.folder_options = generate_options(FolderOptions)

    def test_scan_should_detect_entropy_and_not_binary(self):
        folder_path = pathlib.Path(__file__).parent / "data/scan_folder"
        self.folder_options.pattern = "*"
        self.global_options.entropy = True
        self.global_options.exclude_signatures = []

        test_scanner = scanner.FolderScanner(
            self.global_options, self.folder_options, folder_path
        )
        issues = test_scanner.scan()

        self.assertEqual(1, len(issues))
        self.assertEqual("KQ0I97OBuPlGB9yPRxoSxnX52zE=", issues[0].matched_string)
        self.assertEqual(IssueType.Entropy, issues[0].issue_type)


if __name__ == "__main__":
    unittest.main()
