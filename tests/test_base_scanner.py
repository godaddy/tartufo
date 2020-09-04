import re
import unittest
from unittest import mock

from tartufo import scanner, types
from tartufo.types import GlobalOptions

from tests.helpers import generate_options


class TestScanner(scanner.ScannerBase):  # pylint: disable=too-many-instance-attributes
    """A simple scanner subclass for testing purposes.

    Since `chunks` is an abstract property, we cannot directly instantiate the
    `ScannerBase` class."""

    __test__ = False

    @property
    def chunks(self):
        return ("foo", "bar", "baz")


class ScannerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.options = generate_options(GlobalOptions)


class ScanTests(ScannerTestCase):
    @mock.patch("tartufo.scanner.ScannerBase.scan_entropy")
    def test_scan_iterates_through_all_chunks(self, mock_entropy: mock.MagicMock):
        # Make sure we do at least one type of scan
        self.options.entropy = True
        test_scanner = TestScanner(self.options)
        test_scanner.scan()
        mock_entropy.assert_has_calls(
            (mock.call("foo"), mock.call("bar"), mock.call("baz")), any_order=True
        )

    @mock.patch("tartufo.scanner.ScannerBase.scan_entropy")
    def test_scan_checks_entropy_if_specified(self, mock_entropy: mock.MagicMock):
        self.options.entropy = True
        test_scanner = TestScanner(self.options)
        test_scanner.scan()
        mock_entropy.assert_called()

    @mock.patch("tartufo.scanner.ScannerBase.scan_regex")
    def test_scan_checks_regex_if_specified(self, mock_regex: mock.MagicMock):
        self.options.regex = True
        test_scanner = TestScanner(self.options)
        test_scanner.scan()
        mock_regex.assert_called()


class IssuesTests(ScannerTestCase):
    @mock.patch("tartufo.scanner.ScannerBase.scan")
    def test_empty_issue_list_causes_scan(self, mock_scan: mock.MagicMock):
        test_scanner = TestScanner(self.options)
        test_scanner.issues  # pylint: disable=pointless-statement
        mock_scan.assert_called()

    @mock.patch("tartufo.scanner.ScannerBase.scan")
    def test_populated_issues_list_does_not_rescan(self, mock_scan: mock.MagicMock):
        test_scanner = TestScanner(self.options)
        test_scanner._issues = [  # pylint: disable=protected-access
            scanner.Issue(types.IssueType.RegEx, "foo")
        ]
        test_scanner.issues  # pylint: disable=pointless-statement
        mock_scan.assert_not_called()


class IncludeExcludePathsTests(ScannerTestCase):
    @mock.patch("tartufo.config.compile_path_rules")
    def test_populated_included_paths_list_does_not_recompute(
        self, mock_compile: mock.MagicMock
    ):
        test_scanner = TestScanner(self.options)
        test_scanner._included_paths = []  # pylint: disable=protected-access
        test_scanner.included_paths  # pylint: disable=pointless-statement
        mock_compile.assert_not_called()

    def test_included_paths_is_empty_if_not_specified(self):
        test_scanner = TestScanner(self.options)
        self.assertEqual(test_scanner.included_paths, [])

    @mock.patch("tartufo.config.compile_path_rules")
    def test_include_paths_are_calculated_if_specified(
        self, mock_compile: mock.MagicMock
    ):
        mock_include = mock.MagicMock()
        self.options.include_paths = mock_include
        test_scanner = TestScanner(self.options)
        test_scanner.included_paths  # pylint: disable=pointless-statement
        mock_compile.assert_called_once_with(mock_include.readlines.return_value)

    @mock.patch("tartufo.config.compile_path_rules")
    def test_populated_excluded_paths_list_does_not_recompute(
        self, mock_compile: mock.MagicMock
    ):
        test_scanner = TestScanner(self.options)
        test_scanner._excluded_paths = []  # pylint: disable=protected-access
        test_scanner.excluded_paths  # pylint: disable=pointless-statement
        mock_compile.assert_not_called()

    def test_excluded_paths_is_empty_if_not_specified(self):
        test_scanner = TestScanner(self.options)
        self.assertEqual(test_scanner.excluded_paths, [])

    @mock.patch("tartufo.config.compile_path_rules")
    def test_exclude_paths_are_calculated_if_specified(
        self, mock_compile: mock.MagicMock
    ):
        mock_exclude = mock.MagicMock()
        self.options.exclude_paths = mock_exclude
        test_scanner = TestScanner(self.options)
        test_scanner.excluded_paths  # pylint: disable=pointless-statement
        mock_compile.assert_called_once_with(mock_exclude.readlines.return_value)

    def test_should_scan_treats_included_paths_as_exclusive(self):
        test_scanner = TestScanner(self.options)
        test_scanner._included_paths = [  # pylint: disable=protected-access
            re.compile(r"foo\/(.*)")
        ]
        self.assertFalse(test_scanner.should_scan("bar.txt"))

    def test_should_scan_includes_files_in_matched_paths(self):
        test_scanner = TestScanner(self.options)
        test_scanner._included_paths = [  # pylint: disable=protected-access
            re.compile(r"foo\/(.*)")
        ]
        self.assertTrue(test_scanner.should_scan("foo/bar.txt"))

    def test_should_scan_allows_files_which_are_not_excluded(self):
        test_scanner = TestScanner(self.options)
        test_scanner._excluded_paths = [  # pylint: disable=protected-access
            re.compile(r"foo\/(.*)")
        ]
        self.assertTrue(test_scanner.should_scan("bar.txt"))

    def test_should_scan_excludes_files_in_matched_paths(self):
        test_scanner = TestScanner(self.options)
        test_scanner._excluded_paths = [  # pylint: disable=protected-access
            re.compile(r"foo\/(.*)")
        ]
        self.assertFalse(test_scanner.should_scan("foo/bar.txt"))


