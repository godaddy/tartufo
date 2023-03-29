import re
import string
import unittest
from unittest import mock

from tartufo import scanner, types
from tartufo.scanner import Issue
from tartufo.types import GlobalOptions, Rule, MatchType

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
    def test_scan_aborts_when_no_entropy_or_regex(self):
        self.options.entropy = False
        self.options.regex = False
        test_scanner = TestScanner(self.options)
        with self.assertRaisesRegex(types.ConfigException, "No analysis requested."):
            list(test_scanner.scan())

    def test_scan_aborts_when_regex_requested_but_none_found(self):
        self.options.regex = True
        self.options.default_regexes = False
        test_scanner = TestScanner(self.options)
        with self.assertRaisesRegex(
            types.ConfigException, "Regex checks requested, but no regexes found."
        ):
            list(test_scanner.scan())

    @mock.patch("tartufo.config.configure_regexes")
    def test_scan_aborts_due_to_invalid_regex(self, mock_config: mock.MagicMock):
        self.options.regex = True
        test_scanner = TestScanner(self.options)
        mock_config.side_effect = re.error(  # type: ignore
            msg="Invalid regular expression", pattern="42"
        )
        with self.assertRaisesRegex(
            types.ConfigException, "Invalid regular expression"
        ):
            list(test_scanner.scan())

    @mock.patch("tartufo.scanner.ScannerBase.scan_entropy")
    def test_scan_iterates_through_all_chunks(self, mock_entropy: mock.MagicMock):
        # Make sure we do at least one type of scan
        self.options.entropy = True
        test_scanner = TestScanner(self.options)
        list(test_scanner.scan())
        mock_entropy.assert_has_calls(
            (
                mock.call("foo"),
                mock.call("bar"),
                mock.call("baz"),
            ),
            any_order=True,
        )

    @mock.patch("tartufo.scanner.ScannerBase.scan_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.scan_regex")
    def test_scan_does_not_rescan(self, mock_regex, mock_entropy):
        """Make sure scan() does not rescan"""

        self.options.regex = True
        self.options.entropy = True
        test_scanner = TestScanner(self.options)
        test_scanner._completed = True  # pylint: disable=protected-access
        test_scanner._issue_list = [1, 2, 3]  # pylint: disable=protected-access
        test_scanner._issue_count = 3  # pylint: disable=protected-access
        test_scanner._issue_file = None  # pylint: disable=protected-access
        result = list(test_scanner.scan())
        mock_regex.assert_not_called()
        mock_entropy.assert_not_called()
        self.assertEqual(result, [1, 2, 3])

    @mock.patch("tartufo.scanner.ScannerBase.scan_entropy")
    def test_scan_checks_entropy_if_specified(self, mock_entropy: mock.MagicMock):
        self.options.entropy = True
        test_scanner = TestScanner(self.options)
        list(test_scanner.scan())
        mock_entropy.assert_called()

    @mock.patch("tartufo.scanner.ScannerBase.scan_regex")
    def test_scan_checks_regex_if_specified(self, mock_regex: mock.MagicMock):
        self.options.regex = True
        self.options.default_regexes = True
        test_scanner = TestScanner(self.options)
        list(test_scanner.scan())
        mock_regex.assert_called()


class IssueFileTests(ScannerTestCase):
    @mock.patch("tempfile.NamedTemporaryFile")
    def test_issue_file_creates_new_temporary_file(self, mock_temp: mock.MagicMock):
        self.options.temp_dir = "/foo/bar"
        test_scanner = TestScanner(self.options)
        issue_file = test_scanner.issue_file
        mock_temp.assert_called_once_with(dir="/foo/bar")
        self.assertEqual(issue_file, mock_temp.return_value)

    @mock.patch("tempfile.NamedTemporaryFile", mock.MagicMock())
    def test_issue_file_is_cached(self):
        self.options.temp_dir = "/foo/bar"
        test_scanner = TestScanner(self.options)
        file1 = test_scanner.issue_file
        file2 = test_scanner.issue_file
        self.assertEqual(file1, file2)


class IssuesTests(ScannerTestCase):
    @mock.patch("tartufo.scanner.ScannerBase.scan")
    def test_empty_issue_list_causes_scan(self, mock_scan: mock.MagicMock):
        test_scanner = TestScanner(self.options)
        list(test_scanner.issues)  # pylint: disable=pointless-statement
        mock_scan.assert_called()


