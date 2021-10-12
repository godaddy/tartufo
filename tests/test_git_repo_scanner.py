# pylint: disable=protected-access
import pathlib
import re
import unittest
from unittest import mock

import git

from tartufo import scanner, types
from tartufo.types import GlobalOptions, GitOptions, TartufoException

from tests.helpers import generate_options


class ScannerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.global_options = generate_options(GlobalOptions)
        self.git_options = generate_options(GitOptions)


class RepoLoadTests(ScannerTestCase):
    def setUp(self):
        self.data_dir = pathlib.Path(__file__).parent / "data"
        super().setUp()

    @mock.patch("git.Repo")
    def test_repo_is_loaded_on_init(self, mock_repo: mock.MagicMock):
        scanner.GitRepoScanner(self.global_options, self.git_options, ".")
        mock_repo.assert_called_once_with(".")

    @mock.patch("git.Repo")
    @mock.patch(
        "tartufo.scanner.GitRepoScanner.filter_submodules", new=mock.MagicMock()
    )
    def test_load_repo_loads_new_repo(self, mock_repo: mock.MagicMock):
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        test_scanner.load_repo("../tartufo")
        mock_repo.assert_has_calls((mock.call("."), mock.call("../tartufo")))

    @mock.patch("git.Repo")
    @mock.patch("tartufo.scanner.GitRepoScanner.filter_submodules")
    def test_load_repo_filters_submodules_when_specified(
        self, mock_filter: mock.MagicMock, mock_repo: mock.MagicMock
    ):
        self.git_options.include_submodules = False
        scanner.GitRepoScanner(self.global_options, self.git_options, ".")
        mock_filter.assert_called_once_with(mock_repo.return_value)

    @mock.patch("git.Repo", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.GitRepoScanner.filter_submodules")
    def test_load_repo_does_not_filter_submodules_when_requested(
        self, mock_filter: mock.MagicMock
    ):
        self.git_options.include_submodules = True
        scanner.GitRepoScanner(self.global_options, self.git_options, ".")
        mock_filter.assert_not_called()

    @mock.patch("git.Repo", new=mock.MagicMock())
    @mock.patch("tartufo.config.load_config_from_path")
    def test_extra_inclusions_get_added(self, mock_load: mock.MagicMock):
        mock_load.return_value = (
            self.data_dir / "pyproject.toml",
            {"include_paths": "include-files", "include_path_patterns": ("foo/",)},
        )
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, str(self.data_dir)
        )
        test_scanner.load_repo("../tartufo")
        self.assertCountEqual(
            test_scanner.included_paths,
            [re.compile("foo/"), re.compile("tartufo/"), re.compile("scripts/")],
        )

    @mock.patch("git.Repo", new=mock.MagicMock())
    @mock.patch("tartufo.config.load_config_from_path")
    def test_extra_exclusions_get_added(self, mock_load: mock.MagicMock):
        mock_load.return_value = (
            self.data_dir / "pyproject.toml",
            {"exclude_paths": "exclude-files", "exclude_path_patterns": ("bar/",)},
        )
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, str(self.data_dir)
        )
        test_scanner.load_repo("../tartufo")
        self.assertCountEqual(
            test_scanner.excluded_paths,
            [
                re.compile("bar/"),
                re.compile("tests/"),
                re.compile(r"\.venv/"),
                re.compile(r".*\.egg-info/"),
            ],
        )

    @mock.patch("git.Repo", new=mock.MagicMock())
    @mock.patch("tartufo.config.load_config_from_path")
    def test_extra_signatures_get_added(self, mock_load: mock.MagicMock):
        self.global_options.exclude_signatures = ()
        mock_load.return_value = (
            self.data_dir / "pyproject.toml",
            {"exclude_signatures": ["foo", "bar"]},
        )
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, str(self.data_dir)
        )
        test_scanner.load_repo("../tartufo")
        self.assertEqual(
            sorted(test_scanner.global_options.exclude_signatures), ["bar", "foo"]
        )


class FilterSubmoduleTests(ScannerTestCase):
    @mock.patch("git.Repo")
    def test_filter_submodules_adds_all_submodule_paths_to_exclusions(
        self, mock_repo: mock.MagicMock
    ):
        class FakeSubmodule:
            path: str

            def __init__(self, path: str):
                self.path = path

        self.git_options.include_submodules = False
        mock_repo.return_value.submodules = [FakeSubmodule("foo"), FakeSubmodule("bar")]
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        self.assertCountEqual(
            test_scanner.excluded_paths, [re.compile("^foo"), re.compile("^bar")]
        )

    @mock.patch("git.Repo")
    def test_filter_submodules_handles_broken_submodules_explicitly(
        self, mock_repo: mock.MagicMock
    ):
        self.git_options.include_submodules = False
        mock_repo.return_value.submodules.__iter__.side_effect = AttributeError
        with self.assertRaisesRegex(
            TartufoException, "There was an error while parsing submodules"
        ):
            scanner.GitRepoScanner(self.global_options, self.git_options, ".")


