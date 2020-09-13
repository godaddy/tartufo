# pylint: disable=protected-access
import unittest
from unittest import mock

import git

from tartufo import scanner, types
from tartufo.types import GlobalOptions, GitOptions

from tests.helpers import generate_options


class ScannerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.global_options = generate_options(GlobalOptions)
        self.git_options = generate_options(GitOptions)


class RepoLoadTests(ScannerTestCase):
    @mock.patch("git.Repo")
    def test_repo_is_loaded_on_init(self, mock_repo: mock.MagicMock):
        scanner.GitRepoScanner(self.global_options, self.git_options, ".")
        mock_repo.assert_called_once_with(".")

    @mock.patch("git.Repo")
    def test_load_repo_loads_new_repo(self, mock_repo: mock.MagicMock):
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        test_scanner.load_repo("../tartufo")
        mock_repo.assert_has_calls((mock.call("."), mock.call("../tartufo")))


class ChunkGeneratorTests(ScannerTestCase):
    @mock.patch("git.Repo")
    def test_single_branch_is_loaded_if_specified(self, mock_repo: mock.MagicMock):
        self.git_options.branch = "foo"
        mock_fetch = mock.MagicMock()
        mock_fetch.return_value = []
        mock_repo.return_value.remotes.origin.fetch = mock_fetch
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        for _ in test_scanner.chunks:
            pass
        mock_fetch.assert_called_once_with("foo")

    @mock.patch("git.Repo")
    def test_all_branches_are_loaded_if_specified(self, mock_repo: mock.MagicMock):
        mock_fetch = mock.MagicMock()
        mock_fetch.return_value = []
        mock_repo.return_value.remotes.origin.fetch = mock_fetch
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        for _ in test_scanner.chunks:
            pass
        mock_fetch.assert_called_once_with()

    @mock.patch("tartufo.scanner.GitRepoScanner._iter_branch_commits")
    @mock.patch("git.Repo")
    def test_all_branches_are_scanned_for_commits(
        self, mock_repo: mock.MagicMock, mock_iter_commits: mock.MagicMock
    ):
        mock_repo.return_value.remotes.origin.fetch.return_value = ["foo", "bar"]
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
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
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
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
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
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


class IterDiffIndexTests(ScannerTestCase):
    @mock.patch("git.Repo", new=mock.MagicMock())
    def test_binary_files_are_skipped(self):
        mock_diff = mock.MagicMock()
        mock_diff.diff.decode.return_value = "Binary files\n101010"
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        diffs = list(test_scanner._iter_diff_index([mock_diff]))
        self.assertEqual(diffs, [])

    @mock.patch("git.Repo", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.ScannerBase.should_scan")
    def test_excluded_files_are_not_scanned(self, mock_should: mock.MagicMock):
        mock_should.return_value = False
        mock_diff = mock.MagicMock()
        mock_diff.diff.decode.return_value = "+ Ford Prefect"
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        diffs = list(test_scanner._iter_diff_index([mock_diff]))
        self.assertEqual(diffs, [])
        mock_should.assert_called_once()

    @mock.patch("git.Repo", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.ScannerBase.should_scan")
    def test_all_files_are_yielded(self, mock_should: mock.MagicMock):
        mock_should.return_value = True
        mock_diff_1 = mock.MagicMock()
        mock_diff_1.diff.decode.return_value = "+ Ford Prefect"
        mock_diff_2 = mock.MagicMock()
        mock_diff_2.diff.decode.return_value = "- Marvin"
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        diffs = list(test_scanner._iter_diff_index([mock_diff_1, mock_diff_2]))
        self.assertEqual(
            diffs,
            [("+ Ford Prefect", mock_diff_1.b_path), ("- Marvin", mock_diff_2.b_path)],
        )


class IterBranchCommitsTests(ScannerTestCase):
    @mock.patch("git.Repo", new=mock.MagicMock())
    def test_all_commits_get_yielded_in_pairs(self):
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        mock_repo = mock.MagicMock()
        mock_branch = mock.MagicMock(name="foo")
        mock_commit_1 = mock.MagicMock()
        mock_commit_2 = mock.MagicMock()
        mock_commit_3 = mock.MagicMock()
        mock_commit_4 = mock.MagicMock()
        mock_repo.iter_commits.return_value = [
            mock_commit_1,
            mock_commit_2,
            mock_commit_3,
            mock_commit_4,
        ]
        commits = list(test_scanner._iter_branch_commits(mock_repo, mock_branch))
        self.assertEqual(
            commits,
            [
                (mock_commit_2, mock_commit_1),
                (mock_commit_3, mock_commit_2),
                (mock_commit_4, mock_commit_3),
            ],
        )

    @mock.patch("git.Repo", new=mock.MagicMock())
    def test_iteration_stops_when_since_commit_is_reached(self):
        self.git_options.since_commit = "42"
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        mock_repo = mock.MagicMock()
        mock_branch = mock.MagicMock(name="foo")
        mock_commit_1 = mock.MagicMock()
        mock_commit_2 = mock.MagicMock()
        mock_commit_3 = mock.MagicMock()
        mock_commit_3.hexsha = "42"
        mock_commit_4 = mock.MagicMock()
        mock_repo.iter_commits.return_value = [
            mock_commit_1,
            mock_commit_2,
            mock_commit_3,
            mock_commit_4,
        ]
        commits = list(test_scanner._iter_branch_commits(mock_repo, mock_branch))
        # Because "since commit" is exclusive, only the 2 commits before it are ever yielded
        self.assertEqual(
            commits, [(mock_commit_2, mock_commit_1)],
        )


if __name__ == "__main__":
    unittest.main()