class IssueTests(unittest.TestCase):
    def test_as_dict_returns_dictionary(self):
        issue = Issue(
            types.IssueType.Entropy,
            "test-string",
            types.Chunk(
                "test-contents", "test-file", {"test-meta1": "test-meta-value"}, True
            ),
        )
        issue.issue_detail = "issue-detail"
        actual = issue.as_dict()
        self.assertEqual(
            {
                "diff": "test-contents",
                "file_path": "test-file",
                "issue_detail": "issue-detail",
                "issue_type": "High Entropy",
                "matched_string": "test-string",
                "signature": "bf09b8c7e62db27c45e618f4aa9d8b13bf91cf3de593b11c1fb515e8b1003ca8",
                "test-meta1": "test-meta-value",
            },
            actual,
        )

    def test_as_dict_returns_compact_dictionary(self):
        issue = Issue(
            types.IssueType.Entropy,
            "test-string",
            types.Chunk(
                "test-contents", "test-file", {"test-meta1": "test-meta-value"}, True
            ),
        )
        issue.issue_detail = "issue-detail"
        actual = issue.as_dict(compact=True)
        self.assertEqual(
            {
                "file_path": "test-file",
                "issue_detail": "issue-detail",
                "issue_type": "High Entropy",
                "matched_string": "test-string",
                "signature": "bf09b8c7e62db27c45e618f4aa9d8b13bf91cf3de593b11c1fb515e8b1003ca8",
            },
            actual,
        )


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
        self.options.include_path_patterns = (
            {"path-pattern": "foo", "reason": "Testing exclude path pattern"},
        )
        test_scanner = TestScanner(self.options)
        test_scanner.included_paths  # pylint: disable=pointless-statement
        mock_compile.assert_called_once_with({"foo"})

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
        self.options.exclude_path_patterns = (
            {"path-pattern": "foo", "reason": "Testing exclude path pattern"},
        )
        test_scanner = TestScanner(self.options)
        test_scanner.excluded_paths  # pylint: disable=pointless-statement
        mock_compile.assert_called_once_with({"foo"})

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
    def setUp(self) -> None:
        self.config_patcher = mock.patch("tartufo.config.configure_regexes")
        self.mock_configure = self.config_patcher.start()

        self.addCleanup(self.config_patcher.stop)
        return super().setUp()

    def test_populated_regex_list_does_not_recompute(self):
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = set()  # pylint: disable=protected-access
        test_scanner.rules_regexes  # pylint: disable=pointless-statement
        self.mock_configure.assert_not_called()

    def test_regex_rules_are_computed_when_first_accessed(self):
        self.options.default_regexes = True
        self.options.git_rules_repo = "bar"
        self.options.git_rules_files = "baz"  # type: ignore
        test_scanner = TestScanner(self.options)
        test_scanner._rule_patterns = "oof"  # pylint: disable=protected-access
        test_scanner.rules_regexes  # pylint: disable=pointless-statement
        self.mock_configure.assert_called_once_with(
            include_default=True,
            rule_patterns="oof",
            rules_repo="bar",
            rules_repo_files="baz",
        )

    def test_rule_patterns_with_rules_in_default_config(self):
        rule_patterns = [
            {
                "reason": "RSA private key 2",
                "pattern": "-----BEGIN default PRIVATE KEY-----",
            }
        ]
        self.options.rule_patterns = []
        test_scanner = TestScanner(self.options)
        test_scanner.config_data = {"rule_patterns": rule_patterns}
        self.assertEqual(test_scanner.rule_patterns, rule_patterns)

    def test_rule_patterns_with_rules_in_custom_config(self):
        rule_patterns = [
            {
                "reason": "RSA private key 2",
                "pattern": "-----BEGIN default PRIVATE KEY-----",
            }
        ]
        self.options.rule_patterns = rule_patterns
        test_scanner = TestScanner(self.options)
        test_scanner.config_data = {}
        self.assertEqual(test_scanner.rule_patterns, rule_patterns)

    def test_rule_patterns_with_rule_patterns_syntax_issue(self):
        rule_patterns = {
            "reason": "RSA private key 2",
            "pattern": "-----BEGIN default PRIVATE KEY-----",
        }
        self.options.rule_patterns = rule_patterns
        test_scanner = TestScanner(self.options)
        test_scanner.config_data = {}
        with self.assertRaisesRegex(
            types.ConfigException, "str pattern is illegal in rule-patterns"
        ):
            test_scanner.rule_patterns  # pylint: disable=pointless-statement


