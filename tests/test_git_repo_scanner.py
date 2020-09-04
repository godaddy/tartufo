# pylint: disable=protected-access
import unittest
from unittest import mock

import git

from tartufo import scanner, types
from tartufo.types import GitOptions

from tests.helpers import generate_options


class ScannerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.options = generate_options(GitOptions)


class RepoLoadTests(ScannerTestCase):
    @mock.patch("git.Repo")
    def test_repo_is_loaded_on_init(self, mock_repo: mock.MagicMock):
        scanner.GitRepoScanner(self.options, ".")
        mock_repo.assert_called_once_with(".")

    @mock.patch("git.Repo")
    def test_load_repo_loads_new_repo(self, mock_repo: mock.MagicMock):
        test_scanner = scanner.GitRepoScanner(self.options, ".")
        test_scanner.load_repo("../tartufo")
        mock_repo.assert_has_calls((mock.call("."), mock.call("../tartufo")))


class ChunkGeneratorTests(ScannerTestCase):
    @mock.patch("git.Repo")
    def test_single_branch_is_loaded_if_specified(self, mock_repo: mock.MagicMock):
        self.options.branch = "foo"
        mock_fetch = mock.MagicMock()
        mock_fetch.return_value = []
        mock_repo.return_value.remotes.origin.fetch = mock_fetch
        test_scanner = scanner.GitRepoScanner(self.options, ".")
        for _ in test_scanner.chunks:
            pass
        mock_fetch.assert_called_once_with("foo")

    @mock.patch("git.Repo")
    def test_all_branches_are_loaded_if_specified(self, mock_repo: mock.MagicMock):
        mock_fetch = mock.MagicMock()
        mock_fetch.return_value = []
        mock_repo.return_value.remotes.origin.fetch = mock_fetch
        test_scanner = scanner.GitRepoScanner(self.options, ".")
        for _ in test_scanner.chunks:
            pass
        mock_fetch.assert_called_once_with()

    @mock.patch("tartufo.scanner.GitRepoScanner._iter_branch_commits")
    @mock.patch("git.Repo")
    def test_all_branches_are_scanned_for_commits(
        self, mock_repo: mock.MagicMock, mock_iter_commits: mock.MagicMock
    ):
        mock_repo.return_value.remotes.origin.fetch.return_value = ["foo", "bar"]
        test_scanner = scanner.GitRepoScanner(self.options, ".")
        mock_iter_commits.return_value = []
        for _ in test_scanner.chunks:
            pass
        mock_iter_commits.assert_has_calls(
            (
                mock.call(mock_repo.return_value, "foo"),
                mock.call(mock_repo.return_value, "bar"),
            )
        )

    @mock.patch("tartufo.scanner.GitRepoScanner._iter_branch_commits")
    @mock.patch("tartufo.scanner.GitRepoScanner._iter_diff_index")
    @mock.patch("git.Repo")
    def test_all_commits_are_scanned_for_files(
        self,
        mock_repo: mock.MagicMock,
        mock_iter_diff: mock.MagicMock,
        mock_iter_commits: mock.MagicMock,
    ):
        mock_repo.return_value.remotes.origin.fetch.return_value = ["foo"]
        test_scanner = scanner.GitRepoScanner(self.options, ".")
        mock_commit_1 = mock.MagicMock()
        mock_commit_2 = mock.MagicMock()
        mock_commit_3 = mock.MagicMock()
        mock_iter_commits.return_value = [
            (mock_commit_2, mock_commit_3),
            (mock_commit_1, mock_commit_2),
        ]
        mock_iter_diff.return_value = []
        for _ in test_scanner.chunks:
            pass
        mock_commit_2.diff.assert_called_once_with(mock_commit_3, create_patch=True)
        mock_commit_1.diff.assert_has_calls(
            (
                mock.call(mock_commit_2, create_patch=True),
                mock.call(git.NULL_TREE, create_patch=True),
            )
        )
        mock_iter_diff.assert_has_calls(
            (
                mock.call(mock_commit_2.diff.return_value),
                mock.call(mock_commit_1.diff.return_value),
                mock.call(mock_commit_1.diff.return_value),
            )
        )

    @mock.patch("tartufo.scanner.GitRepoScanner._iter_branch_commits")
    @mock.patch("tartufo.scanner.GitRepoScanner._iter_diff_index")
    @mock.patch("tartufo.util.extract_commit_metadata")
    @mock.patch("git.Repo")
    def test_all_files_are_yielded_as_chunks(
        self,
        mock_repo: mock.MagicMock,
        mock_extract: mock.MagicMock,
        mock_iter_diff: mock.MagicMock,
        mock_iter_commits: mock.MagicMock,
    ):
        mock_repo.return_value.remotes.origin.fetch.return_value = ["foo"]
        test_scanner = scanner.GitRepoScanner(self.options, ".")
        mock_commit_1 = mock.MagicMock()
        mock_commit_2 = mock.MagicMock()
        mock_iter_commits.return_value = [(mock_commit_1, mock_commit_2)]
        mock_iter_diff.return_value = [("foo", "bar.py"), ("baz", "blah.py")]
        chunks = list(test_scanner.chunks)
        # These get duplicated in this test, because `_iter_diff_index` is called
        # both in the normal branch/commit iteration, and then once more afterward
        # to capture the first commit on the branch
        self.assertEqual(
            chunks,
            [
                types.Chunk("foo", "bar.py", mock_extract.return_value),
                types.Chunk("baz", "blah.py", mock_extract.return_value),
                types.Chunk("foo", "bar.py", mock_extract.return_value),
                types.Chunk("baz", "blah.py", mock_extract.return_value),
            ],
        )


if __name__ == "__main__":
    unittest.main()