class RegexRulesTests(ScannerTestCase):
    @mock.patch("tartufo.config.configure_regexes")
    def test_populated_regex_list_does_not_recompute(
        self, mock_configure: mock.MagicMock
    ):
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = {}  # pylint: disable=protected-access
        test_scanner.rules_regexes  # pylint: disable=pointless-statement
        mock_configure.assert_not_called()

    @mock.patch("tartufo.config.configure_regexes")
    def test_regex_rules_are_computed_when_first_accessed(
        self, mock_configure: mock.MagicMock
    ):
        self.options.default_regexes = True
        self.options.rules = "foo"  # type: ignore
        self.options.git_rules_repo = "bar"
        self.options.git_rules_files = "baz"  # type: ignore
        test_scanner = TestScanner(self.options)
        test_scanner.rules_regexes  # pylint: disable=pointless-statement
        mock_configure.assert_called_once_with(True, "foo", "bar", "baz")


class SignatureTests(ScannerTestCase):
    @mock.patch("tartufo.util.generate_signature")
    def test_matched_signatures_are_excluded(self, mock_signature: mock.MagicMock):
        self.options.exclude_signatures = ("foo",)
        mock_signature.return_value = "foo"
        test_scanner = TestScanner(self.options)
        self.assertTrue(test_scanner.signature_is_excluded("bar", "blah"))

    @mock.patch("tartufo.util.generate_signature")
    def test_unmatched_signatures_are_not_excluded(
        self, mock_signature: mock.MagicMock
    ):
        self.options.exclude_signatures = ("foo",)
        mock_signature.return_value = "bar"
        test_scanner = TestScanner(self.options)
        self.assertFalse(test_scanner.signature_is_excluded("blah", "stuff"))


class RegexScanTests(ScannerTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.options.regex = True
        self.options.default_regexes = True

    def test_all_regex_rules_are_checked(self):
        rule_1 = mock.MagicMock()
        rule_1.findall.return_value = []
        rule_2 = mock.MagicMock()
        rule_2.findall.return_value = []
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = {  # pylint: disable=protected-access
            "foo": rule_1,
            "bar": rule_2,
        }
        chunk = types.Chunk("foo", "bar")
        test_scanner.scan_regex(chunk)
        rule_1.findall.assert_called_once_with("foo")
        rule_2.findall.assert_called_once_with("foo")

    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    def test_issue_is_not_created_if_signature_is_excluded(
        self, mock_signature: mock.MagicMock
    ):
        mock_signature.return_value = True
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = {  # pylint: disable=protected-access
            "foo": re.compile("foo")
        }
        chunk = types.Chunk("foo", "bar")
        issues = test_scanner.scan_regex(chunk)
        mock_signature.assert_called_once_with("foo", "bar")
        self.assertEqual(issues, [])

    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    def test_issue_is_returned_if_signature_is_not_excluded(
        self, mock_signature: mock.MagicMock
    ):
        mock_signature.return_value = False
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = {  # pylint: disable=protected-access
            "foo": re.compile("foo")
        }
        chunk = types.Chunk("foo", "bar")
        issues = test_scanner.scan_regex(chunk)
        mock_signature.assert_called_once_with("foo", "bar")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_detail, "foo")
        self.assertEqual(issues[0].issue_type, types.IssueType.RegEx)
        self.assertEqual(issues[0].matched_string, "foo")