class SignatureTests(ScannerTestCase):
    @mock.patch("tartufo.util.generate_signature")
    def test_matched_signatures_are_excluded(self, mock_signature: mock.MagicMock):
        mock_signature.return_value = "foo"
        test_scanner = TestScanner(self.options)
        self.options.exclude_signatures = (
            {"signature": "foo", "reason": "Testing exclude signature"},
        )
        self.assertTrue(test_scanner.signature_is_excluded("bar", "blah"))

    @mock.patch("tartufo.util.generate_signature")
    def test_unmatched_signatures_are_not_excluded(
        self, mock_signature: mock.MagicMock
    ):
        mock_signature.return_value = "bar"
        test_scanner = TestScanner(self.options)
        self.options.exclude_signatures = (
            {"signature": "foo", "reason": "Testing exclude signature"},
        )
        self.assertFalse(test_scanner.signature_is_excluded("blah", "stuff"))

    def test_signature_found_as_scan_match_is_excluded(self):
        test_scanner = TestScanner(self.options)
        self.options.exclude_signatures = (
            {"signature": "ford_prefect", "reason": "Testing exclude signature"},
        )
        self.assertTrue(test_scanner.signature_is_excluded("ford_prefect", "/earth"))


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
        rule_2_path = mock.MagicMock()
        rule_2_path.match = mock.MagicMock(return_value=["/file/path"])
        rule_3 = mock.MagicMock()
        rule_3_path = mock.MagicMock()
        rule_3_path.match = mock.MagicMock(return_value=[])
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = {  # pylint: disable=protected-access
            Rule(
                name="foo",
                pattern=rule_1,
                path_pattern=None,
                re_match_type=MatchType.Match,
                re_match_scope=None,
            ),
            Rule(
                name="bar",
                pattern=rule_2,
                path_pattern=rule_2_path,
                re_match_type=MatchType.Match,
                re_match_scope=None,
            ),
            Rule(
                name="not-found",
                pattern=rule_3,
                path_pattern=rule_3_path,
                re_match_type=MatchType.Match,
                re_match_scope=None,
            ),
        }
        chunk = types.Chunk("foo", "/file/path", {}, False)
        list(test_scanner.scan_regex(chunk))
        rule_1.findall.assert_called_once_with("foo")
        rule_2.findall.assert_called_once_with("foo")
        rule_2_path.match.assert_called_once_with("/file/path")
        rule_3_path.match.assert_called_once_with("/file/path")
        rule_3.assert_not_called()

    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    def test_issue_is_not_created_if_signature_is_excluded(
        self, mock_signature: mock.MagicMock
    ):
        mock_signature.return_value = True
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = {  # pylint: disable=protected-access
            Rule(
                name="foo",
                pattern=re.compile("foo"),
                path_pattern=None,
                re_match_type=MatchType.Match,
                re_match_scope=None,
            )
        }
        chunk = types.Chunk("foo", "bar", {}, False)
        issues = list(test_scanner.scan_regex(chunk))
        mock_signature.assert_called_once_with("foo", "bar")
        self.assertEqual(issues, [])

    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    def test_issue_is_returned_if_signature_is_not_excluded(
        self, mock_signature: mock.MagicMock
    ):
        mock_signature.return_value = False
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = {  # pylint: disable=protected-access
            Rule(
                name="foo",
                pattern=re.compile("foo"),
                path_pattern=None,
                re_match_type=MatchType.Match,
                re_match_scope=None,
            )
        }
        chunk = types.Chunk("foo", "bar", {}, False)
        issues = list(test_scanner.scan_regex(chunk))
        mock_signature.assert_called_once_with("foo", "bar")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_detail, "foo")
        self.assertEqual(issues[0].issue_type, types.IssueType.RegEx)
        self.assertEqual(issues[0].matched_string, "foo")

    @mock.patch("tartufo.scanner.ScannerBase.regex_string_is_excluded")
    def test_issue_is_not_created_if_regex_string_is_excluded(
        self, mock_regex_string: mock.MagicMock
    ):
        mock_regex_string.return_value = True
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = {  # pylint: disable=protected-access
            Rule(
                name="foo",
                pattern=re.compile("foo"),
                path_pattern=None,
                re_match_type=MatchType.Match,
                re_match_scope=None,
            )
        }
        chunk = types.Chunk("foo", "bar", {}, False)
        issues = list(test_scanner.scan_regex(chunk))
        mock_regex_string.assert_called_once_with("foo", "bar")
        self.assertEqual(issues, [])

    @mock.patch("tartufo.scanner.ScannerBase.regex_string_is_excluded")
    def test_issue_is_returned_if_regex_string_is_not_excluded(
        self, mock_regex_string: mock.MagicMock
    ):
        mock_regex_string.return_value = False
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = {  # pylint: disable=protected-access
            Rule(
                name="foo",
                pattern=re.compile("foo"),
                path_pattern=None,
                re_match_type=MatchType.Match,
                re_match_scope=None,
            )
        }
        chunk = types.Chunk("foo", "bar", {}, False)
        issues = list(test_scanner.scan_regex(chunk))
        mock_regex_string.assert_called_once_with("foo", "bar")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_detail, "foo")
        self.assertEqual(issues[0].issue_type, types.IssueType.RegEx)
        self.assertEqual(issues[0].matched_string, "foo")

    def test_regex_string_is_excluded(self):
        self.options.exclude_regex_patterns = [
            {
                "path-pattern": r"docs/.*\.md",
                "pattern": "f.*",
            }
        ]
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = {  # pylint: disable=protected-access
            Rule(
                name="foo",
                pattern=re.compile("foo"),
                path_pattern=None,
                re_match_type=MatchType.Match,
                re_match_scope=None,
            )
        }
        excluded = test_scanner.regex_string_is_excluded("barfoo", "docs/README.md")
        self.assertTrue(excluded)

    def test_regex_string_is_excluded_given_partial_line_match(self):
        self.options.exclude_regex_patterns = [
            {"path-pattern": r"docs/.*\.md", "pattern": "line.+?foo"}
        ]
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = {  # pylint: disable=protected-access
            Rule(
                name="foo",
                pattern=re.compile("foo"),
                path_pattern=None,
                re_match_type=MatchType.Match,
                re_match_scope=None,
            )
        }
        excluded = test_scanner.regex_string_is_excluded(
            "+a line that contains foo", "docs/README.md"
        )
        self.assertTrue(excluded)

    def test_regex_string_is_not_excluded(self):
        self.options.exclude_regex_patterns = [
            {"path-pattern": r"foo\..*", "pattern": "f.*", "match-type": "match"}
        ]
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = {  # pylint: disable=protected-access
            Rule(
                name="foo",
                pattern=re.compile("foo"),
                path_pattern=None,
                re_match_type=MatchType.Match,
                re_match_scope=None,
            )
        }
        excluded = test_scanner.regex_string_is_excluded("bar", "foo.py")
        self.assertFalse(excluded)

    def test_regex_string_is_not_excluded_given_different_path(self):
        self.options.exclude_regex_patterns = [
            {"path-pattern": r"foo\..*", "pattern": "f.*", "match-type": "match"}
        ]
        test_scanner = TestScanner(self.options)
        test_scanner._rules_regexes = {  # pylint: disable=protected-access
            Rule(
                name="foo",
                pattern=re.compile("foo"),
                path_pattern=None,
                re_match_type=MatchType.Match,
                re_match_scope=None,
            )
        }
        excluded = test_scanner.regex_string_is_excluded("bar", "bar.py")
        self.assertFalse(excluded)


