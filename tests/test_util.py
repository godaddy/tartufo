from io import StringIO
import importlib
import json
import re
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import call
import pytest

import git

from tartufo import scanner, types, util
from tartufo.types import GlobalOptions, Rule, MatchType, Scope

from tests.helpers import generate_options

try:
    from importlib import metadata  # type: ignore

    importlib_metadata = None  # pylint: disable=invalid-name
except ImportError:
    # Python < 3.8
    import importlib_metadata  # type: ignore

    metadata = None  # type: ignore # pylint: disable=invalid-name


class GitTests(unittest.TestCase):
    """Test that we interact with git properly.

    We will not test that we get the eventual result desired (e.g. a fully
    cloned repo) for a couple of reasons.

      1. That functionality is not the responsibility of our package;
         it is the responsibility of the `git` package.
      2. Full tests such as those would require an internet connection,
         and rely on the functionality of external systems. Unit tests
         should only ever rely on the code which is being directly tested.
    """

    @mock.patch("git.Repo.clone_from")
    @mock.patch("tartufo.util.tempfile.mkdtemp")
    def test_tartufo_clones_git_repo_into_temp_dir(
        self, mock_mkdtemp: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_mkdtemp.return_value = "/foo"
        util.clone_git_repo("https://github.com/godaddy/tartufo.git")
        mock_clone.assert_called_once_with(
            "https://github.com/godaddy/tartufo.git", "/foo"
        )

    @mock.patch("git.Repo.clone_from")
    @mock.patch("tartufo.util.tempfile.mkdtemp")
    def test_clone_git_repo_returns_path_to_clone(
        self, mock_mkdtemp: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        mock_remote = mock.MagicMock()
        mock_remote.name = "origin"
        mock_repo = mock.MagicMock()
        mock_repo.remotes = [mock_remote]
        mock_clone.return_value = mock_repo
        mock_mkdtemp.return_value = "/foo"
        repo_path, repo_origin = util.clone_git_repo(
            "https://github.com/godaddy/tartufo.git"
        )
        self.assertEqual(repo_path, Path("/foo"))
        self.assertEqual(repo_origin, "origin")

    @mock.patch("git.Repo.clone_from")
    @mock.patch("tartufo.util.tempfile.mkdtemp")
    def test_clone_git_repo_clones_into_target_dir(
        self, mock_temp: mock.MagicMock, mock_clone: mock.MagicMock
    ):
        util.clone_git_repo(
            "https://github.com/godaddy/tartufo.git", Path("/foo/tartufo.git")
        )
        mock_temp.assert_not_called()
        mock_clone.assert_called_once_with(
            "https://github.com/godaddy/tartufo.git",
            str(Path("/foo/tartufo.git")),
        )

    @mock.patch("git.Repo.clone_from")
    @mock.patch("tartufo.util.tempfile.mkdtemp", new=mock.MagicMock())
    def test_clone_git_repo_raises_explicit_exception_on_clone_fail(
        self, mock_clone: mock.MagicMock
    ):
        mock_clone.side_effect = git.GitCommandError(
            command="git clone foo.git", status=42, stderr="Error cloning repo!"
        )
        with self.assertRaisesRegex(
            types.GitRemoteException, "stderr: 'Error cloning repo!'"
        ):
            util.clone_git_repo("https://github.com/godaddy/tartufo.git")

    @mock.patch("pygit2.Repository")
    def test_path_contains_git_should_return_false_given_giterror(
        self, mock_git_repo: mock.MagicMock
    ):
        mock_git_repo.side_effect = git.GitError()
        actual = util.path_contains_git("./test")
        self.assertFalse(actual)

    @mock.patch("git.Repo")
    def test_path_contains_git_should_return_false_given_null_repo(
        self, mock_git_repo: mock.MagicMock
    ):
        mock_git_repo.return_value = None
        actual = util.path_contains_git("./test")
        self.assertFalse(actual)

    @mock.patch("git.Repo")
    def test_path_contains_git_should_return_true_given_repo_object(
        self, mock_git_repo: mock.MagicMock
    ):
        mock_git_repo.return_value = mock.Mock()
        actual = util.path_contains_git("./test")
        self.assertTrue(actual)


class OutputTests(unittest.TestCase):
    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    def test_echo_result_echos_all_when_not_json(self, mock_click, mock_scanner):
        options = generate_options(GlobalOptions, verbose=0)
        mock_scanner.exclude_signatures = []
        mock_scanner.scan.return_value = (1, 2, 3, 4)
        util.echo_result(options, mock_scanner, "", "")

        mock_click.echo.assert_has_calls(
            [
                mock.call(str(1)),
                mock.call(str(2)),
                mock.call(str(3)),
                mock.call(str(4)),
            ]
        )
        self.assertEqual(mock_click.echo.call_count, 4)

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    def test_echo_result_outputs_compact_format(self, mock_click, mock_scanner):
        options = generate_options(GlobalOptions, verbose=0, output_format="compact")
        issue1 = scanner.Issue(
            types.IssueType.Entropy,
            "foo",
            types.Chunk("fullfoobar", "/what/foo", {}, False),
        )
        issue2 = scanner.Issue(
            types.IssueType.RegEx,
            "bar",
            types.Chunk("fullfoobar", "/what/bar", {}, False),
        )
        issue2.issue_detail = "Meets the bar"
        mock_scanner.scan.return_value = (issue1, issue2)
        util.echo_result(options, mock_scanner, "", "")

        mock_click.echo.assert_has_calls(
            [
                mock.call(
                    "[High Entropy] /what/foo: foo (ea29b8c0f8a478f260689899393107cca188fbbff1c5a5bd4ff32c102cb60226, None)"
                ),
                mock.call(
                    "[Regular Expression Match] /what/bar: bar (fa692eebc3d60e67a9f22b4b877d5939cb2ec96c0c26c7e5168b3b8b660c573c, Meets the bar)"
                ),
            ],
        )

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    @mock.patch("tartufo.util.datetime")
    def test_echo_result_echos_message_when_clean(
        self, mock_time, mock_click, mock_scanner
    ):
        mock_time.now.return_value.isoformat.return_value = "now:now:now"
        options = generate_options(GlobalOptions, quiet=False, verbose=0)
        mock_scanner.exclude_signatures = []
        mock_scanner.issue_count = 0
        mock_scanner.issues = []
        util.echo_result(options, mock_scanner, "", "")
        mock_click.echo.assert_called_once_with(
            "Time: now:now:now\nAll clear. No secrets detected."
        )

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    @mock.patch("tartufo.util.datetime")
    def test_echo_result_echos_exclusions_verbose(
        self, mock_time, mock_click, mock_scanner
    ):
        mock_time.now.return_value.isoformat.return_value = "now:now:now"

        options = generate_options(
            GlobalOptions,
            quiet=False,
            verbose=1,
        )
        mock_scanner.issues = []
        mock_scanner.issue_count = 0
        mock_scanner.excluded_paths = [
            re.compile("package-lock.json"),
            re.compile("poetry.lock"),
        ]
        mock_scanner.excluded_signatures = [
            "fffffffffffff",
            "ooooooooooooo",
        ]

        rule_1 = (
            Rule(
                name="Rule-1",
                pattern="aaaa",
                path_pattern="bbbb",
                re_match_type=MatchType.Search,
                re_match_scope=Scope.Line,
            ),
        )
        rule_2 = (
            Rule(
                name="Rule-1",
                pattern="cccc",
                path_pattern="dddd",
                re_match_type=MatchType.Search,
                re_match_scope=Scope.Line,
            ),
        )
        mock_scanner.excluded_entropy = [rule_1, rule_2]
        util.echo_result(options, mock_scanner, "", "")
        mock_click.echo.assert_has_calls(
            (
                mock.call("Time: now:now:now\nAll clear. No secrets detected."),
                mock.call("\nExcluded paths:"),
                mock.call("re.compile('package-lock.json')\nre.compile('poetry.lock')"),
                mock.call("\nExcluded signatures:"),
                mock.call("fffffffffffff\nooooooooooooo"),
                mock.call("\nExcluded entropy patterns:"),
                mock.call(f"{rule_1}\n{rule_2}"),
            ),
            any_order=False,
        )

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    def test_echo_result_echos_no_message_when_quiet(self, mock_click, mock_scanner):
        options = generate_options(GlobalOptions, quiet=True, verbose=0)
        mock_scanner.issues = []
        mock_scanner.exclude_signatures = []
        util.echo_result(options, mock_scanner, "", "")
        mock_click.echo.assert_not_called()

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.datetime")
    def test_echo_result_outputs_proper_json_when_requested(
        self,
        mock_time,
        mock_scanner,
    ):
        mock_time.now.return_value.isoformat.return_value = "now:now:now"
        issue_1 = scanner.Issue(
            types.IssueType.Entropy, "foo", types.Chunk("foo", "/bar", {}, False)
        )
        issue_2 = scanner.Issue(
            types.IssueType.RegEx, "bar", types.Chunk("foo", "/bar", {}, False)
        )
        mock_scanner.scan.return_value = (issue_1, issue_2)
        mock_scanner.excluded_paths = []
        options = generate_options(
            GlobalOptions,
            output_format=types.OutputFormat.Json.value,
            exclude_signatures=[],
            exclude_entropy_patterns=[],
            exclude_regex_patterns=[],
        )

        # We're generating JSON piecemeal, so if we want to be safe we'll recover
        # the entire output, deserialize it (to confirm it's valid syntax) and
        # compare the result to the original input dictionary.
        with mock.patch("sys.stdout", new=StringIO()) as mock_stdout:
            util.echo_result(options, mock_scanner, "/repo", "/output")
            actual_output = mock_stdout.getvalue()

        self.assertEqual(
            json.loads(actual_output),
            {
                "scan_time": "now:now:now",
                "project_path": "/repo",
                "output_dir": "/output",
                "excluded_paths": [],
                "excluded_signatures": [],
                "exclude_entropy_patterns": [],
                "exclude_regex_patterns": [],
                "found_issues": [
                    {
                        "issue_type": "High Entropy",
                        "issue_detail": None,
                        "diff": "foo",
                        "matched_string": "foo",
                        "signature": "4db0024275a64ac2bf5e7d061e130e283b0b37a44167b605643e06e33177f74e",
                        "file_path": "/bar",
                    },
                    {
                        "issue_type": "Regular Expression Match",
                        "issue_detail": None,
                        "diff": "foo",
                        "matched_string": "bar",
                        "signature": "1516f2c3395943be40811573bb63ed1e2b8fe3a0e6dcc8dbb43351ca90ba6822",
                        "file_path": "/bar",
                    },
                ],
            },
        )

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.datetime")
    def test_echo_result_outputs_proper_json_when_requested_pathtype(
        self, mock_time, mock_scanner
    ):
        mock_time.now.return_value.isoformat.return_value = "now:now:now"
        issue_1 = scanner.Issue(
            types.IssueType.Entropy, "foo", types.Chunk("foo", "/bar", {}, False)
        )
        issue_2 = scanner.Issue(
            types.IssueType.RegEx, "bar", types.Chunk("foo", "/bar", {}, False)
        )
        mock_scanner.scan.return_value = (issue_1, issue_2)
        mock_scanner.excluded_paths = [
            re.compile("package-lock.json"),
            re.compile("poetry.lock"),
        ]
        mock_scanner.excluded_signatures = [
            "fffffffffffff",
            "ooooooooooooo",
        ]
        exclude_entropy_patterns = [
            "aaaaa::bbbbb",
            "ccccc::ddddd",
        ]
        exclude_regex_patterns = [
            "eeeee::fffff",
            "ggggg::hhhhh",
        ]
        options = generate_options(
            GlobalOptions,
            output_format=types.OutputFormat.Json.value,
            exclude_entropy_patterns=exclude_entropy_patterns,
            exclude_regex_patterns=exclude_regex_patterns,
        )

        # We're generating JSON piecemeal, so if we want to be safe we'll recover
        # the entire output, deserialize it (to confirm it's valid syntax) and
        # compare the result to the original input dictionary.
        with mock.patch("sys.stdout", new=StringIO()) as mock_stdout:
            util.echo_result(options, mock_scanner, "/repo", Path("/tmp"))
            actual_output = mock_stdout.getvalue()
        self.assertEqual(
            json.loads(actual_output),
            {
                "scan_time": "now:now:now",
                "project_path": "/repo",
                "output_dir": str(Path("/tmp")),
                "excluded_paths": ["package-lock.json", "poetry.lock"],
                "excluded_signatures": [
                    "fffffffffffff",
                    "ooooooooooooo",
                ],
                "exclude_entropy_patterns": [
                    "aaaaa::bbbbb",
                    "ccccc::ddddd",
                ],
                "exclude_regex_patterns": [
                    "eeeee::fffff",
                    "ggggg::hhhhh",
                ],
                "found_issues": [
                    {
                        "issue_type": "High Entropy",
                        "issue_detail": None,
                        "diff": "foo",
                        "matched_string": "foo",
                        "signature": "4db0024275a64ac2bf5e7d061e130e283b0b37a44167b605643e06e33177f74e",
                        "file_path": "/bar",
                    },
                    {
                        "issue_type": "Regular Expression Match",
                        "issue_detail": None,
                        "diff": "foo",
                        "matched_string": "bar",
                        "signature": "1516f2c3395943be40811573bb63ed1e2b8fe3a0e6dcc8dbb43351ca90ba6822",
                        "file_path": "/bar",
                    },
                ],
            },
        )

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    @mock.patch("tartufo.util.datetime")
    @mock.patch("tartufo.util.get_version")
    def test_echo_report_result_echos_report_output(
        self, mock_getversion, mock_time, mock_click, mock_scanner
    ):
        mock_getversion.return_value = "3.2.2"
        mock_time.now.return_value.isoformat.return_value = "now:now:now"

        options = generate_options(
            GlobalOptions,
            quiet=False,
            output_format="report",
            entropy=True,
            regex=True,
            entropy_sensitivity=75,
            exclude_signatures=[
                "fffffffffffff",
                "ooooooooooooo",
            ],
            exclude_path_patterns=["file1.txt", "file2.txt"],
        )
        mock_scanner.global_options = options
        mock_scanner.issues = []
        mock_scanner.issue_count = 0

        util.echo_result(options, mock_scanner, "", "")
        mock_click.echo.assert_has_calls(
            (
                call("Tartufo Scan Results (Time: now:now:now)"),
                call("All clear. No secrets detected."),
                call("\nConfiguration:"),
                call("  version:             3.2.2"),
                call("  entropy:             Enabled"),
                call("    sensitivity: 75"),
                call("  regex:               Enabled"),
                call("\nExcluded paths:"),
                call("  file1.txt: Unknown reason"),
                call("  file2.txt: Unknown reason"),
                call("\nExcluded signatures:"),
                call("  fffffffffffff: Unknown reason"),
                call("  ooooooooooooo: Unknown reason"),
                call("\nExcluded entropy patterns:"),
            ),
            any_order=False,
        )

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    @mock.patch("tartufo.util.datetime")
    @mock.patch("tartufo.util.get_version")
    def test_echo_report_result_given_dict_options_echos_report_output_with_reasons(
        self, mock_getversion, mock_time, mock_click, mock_scanner
    ):
        mock_getversion.return_value = "3.2.2"
        mock_time.now.return_value.isoformat.return_value = "now:now:now"

        options = generate_options(
            GlobalOptions,
            quiet=False,
            output_format="report",
            entropy=True,
            regex=True,
            entropy_sensitivity=75,
            exclude_signatures=[
                {"signature": "fffffffffffff", "reason": "reason 1"},
                {"signature": "ooooooooooooo", "reason": "reason 2"},
            ],
            exclude_path_patterns=[
                {"path-pattern": "file1.txt", "reason": "reason 1"},
                {"path-pattern": "file2.txt", "reason": "reason 2"},
            ],
        )
        mock_scanner.global_options = options
        mock_scanner.issues = []
        mock_scanner.issue_count = 0
        mock_scanner.excluded_entropy = [
            Rule(
                "reason 1",
                re.compile("pattern1"),
                re.compile("file1.txt"),
                MatchType.Search,
                Scope.Line,
            ),
            Rule(
                "reason 2",
                re.compile("pattern2"),
                re.compile("file2.txt"),
                MatchType.Search,
                Scope.Line,
            ),
        ]

        util.echo_result(options, mock_scanner, "", "")
        mock_click.echo.assert_has_calls(
            (
                call("Tartufo Scan Results (Time: now:now:now)"),
                call("All clear. No secrets detected."),
                call("\nConfiguration:"),
                call("  version:             3.2.2"),
                call("  entropy:             Enabled"),
                call("    sensitivity: 75"),
                call("  regex:               Enabled"),
                call("\nExcluded paths:"),
                call("  file1.txt: reason 1"),
                call("  file2.txt: reason 2"),
                call("\nExcluded signatures:"),
                call("  fffffffffffff: reason 1"),
                call("  ooooooooooooo: reason 2"),
                call("\nExcluded entropy patterns:"),
                call("  pattern1 (path=file1.txt, scope=line, type=search): reason 1"),
                call("  pattern2 (path=file2.txt, scope=line, type=search): reason 2"),
            ),
            any_order=False,
        )

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    @mock.patch("tartufo.util.datetime")
    @mock.patch("tartufo.util.get_version")
    def test_echo_report_result_given_no_excludes_outputs_empty_report(
        self, mock_getversion, mock_time, mock_click, mock_scanner
    ):
        mock_getversion.return_value = "3.2.2"
        mock_time.now.return_value.isoformat.return_value = "now:now:now"

        options = generate_options(
            GlobalOptions,
            quiet=False,
            output_format="report",
            entropy=True,
            regex=True,
            entropy_sensitivity=75,
            exclude_signatures=[],
            exclude_path_patterns=[],
            exclude_entropy_patterns=[],
            exclude_regex_patterns=[],
        )
        mock_scanner.global_options = options
        mock_scanner.issues = []
        mock_scanner.issue_count = 0

        util.echo_result(options, mock_scanner, "", "")
        mock_click.echo.assert_has_calls(
            (
                call("Tartufo Scan Results (Time: now:now:now)"),
                call("All clear. No secrets detected."),
                call("\nConfiguration:"),
                call("  version:             3.2.2"),
                call("  entropy:             Enabled"),
                call("    sensitivity: 75"),
                call("  regex:               Enabled"),
                call("\nExcluded paths:"),
                call("\nExcluded signatures:"),
                call("\nExcluded entropy patterns:"),
            ),
            any_order=False,
        )

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    @mock.patch("tartufo.util.datetime")
    @mock.patch("tartufo.util.get_version")
    def test_echo_report_result_given_disabled_report_shows_disabled(
        self, mock_getversion, mock_time, mock_click, mock_scanner
    ):
        mock_getversion.return_value = "3.2.2"
        mock_time.now.return_value.isoformat.return_value = "now:now:now"

        options = generate_options(
            GlobalOptions,
            quiet=False,
            output_format="report",
            entropy=False,
            regex=False,
            entropy_sensitivity=75,
            exclude_signatures=[],
            exclude_path_patterns=[],
            exclude_entropy_patterns=[],
            exclude_regex_patterns=[],
        )
        mock_scanner.global_options = options
        mock_scanner.issues = []
        mock_scanner.issue_count = 0

        util.echo_result(options, mock_scanner, "", "")
        mock_click.echo.assert_has_calls(
            (
                call("Tartufo Scan Results (Time: now:now:now)"),
                call("All clear. No secrets detected."),
                call("\nConfiguration:"),
                call("  version:             3.2.2"),
                call("  entropy:             Disabled"),
                call("  regex:               Disabled"),
                call("\nExcluded paths:"),
                call("\nExcluded signatures:"),
                call("\nExcluded entropy patterns:"),
            ),
            any_order=False,
        )

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    @mock.patch("tartufo.util.datetime")
    @mock.patch("tartufo.util.get_version")
    def test_echo_report_result_issues_report_shows_issues(
        self, mock_getversion, mock_time, mock_click, mock_scanner
    ):
        mock_getversion.return_value = "3.2.2"
        mock_time.now.return_value.isoformat.return_value = "now:now:now"

        options = generate_options(
            GlobalOptions,
            quiet=False,
            output_format="report",
            entropy=False,
            regex=False,
            entropy_sensitivity=75,
            exclude_signatures=[],
            exclude_path_patterns=[],
            exclude_entropy_patterns=[],
            exclude_regex_patterns=[],
        )
        mock_scanner.global_options = options
        issue_1 = scanner.Issue(
            types.IssueType.Entropy, "foo", types.Chunk("foo", "/bar", {}, False)
        )
        mock_scanner.scan.return_value = [issue_1]
        mock_scanner.issues = [issue_1]
        mock_scanner.issue_count = 1

        util.echo_result(options, mock_scanner, "", "")
        mock_click.echo.assert_has_calls(
            (
                call("Tartufo Scan Results (Time: now:now:now)"),
                call(
                    "~~~~~~~~~~~~~~~~~~~~~\nReason: High Entropy\nFilepath: /bar\nSignature: 4db0024275a64ac2bf5e7d061e130e283b0b37a44167b605643e06e33177f74e\nfoo\n~~~~~~~~~~~~~~~~~~~~~"
                ),
                call("\nConfiguration:"),
                call("  version:             3.2.2"),
                call("  entropy:             Disabled"),
                call("  regex:               Disabled"),
                call("\nExcluded paths:"),
                call("\nExcluded signatures:"),
                call("\nExcluded entropy patterns:"),
            ),
            any_order=False,
        )

    @pytest.mark.skipif(
        importlib_metadata is None,
        reason="importlib_metadata not available",  # pylint: disable=used-before-assignment
    )
    def test_get_version_importlib_metadata(self):
        with mock.patch("importlib_metadata.version") as mock_version:
            mock_version.return_value = "1.0.0"

            actual = util.get_version()
            self.assertEqual(actual, "1.0.0")

    @pytest.mark.skipif(metadata is None, reason="importlib.metadata not available")
    def test_get_version_importlib(self):
        with mock.patch("importlib.metadata.version") as mock_version:
            mock_version.return_value = "1.0.0"

            actual = util.get_version()
            self.assertEqual(actual, "1.0.0")


class GeneralUtilTests(unittest.TestCase):
    @mock.patch("tartufo.util.click", new=mock.MagicMock())
    def test_fail_exits_with_exit_code(self):
        mock_context = mock.MagicMock()
        util.fail("Foo!", mock_context, 42)
        mock_context.exit.assert_called_once_with(42)  # pylint: disable=unreachable

    @mock.patch("tartufo.util.style_error")
    @mock.patch("tartufo.util.click")
    def test_fail_echos_styled_error_message(self, mock_click, mock_style):
        util.fail("Foo!", mock.MagicMock(), 42)
        mock_style.assert_called_once_with("Foo!")  # pylint: disable=unreachable
        mock_click.echo.assert_called_once_with(mock_style.return_value, err=True)

    @mock.patch("tartufo.util.sys.stdout")
    def test_style_when_color_is_disabled(self, mock_stdout):
        mock_stdout.isatty.return_value = True
        importlib.reload(util)  # Forces sys.stdout.isatty to False

        options = generate_options(GlobalOptions, verbose=0, color=False)
        util.init_styles(options)

        ok_result = util.style_ok("OK")
        error_result = util.style_error("ERROR")
        warning_result = util.style_warning("WARNING")

        self.assertEqual(ok_result, "OK")
        self.assertEqual(error_result, "ERROR")
        self.assertEqual(warning_result, "WARNING")

    @mock.patch("tartufo.util.sys.stdout")
    def test_style_when_color_is_enabled(self, mock_stdout):
        mock_stdout.isatty.return_value = False
        importlib.reload(util)  # Forces sys.stdout.isatty to False

        options = generate_options(GlobalOptions, verbose=0, color=True)
        util.init_styles(options)

        ok_result = util.style_ok("OK")
        error_result = util.style_error("ERROR")
        warning_result = util.style_warning("WARNING")

        self.assertEqual(ok_result, "\x1b[92mOK\x1b[0m")
        self.assertEqual(error_result, "\x1b[31m\x1b[1mERROR\x1b[0m")
        self.assertEqual(warning_result, "\x1b[93mWARNING\x1b[0m")

    @mock.patch("tartufo.util.sys.stdout")
    def test_style_when_not_a_tty(self, mock_stdout):
        mock_stdout.isatty.return_value = False
        importlib.reload(util)  # Forces sys.stdout.isatty to False

        options = generate_options(GlobalOptions, verbose=0)
        util.init_styles(options)

        ok_result = util.style_ok("OK")
        error_result = util.style_error("ERROR")
        warning_result = util.style_warning("WARNING")

        mock_stdout.isatty.assert_called_once()
        self.assertEqual(ok_result, "OK")
        self.assertEqual(error_result, "ERROR")
        self.assertEqual(warning_result, "WARNING")

    @mock.patch("tartufo.util.sys.stdout")
    def test_style_when_is_a_tty(self, mock_stdout):
        mock_stdout.isatty.return_value = True
        importlib.reload(util)  # Forces sys.stdout.isatty to True

        options = generate_options(GlobalOptions, verbose=0)
        util.init_styles(options)

        ok_result = util.style_ok("OK")
        error_result = util.style_error("ERROR")
        warning_result = util.style_warning("WARNING")

        mock_stdout.isatty.assert_called_once()
        self.assertEqual(ok_result, "\x1b[92mOK\x1b[0m")
        self.assertEqual(error_result, "\x1b[31m\x1b[1mERROR\x1b[0m")
        self.assertEqual(warning_result, "\x1b[93mWARNING\x1b[0m")

    @mock.patch("tartufo.util.blake2s")
    def test_signature_is_generated_with_snippet_and_filename(self, mock_hash):
        util.generate_signature.cache_clear()
        util.generate_signature("foo", "bar")
        mock_hash.assert_called_once_with(b"foo$$bar")

    def test_find_strings_by_regex_splits_string_by_chars_outside_charset(self):
        strings = list(
            util.find_strings_by_regex("asdf.qwer", re.compile(r"[asdfqwer]+"), 1)
        )
        self.assertEqual(strings, ["asdf", "qwer"])

    def test_find_strings_by_regex_will_not_return_strings_below_threshold_length(self):
        strings = list(
            util.find_strings_by_regex("w.asdf.q", re.compile(r"[asdfqwer]+"), 3)
        )
        self.assertEqual(strings, ["asdf"])

    def test_find_strings_by_regex_recognizes_hexadecimal(self):
        sample_input = """
        1111111111fffffCCCCC This is valid hexadecimal
        g111111111fffffCCCCC This is not because "g" is not in alphabet
        """

        strings = list(util.find_strings_by_regex(sample_input, scanner.HEX_REGEX, 20))
        self.assertEqual(strings, ["1111111111fffffCCCCC"])

    def test_find_strings_by_regex_recognizes_base64(self):
        sample_input = """
        111111111+ffffCCCC== This is valid base64
        @111111111+ffffCCCC= This is not because "@" is not in alphabet
        """

        strings = list(
            util.find_strings_by_regex(sample_input, scanner.BASE64_REGEX, 20)
        )
        self.assertEqual(strings, ["111111111+ffffCCCC=="])

    def test_find_strings_by_regex_recognizes_base64url(self):
        sample_input = """
        111111111-ffffCCCC== This is valid base64url
        @111111111-ffffCCCC= This is not because "@" is not in alphabet
        """

        strings = list(
            util.find_strings_by_regex(sample_input, scanner.BASE64_REGEX, 20)
        )
        self.assertEqual(strings, ["111111111-ffffCCCC=="])

    def test_find_strings_by_regex_recognizes_mutant_base64(self):
        sample_input = """
        +111111111-ffffCCCC= Can't mix + and - but both are in regex
        111111111111111111111== Not a valid length but we don't care
        ==111111111111111111 = Is supposed to be end only but we don't care
        """

        strings = list(
            util.find_strings_by_regex(sample_input, scanner.BASE64_REGEX, 20)
        )
        self.assertEqual(
            strings,
            ["+111111111-ffffCCCC=", "111111111111111111111==", "==111111111111111111"],
        )
