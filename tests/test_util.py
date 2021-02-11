import unittest
import re
from pathlib import Path
from unittest import mock

import git

from tartufo import scanner, types, util
from tartufo.types import GlobalOptions

from tests.helpers import generate_options


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

    @mock.patch("git.Repo.clone_from", new=mock.MagicMock())
    @mock.patch("tartufo.util.tempfile.mkdtemp")
    def test_clone_git_repo_returns_path_to_clone(self, mock_mkdtemp: mock.MagicMock):
        mock_mkdtemp.return_value = "/foo"
        repo_path = util.clone_git_repo("https://github.com/godaddy/tartufo.git")
        self.assertEqual(repo_path, Path("/foo"))

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


class OutputTests(unittest.TestCase):
    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    def test_echo_result_echos_all_when_not_json(self, mock_click, mock_scanner):
        options = generate_options(GlobalOptions, json=False, verbose=0)
        mock_scanner.exclude_signatures = []
        mock_scanner.issues = [1, 2, 3, 4]
        util.echo_result(options, mock_scanner, "", "")
        mock_click.echo.assert_called_once_with("1\n2\n3\n4")

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    @mock.patch("tartufo.util.datetime")
    def test_echo_result_echos_message_when_clean(
        self, mock_time, mock_click, mock_scanner
    ):
        mock_time.now.return_value.isoformat.return_value = "now:now:now"
        options = generate_options(GlobalOptions, json=False, quiet=False, verbose=0)
        mock_scanner.exclude_signatures = []
        mock_scanner.issues = []
        util.echo_result(options, mock_scanner, "", "")
        mock_click.echo.assert_called_with(
            "Time: now:now:now\nAll clear. No secrets detected."
        )

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    @mock.patch("tartufo.util.datetime")
    def test_echo_result_echos_exclusions_verbose(
        self, mock_time, mock_click, mock_scanner
    ):
        mock_time.now.return_value.isoformat.return_value = "now:now:now"
        exclude_signatures = [
            "fffffffffffff",
            "ooooooooooooo",
        ]
        options = generate_options(
            GlobalOptions,
            json=False,
            quiet=False,
            verbose=1,
            exclude_signatures=exclude_signatures,
        )
        mock_scanner.issues = []
        mock_scanner.excluded_paths = [
            re.compile("package-lock.json"),
            re.compile("poetry.lock"),
        ]
        util.echo_result(options, mock_scanner, "", "")
        mock_click.echo.assert_has_calls(
            (
                mock.call("Time: now:now:now\nAll clear. No secrets detected."),
                mock.call("\nExcluded paths:"),
                mock.call("package-lock.json\npoetry.lock"),
                mock.call("\nExcluded signatures:"),
                mock.call("fffffffffffff\nooooooooooooo"),
            ),
            any_order=False,
        )

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click")
    def test_echo_result_echos_no_message_when_quiet(self, mock_click, mock_scanner):
        options = generate_options(GlobalOptions, json=False, quiet=True, verbose=0)
        mock_scanner.issues = []
        mock_scanner.exclude_signatures = []
        util.echo_result(options, mock_scanner, "", "")
        mock_click.echo.assert_not_called()

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click", new=mock.MagicMock())
    @mock.patch("tartufo.util.json")
    @mock.patch("tartufo.util.datetime")
    def test_echo_result_outputs_proper_json_when_requested(
        self,
        mock_time,
        mock_json,
        mock_scanner,
    ):
        mock_time.now.return_value.isoformat.return_value = "now:now:now"
        issue_1 = scanner.Issue(
            types.IssueType.Entropy, "foo", types.Chunk("foo", "/bar", {})
        )
        issue_2 = scanner.Issue(
            types.IssueType.RegEx, "bar", types.Chunk("foo", "/bar", {})
        )
        mock_scanner.issues = [issue_1, issue_2]
        mock_scanner.excluded_paths = []
        options = generate_options(GlobalOptions, json=True, exclude_signatures=[])
        util.echo_result(options, mock_scanner, "/repo", "/output")

        mock_json.dumps.assert_called_once_with(
            {
                "scan_time": "now:now:now",
                "project_path": "/repo",
                "output_dir": "/output",
                "excluded_paths": [],
                "excluded_signatures": [],
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
            }
        )

    @mock.patch("tartufo.scanner.ScannerBase")
    @mock.patch("tartufo.util.click", new=mock.MagicMock())
    @mock.patch("tartufo.util.json")
    @mock.patch("tartufo.util.datetime")
    def test_echo_result_outputs_proper_json_when_requested_pathtype(
        self, mock_time, mock_json, mock_scanner
    ):
        mock_time.now.return_value.isoformat.return_value = "now:now:now"
        issue_1 = scanner.Issue(
            types.IssueType.Entropy, "foo", types.Chunk("foo", "/bar", {})
        )
        issue_2 = scanner.Issue(
            types.IssueType.RegEx, "bar", types.Chunk("foo", "/bar", {})
        )
        mock_scanner.issues = [issue_1, issue_2]
        mock_scanner.excluded_paths = [
            re.compile("package-lock.json"),
            re.compile("poetry.lock"),
        ]
        exclude_signatures = [
            "fffffffffffff",
            "ooooooooooooo",
        ]
        options = generate_options(
            GlobalOptions, json=True, exclude_signatures=exclude_signatures
        )
        util.echo_result(options, mock_scanner, "/repo", Path("/tmp"))
        mock_json.dumps.assert_called_once_with(
            {
                "scan_time": "now:now:now",
                "project_path": "/repo",
                "output_dir": str(Path("/tmp")),
                "excluded_paths": ["package-lock.json", "poetry.lock"],
                "excluded_signatures": [
                    "fffffffffffff",
                    "ooooooooooooo",
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
            }
        )


class GeneralUtilTests(unittest.TestCase):
    @mock.patch("tartufo.util.click", new=mock.MagicMock())
    def test_fail_exits_with_exit_code(self):
        mock_context = mock.MagicMock()
        util.fail("Foo!", mock_context, 42)
        mock_context.exit.assert_called_once_with(42)

    @mock.patch("tartufo.util.style_error")
    @mock.patch("tartufo.util.click")
    def test_fail_echos_styled_error_message(self, mock_click, mock_style):
        util.fail("Foo!", mock.MagicMock(), 42)
        mock_style.assert_called_once_with("Foo!")
        mock_click.echo.assert_called_once_with(mock_style.return_value, err=True)

    @mock.patch("tartufo.util.blake2s")
    def test_signature_is_generated_with_snippet_and_filename(self, mock_hash):
        util.generate_signature("foo", "bar")
        mock_hash.assert_called_once_with(b"foo$$bar")

    def test_get_strings_of_set_splits_string_by_chars_outside_charset(self):
        strings = util.get_strings_of_set("asdf.qwer", "asdfqwer", 1)
        self.assertEqual(strings, ["asdf", "qwer"])

    def test_get_strings_of_set_will_not_return_strings_below_threshold_length(self):
        strings = util.get_strings_of_set("w.asdf.q", "asdfqwer", 3)
        self.assertEqual(strings, ["asdf"])