class EntropyManagementTests(ScannerTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.options.entropy = True
        self.chunk = types.Chunk(
            """
        foo bar
        asdfqwer
        """,
            "foo.py",
            {},
            False,
        )
        self.scanner = TestScanner(self.options)

    def test_entropy_string_is_excluded(self):
        self.options.exclude_entropy_patterns = [
            {
                "path-pattern": r"docs/.*\.md",
                "pattern": "f.*",
            }
        ]
        excluded = self.scanner.entropy_string_is_excluded(
            "foo", "barfoo", "docs/README.md"
        )
        self.assertEqual(True, excluded)

    def test_entropy_string_is_excluded_given_partial_line_match(self):
        self.options.exclude_entropy_patterns = [
            {"path-pattern": r"docs/.*\.md", "pattern": "line.+?foo"}
        ]
        excluded = self.scanner.entropy_string_is_excluded(
            "foo", "+a line that contains foo", "docs/README.md"
        )
        self.assertEqual(True, excluded)

    def test_entropy_string_is_not_excluded(self):
        self.options.exclude_entropy_patterns = [
            {"path-pattern": r"foo\..*", "pattern": "f.*", "match-type": "match"}
        ]
        excluded = self.scanner.entropy_string_is_excluded("foo", "bar", "foo.py")
        self.assertEqual(False, excluded)

    def test_entropy_string_is_not_excluded_given_different_path(self):
        self.options.exclude_entropy_patterns = [
            {"path-pattern": r"foo\..*", "pattern": "f.*", "match-type": "match"}
        ]
        excluded = self.scanner.entropy_string_is_excluded("foo", "bar", "bar.py")
        self.assertEqual(False, excluded)

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.util.find_strings_by_regex")
    def test_issues_are_not_created_for_b64_string_excluded_signatures(
        self,
        mock_strings: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = (["foo"], [], [], [], [], [])
        mock_signature.return_value = True
        issues = list(self.scanner.scan_entropy(self.chunk))
        mock_calculate.assert_not_called()
        self.assertEqual(issues, [])

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.util.find_strings_by_regex")
    def test_issues_are_not_created_for_hex_string_excluded_signatures(
        self,
        mock_strings: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = ([], ["foo"], [], [], [], [])
        mock_signature.return_value = True
        issues = list(self.scanner.scan_entropy(self.chunk))
        mock_calculate.assert_not_called()
        self.assertEqual(issues, [])

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.util.find_strings_by_regex")
    def test_issues_are_created_for_high_entropy_b64_strings(
        self,
        mock_strings: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = (["foo"], [], [], [], [], [])
        mock_signature.return_value = False
        mock_calculate.return_value = 9.0
        issues = list(self.scanner.scan_entropy(self.chunk))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, types.IssueType.Entropy)
        self.assertEqual(issues[0].matched_string, "foo")

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.util.find_strings_by_regex")
    def test_issues_are_created_for_high_entropy_hex_strings(
        self,
        mock_strings: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = ([], ["foo"], [], [], [], [])
        mock_signature.return_value = False
        mock_calculate.return_value = 9.0
        issues = list(self.scanner.scan_entropy(self.chunk))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, types.IssueType.Entropy)
        self.assertEqual(issues[0].matched_string, "foo")

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.scanner.ScannerBase.entropy_string_is_excluded")
    @mock.patch("tartufo.util.find_strings_by_regex")
    def test_issues_are_not_created_for_high_entropy_hex_strings_given_entropy_is_excluded(
        self,
        mock_strings: mock.MagicMock,
        mock_entropy: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = ([], ["foo"], [], [], [], [])
        mock_entropy.return_value = True
        mock_signature.return_value = False
        mock_calculate.return_value = 9.0
        issues = list(self.scanner.scan_entropy(self.chunk))
        self.assertEqual(len(issues), 0)

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.scanner.ScannerBase.entropy_string_is_excluded")
    @mock.patch("tartufo.util.find_strings_by_regex")
    def test_issues_are_not_created_for_low_entropy_b64_strings_given_entropy_is_excluded(
        self,
        mock_strings: mock.MagicMock,
        mock_entropy: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = (["foo"], [], [], [], [], [])
        mock_entropy.return_value = True
        mock_signature.return_value = False
        mock_calculate.return_value = 9.0
        issues = list(self.scanner.scan_entropy(self.chunk))
        self.assertEqual(len(issues), 0)

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.util.find_strings_by_regex")
    def test_issues_are_not_created_for_low_entropy_b64_strings(
        self,
        mock_strings: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = (["foo"], [], [], [], [], [])
        mock_signature.return_value = False
        mock_calculate.return_value = 1.0
        issues = list(self.scanner.scan_entropy(self.chunk))
        self.assertEqual(len(issues), 0)

    @mock.patch("tartufo.scanner.ScannerBase.calculate_entropy")
    @mock.patch("tartufo.scanner.ScannerBase.signature_is_excluded")
    @mock.patch("tartufo.util.find_strings_by_regex")
    def test_issues_are_not_created_for_low_entropy_hex_strings(
        self,
        mock_strings: mock.MagicMock,
        mock_signature: mock.MagicMock,
        mock_calculate: mock.MagicMock,
    ):
        mock_strings.side_effect = ([], ["foo"], [], [], [], [])
        mock_signature.return_value = False
        mock_calculate.return_value = 1.0
        issues = list(self.scanner.scan_entropy(self.chunk))
        self.assertEqual(len(issues), 0)


class EntropyDetectionTests(ScannerTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.options.entropy = True
        self.chunk = types.Chunk(
            """
        foo bar
        asdfqwer
        """,
            "foo.py",
            {},
            False,
        )
        self.scanner = TestScanner(self.options)

    def test_calculate_base64_entropy_calculation(self):
        random_string = (
            "ZWVTjPQSdhwRgl204Hc51YCsritMIzn8B=/p9UyeX7xu6KkAGqfm3FJ+oObLDNEva"
        )
        self.assertGreaterEqual(
            self.scanner.calculate_entropy(random_string),
            4.5,
        )

    def test_calculate_hex_entropy_calculation(self):
        random_string = "b3A0a1FDfe86dcCE945B72"
        self.assertGreaterEqual(self.scanner.calculate_entropy(random_string), 3)

    def test_empty_string_has_no_entropy(self):
        self.assertEqual(self.scanner.calculate_entropy(""), 0.0)

    @mock.patch("tartufo.util.find_strings_by_regex")
    def test_scan_entropy_find_b64_strings_for_every_word_in_diff(
        self, mock_strings: mock.MagicMock
    ):
        mock_strings.return_value = []
        list(self.scanner.scan_entropy(self.chunk))
        mock_strings.assert_has_calls(
            (
                mock.call("foo", scanner.BASE64_REGEX),
                mock.call("foo", scanner.HEX_REGEX),
                mock.call("bar", scanner.BASE64_REGEX),
                mock.call("bar", scanner.HEX_REGEX),
                mock.call("asdfqwer", scanner.BASE64_REGEX),
                mock.call("asdfqwer", scanner.HEX_REGEX),
            )
        )

    def test_sensitivity_low_end_calculation(self):
        self.options.entropy_sensitivity = 0
        test_scanner = TestScanner(self.options)

        # 0% sensitivity means entropy rate must equal bit rate
        self.assertEqual(test_scanner.b64_entropy_limit, 0.0)
        self.assertEqual(test_scanner.hex_entropy_limit, 0.0)

    def test_sensitivity_high_end_calculation(self):
        self.options.entropy_sensitivity = 100
        test_scanner = TestScanner(self.options)

        # 100% sensitivity means required entropy rate will be zero
        self.assertEqual(test_scanner.b64_entropy_limit, 6.0)
        self.assertEqual(test_scanner.hex_entropy_limit, 4.0)

    def test_calculate_entropy_minimum_calculation(self):
        # We already know an empty string trivially has zero entropy.
        # Doing the math, a one-character string also should have zero entropy.
        self.assertEqual(self.scanner.calculate_entropy("a"), 0.0)

    def test_calculate_entropy_maximum_hexadecimal(self):
        # We reach maximum entropy when every character in the alphabet appears
        # once in the input string (order doesn't matter). Each character represents
        # 4 bits (has 2^4 = 16 possible values).
        #
        # Try to avoid causing a finding ourselves. :)
        #
        # Note there is no requirement that the test alphabet actually is the
        # same as the hexadecimal representation, as long as the size is identical.
        # However, it is convenient to use the real thing to avoid errors. Note
        # that representation is case-insensitive so we do not include uppercase
        # letters in this alphabet.
        alphabet = string.hexdigits[:16]
        self.assertEqual(self.scanner.calculate_entropy(alphabet), 4.0)

    def test_calculate_entropy_maximum_base64(self):
        # See above. base64 uses 4 characters to represent 3 bytes, so the
        # underlying bit rate is 24 / 4 = 6 bits per character. Unlike above,
        # case matters, so we include both upper- and lowercase letters.
        alphabet = string.ascii_letters + string.digits + "+/"
        self.assertEqual(self.scanner.calculate_entropy(alphabet), 6.0)


if __name__ == "__main__":
    unittest.main()