class EntropyTests(ScannerTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.options.entropy = True
        self.chunk = types.Chunk(
            """
        foo bar
        asdfqwer
        """,
            "foo.py",
        )
        self.scanner = TestScanner(self.options)

    def test_calculate_base64_entropy_calculation(self):
        random_string = (
            "ZWVTjPQSdhwRgl204Hc51YCsritMIzn8B=/p9UyeX7xu6KkAGqfm3FJ+oObLDNEva"
        )
        self.assertGreaterEqual(
            self.scanner.calculate_entropy(random_string, scanner.BASE64_CHARS), 4.5
        )

    def test_calculate_hex_entropy_calculation(self):
        random_string = "b3A0a1FDfe86dcCE945B72"
        self.assertGreaterEqual(
            self.scanner.calculate_entropy(random_string, scanner.HEX_CHARS), 3
        )

    def test_empty_string_has_no_entropy(self):
        self.assertEqual(self.scanner.calculate_entropy("", ""), 0.0)

    @mock.patch("tartufo.util.get_strings_of_set")
    def test_scan_entropy_find_b64_strings_for_every_word_in_diff(
        self, mock_strings: mock.MagicMock
    ):
        mock_strings.return_value = []
        self.scanner.scan_entropy(self.chunk)
        mock_strings.assert_has_calls(
            (
                mock.call("foo", scanner.BASE64_CHARS),
                mock.call("foo", scanner.HEX_CHARS),
                mock.call("bar", scanner.BASE64_CHARS),
                mock.call("bar", scanner.HEX_CHARS),
                mock.call("asdfqwer", scanner.BASE64_CHARS),
                mock.call("asdfqwer", scanner.HEX_CHARS),
            )
        )

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.util.get_strings_of_set")
    def test_issues_are_not_created_for_b64_string_excluded_signatures(
        self,
        mock_strings: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = (["foo"], [], [], [], [], [])
        mock_signature.return_value = True
        issues = self.scanner.scan_entropy(self.chunk)
        mock_calculate.assert_not_called()
        self.assertEqual(issues, [])

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.util.get_strings_of_set")
    def test_issues_are_not_created_for_hex_string_excluded_signatures(
        self,
        mock_strings: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = ([], ["foo"], [], [], [], [])
        mock_signature.return_value = True
        issues = self.scanner.scan_entropy(self.chunk)
        mock_calculate.assert_not_called()
        self.assertEqual(issues, [])

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.util.get_strings_of_set")
    def test_issues_are_created_for_high_entropy_b64_strings(
        self,
        mock_strings: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = (["foo"], [], [], [], [], [])
        mock_signature.return_value = False
        mock_calculate.return_value = 9.0
        issues = self.scanner.scan_entropy(self.chunk)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, types.IssueType.Entropy)
        self.assertEqual(issues[0].matched_string, "foo")

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.util.get_strings_of_set")
    def test_issues_are_created_for_high_entropy_hex_strings(
        self,
        mock_strings: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = ([], ["foo"], [], [], [], [])
        mock_signature.return_value = False
        mock_calculate.return_value = 9.0
        issues = self.scanner.scan_entropy(self.chunk)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, types.IssueType.Entropy)
        self.assertEqual(issues[0].matched_string, "foo")

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.util.get_strings_of_set")
    def test_issues_are_not_created_for_low_entropy_b64_strings(
        self,
        mock_strings: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = (["foo"], [], [], [], [], [])
        mock_signature.return_value = False
        mock_calculate.return_value = 1.0
        issues = self.scanner.scan_entropy(self.chunk)
        self.assertEqual(len(issues), 0)

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.util.get_strings_of_set")
    def test_issues_are_not_created_for_low_entropy_hex_strings(
        self,
        mock_strings: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = ([], ["foo"], [], [], [], [])
        mock_signature.return_value = False
        mock_calculate.return_value = 1.0
        issues = self.scanner.scan_entropy(self.chunk)
        self.assertEqual(len(issues), 0)


if __name__ == "__main__":
    unittest.main()