class ChunkGeneratorTests(ScannerTestCase):
    @mock.patch("git.Repo")
    def test_single_branch_is_loaded_if_specified(self, mock_repo: mock.MagicMock):
        self.git_options.branch = "foo"
        self.git_options.fetch = True
        mock_fetch = mock.MagicMock()
        mock_fetch.return_value = []
        mock_branch = mock.MagicMock()
        mock_branch.name = "foo"
        mock_repo.return_value.branches = [mock_branch]
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
        self.git_options.fetch = True
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        for _ in test_scanner.chunks:
            pass
        mock_fetch.assert_called_once_with()

    @mock.patch("git.Repo")
    def test_explicit_exception_is_raised_if_fetch_fails(
        self, mock_repo: mock.MagicMock
    ):
        self.git_options.fetch = True
        mock_repo.return_value.remotes.origin.fetch.side_effect = git.GitCommandError(
            command="git fetch -v origin", status=42, stderr="Fetch failed!"
        )
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        with self.assertRaisesRegex(
            types.GitRemoteException, "stderr: 'Fetch failed!'"
        ):
            for _ in test_scanner.chunks:
                pass

    @mock.patch("tartufo.scanner.GitRepoScanner._iter_branch_commits")
    @mock.patch("git.Repo")
    def test_all_branches_are_scanned_for_commits(
        self, mock_repo: mock.MagicMock, mock_iter_commits: mock.MagicMock
    ):
        self.git_options.fetch = True
        mock_repo.return_value.remotes.origin.fetch.return_value = ["foo", "bar"]
        mock_repo.return_value.branches = ["foo", "bar"]
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
    @mock.patch("git.Repo")
    def test_scan_all_branches_fetch_false(
        self, mock_repo: mock.MagicMock, mock_iter_commits: mock.MagicMock
    ):
        self.git_options.fetch = False
        mock_repo.return_value.remotes.origin.fetch.return_value = ["foo", "bar"]
        mock_repo.return_value.branches = ["foo", "bar"]
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
    @mock.patch("git.Repo")
    def test_scan_single_branch_fetch_false(
        self, mock_repo: mock.MagicMock, mock_iter_commits: mock.MagicMock
    ):
        self.git_options.fetch = False
        self.git_options.branch = "bar"
        mock_foo = mock.MagicMock()
        mock_foo.name = "foo"
        mock_bar = mock.MagicMock()
        mock_bar.name = "bar"
        mock_repo.return_value.remotes.origin.fetch.return_value = ["foo", "bar"]
        mock_repo.return_value.branches = [mock_foo, mock_bar]
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        mock_iter_commits.return_value = []
        for _ in test_scanner.chunks:
            pass
        mock_repo.return_value.remotes.origin.fetch.assert_not_called()
        mock_iter_commits.assert_has_calls(
            (mock.call(mock_repo.return_value, mock_bar),)
        )

    @mock.patch("tartufo.scanner.GitRepoScanner._iter_branch_commits")
    @mock.patch("git.Repo")
    def test_scan_single_branch_throws_exception_when_branch_not_found(
        self, mock_repo: mock.MagicMock, mock_iter_commits: mock.MagicMock
    ):
        self.git_options.fetch = True
        self.git_options.branch = "not-found"
        self.global_options.entropy = True
        mock_foo = mock.MagicMock()
        mock_foo.name = "foo"
        mock_bar = mock.MagicMock()
        mock_bar.name = "bar"
        mock_repo.return_value.remotes.origin.fetch.return_value = ["foo", "bar"]
        mock_repo.return_value.branches = [mock_foo, mock_bar]

        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        mock_iter_commits.return_value = []
        with self.assertRaises(types.BranchNotFoundException):
            list(test_scanner.scan())

    @mock.patch("tartufo.scanner.GitRepoScanner._iter_branch_commits")
    @mock.patch("git.Repo")
    def test_scan_single_branch_fetch_true(
        self, mock_repo: mock.MagicMock, mock_iter_commits: mock.MagicMock
    ):
        self.git_options.fetch = True
        self.git_options.branch = "bar"
        mock_foo = mock.MagicMock()
        mock_foo.name = "foo"
        mock_bar = mock.MagicMock()
        mock_bar.name = "bar"
        mock_repo.return_value.remotes.origin.fetch.return_value = ["foo", "bar"]
        mock_repo.return_value.branches = [mock_foo, mock_bar]
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        mock_iter_commits.return_value = []
        for _ in test_scanner.chunks:
            pass
        mock_repo.return_value.remotes.origin.fetch.assert_called()
        mock_iter_commits.assert_has_calls(
            (mock.call(mock_repo.return_value, mock_bar),)
        )

    @mock.patch("tartufo.scanner.GitRepoScanner._iter_branch_commits")
    @mock.patch("tartufo.scanner.GitRepoScanner._iter_diff_index")
    @mock.patch("git.Repo")
    def test_all_commits_are_scanned_for_files(
        self,
        mock_repo: mock.MagicMock,
        mock_iter_diff_index: mock.MagicMock,
        mock_iter_commits: mock.MagicMock,
    ):
        self.git_options.fetch = True
        mock_repo.return_value.remotes.origin.fetch.return_value = ["foo"]
        mock_repo.return_value.branches = ["foo"]
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
        mock_iter_diff_index.return_value = []
        for _ in test_scanner.chunks:
            pass
        mock_commit_2.diff.assert_called_once_with(mock_commit_3, create_patch=True)
        mock_commit_1.diff.assert_has_calls(
            (
                mock.call(mock_commit_2, create_patch=True),
                mock.call(git.NULL_TREE, create_patch=True),
            )
        )
        mock_iter_diff_index.assert_has_calls(
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
        mock_iter_diff_index: mock.MagicMock,
        mock_iter_commits: mock.MagicMock,
    ):
        self.git_options.fetch = True
        mock_repo.return_value.remotes.origin.fetch.return_value = ["foo"]
        mock_repo.return_value.branches = ["foo"]
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        mock_commit_1 = mock.MagicMock()
        mock_commit_2 = mock.MagicMock()
        mock_iter_commits.return_value = [(mock_commit_1, mock_commit_2)]
        mock_iter_diff_index.return_value = [("foo", "bar.py"), ("baz", "blah.py")]
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
            commits,
            [(mock_commit_2, mock_commit_1)],
        )


if __name__ == "__main__":
    unittest.main()
