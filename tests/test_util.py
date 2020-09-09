import unittest
from pathlib import Path
from unittest import mock

from tartufo import scanner, types, util


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
    def test_tartufo_clones_git_repo_into_temp_dir(self, mock_mkdtemp, mock_clone):
        util.clone_git_repo("https://github.com/godaddy/tartufo.git")
        mock_clone.assert_called_once_with(
            "https://github.com/godaddy/tartufo.git", mock_mkdtemp.return_value
        )

    @mock.patch("git.Repo.clone_from", new=mock.MagicMock())
    @mock.patch("tartufo.util.tempfile.mkdtemp")
    def test_clone_git_repo_returns_path_to_clone(self, mock_mkdtemp):
        repo_path = util.clone_git_repo("https://github.com/godaddy/tartufo.git")
        self.assertEqual(repo_path, mock_mkdtemp.return_value)


class OutputTests(unittest.TestCase):
    @mock.patch("tartufo.util.click")
    def test_echo_issues_echos_all_when_not_json(self, mock_click):
        util.echo_issues([1, 2, 3, 4], False, "", "")
        mock_click.echo.assert_has_calls(
            (mock.call(1), mock.call(2), mock.call(3), mock.call(4)), any_order=False
        )

    @mock.patch("tartufo.util.click", new=mock.MagicMock())
    @mock.patch("tartufo.util.json")
    def test_echo_issues_outputs_proper_json_when_requested(self, mock_json):
        issue_1 = scanner.Issue(
            scanner.IssueType.Entropy, "foo", types.Chunk("foo", "/bar")
        )
        issue_2 = scanner.Issue(
            scanner.IssueType.RegEx, "bar", types.Chunk("foo", "/bar")
        )
        util.echo_issues([issue_1, issue_2], True, "/repo", "/output")
        mock_json.dumps.assert_called_once_with(
            {
                "project_path": "/repo",
                "issues_path": "/output",
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

    @mock.patch("tartufo.util.click", new=mock.MagicMock())
    @mock.patch("tartufo.util.json")
    def test_echo_issues_outputs_proper_json_when_requested_pathtype(self, mock_json):
        issue_1 = scanner.Issue(
            scanner.IssueType.Entropy, "foo", types.Chunk("foo", "/bar")
        )
        issue_2 = scanner.Issue(
            scanner.IssueType.RegEx, "bar", types.Chunk("foo", "/bar")
        )
        util.echo_issues([issue_1, issue_2], True, "/repo", Path("/tmp"))
        mock_json.dumps.assert_called_once_with(
            {
                "project_path": "/repo",
                "issues_path": "/tmp",
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

    @mock.patch("tartufo.util.shutil")
    def test_clean_outputs_deletes_output_directory_if_it_exists(self, mock_shutil):
        class ExistingDir:
            def is_dir(self):
                return True

        output = ExistingDir()
        util.clean_outputs(output)
        mock_shutil.rmtree.assert_called_once_with(output)

    @mock.patch("tartufo.util.shutil")
    def test_clean_outputs_does_nothing_if_output_dir_doesnt_exist(self, mock_shutil):
        util.clean_outputs(None)
        mock_shutil.rmtree.assert_not_called()


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
