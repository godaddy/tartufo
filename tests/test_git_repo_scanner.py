# pylint: disable=protected-access
import pathlib
from pathlib import Path
import re
import unittest
from unittest import mock

from tartufo import scanner, types
from tartufo.types import GlobalOptions, GitOptions

from tests.helpers import generate_options


class ScannerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.global_options = generate_options(GlobalOptions, exclude_signatures=())
        self.git_options = generate_options(GitOptions)


class RepoLoadTests(ScannerTestCase):
    def setUp(self):
        self.data_dir = pathlib.Path(__file__).parent / "data"
        super().setUp()

    @mock.patch("tartufo.config.util.get_repository")
    def test_repo_is_loaded_on_init(self, mock_repo: mock.MagicMock):
        mock_repo.return_value = (pathlib.Path("."), None)
        scanner.GitLocalRepoScanner(self.global_options, self.git_options, ".")
        mock_repo.assert_called_once()

    @mock.patch("tartufo.config.util.get_repository")
    def test_load_repo_loads_new_repo(self, mock_repo: mock.MagicMock):
        repo_path = "../tartufo"
        mock_repo.return_value = (pathlib.Path(repo_path), None)
        test_scanner = scanner.GitLocalRepoScanner(
            self.global_options, self.git_options, "."
        )
        print("test_load_repo_loads_new_repo: load_repo(" + repo_path + ")")
        test_scanner.load_repo(repo_path)
        mock_repo.assert_has_calls(
            (
                mock.call(".", fetch=None, branch=None),
                mock.call("../tartufo", fetch=None, branch=None),
            )
        )

    @mock.patch("tartufo.config.load_config_from_path")
    @mock.patch("tartufo.config.util.get_repository")
    def test_extra_inclusions_get_added(
        self, mock_get_repo: mock.MagicMock, mock_load: mock.MagicMock
    ):
        mock_get_repo.return_value = (self.data_dir, None)
        mock_load.return_value = (
            self.data_dir / "pyproject.toml",
            {"include_paths": "include-files"},
        )
        test_scanner = scanner.GitLocalRepoScanner(
            self.global_options, self.git_options, str(self.data_dir)
        )
        self.assertEqual(
            test_scanner.included_paths,
            [re.compile("tartufo/"), re.compile("scripts/")],
        )

    @mock.patch("tartufo.config.load_config_from_path")
    @mock.patch("tartufo.util.get_repository")
    def test_extra_exclusions_get_added(
        self, mock_get_repo: mock.MagicMock, mock_load: mock.MagicMock
    ):
        mock_get_repo.return_value = (self.data_dir, None)
        mock_load.return_value = (
            self.data_dir / "pyproject.toml",
            {"exclude_paths": "exclude-files"},
        )
        test_scanner = scanner.GitLocalRepoScanner(
            self.global_options, self.git_options, str(self.data_dir)
        )

        self.assertEqual(
            test_scanner.excluded_paths,
            [
                re.compile("tests/"),
                re.compile(r"\.venv/"),
                re.compile(r".*\.egg-info/"),
            ],
        )

    @mock.patch("tartufo.config.load_config_from_path")
    @mock.patch("tartufo.config.util.get_repository")
    def test_extra_signatures_get_added(
        self, mock_get_repo: mock.MagicMock, mock_load: mock.MagicMock
    ):
        self.global_options.exclude_signatures = ()
        mock_get_repo.return_value = (self.data_dir, None)
        mock_load.return_value = (
            self.data_dir / "pyproject.toml",
            {"exclude_signatures": ["foo", "bar"]},
        )
        test_scanner = scanner.GitLocalRepoScanner(
            self.global_options, self.git_options, str(self.data_dir)
        )
        test_scanner.load_repo(str(self.data_dir))
        self.assertEqual(
            sorted(test_scanner.global_options.exclude_signatures), ["bar", "foo"]
        )


class ChunkGeneratorTests(ScannerTestCase):
    @mock.patch("pygit2.RemoteCallbacks")
    @mock.patch("pygit2.Repository")
    def test_single_branch_is_loaded_if_specified(
        self, mock_repo: mock.MagicMock, mock_callback: mock.MagicMock
    ):
        self.git_options.branch = "foo"
        self.git_options.fetch = True
        mock_fetch = mock.MagicMock()
        mock_fetch.return_value = []
        mock_repo.return_value.remotes["origin"].fetch = mock_fetch
        test_scanner = scanner.GitLocalRepoScanner(
            self.global_options, self.git_options, "."
        )
        for _ in test_scanner.chunks:
            pass
        mock_fetch.assert_called_once_with("foo", callbacks=mock_callback.return_value)

    @mock.patch("pygit2.RemoteCallbacks")
    @mock.patch("pygit2.Repository")
    def test_all_branches_are_loaded_if_specified(
        self, mock_repo: mock.MagicMock, mock_callback: mock.MagicMock
    ):
        mock_fetch = mock.MagicMock()
        mock_fetch.return_value = []
        mock_repo.return_value.remotes["origin"].fetch = mock_fetch
        self.git_options.fetch = True
        test_scanner = scanner.GitLocalRepoScanner(
            self.global_options, self.git_options, "."
        )
        for _ in test_scanner.chunks:
            pass
        mock_fetch.assert_called_once_with(callbacks=mock_callback.return_value)

    @mock.patch("pygit2.Repository")
    def test_explicit_exception_is_raised_if_fetch_fails(
        self, mock_repo: mock.MagicMock
    ):
        self.git_options.fetch = True
        mock_repo.return_value.remotes[
            "origin"
        ].fetch.side_effect = types.GitRemoteException(
            "Could not locate working ssh credentials"
        )

        with self.assertRaisesRegex(
            types.GitRemoteException, "Could not locate working ssh credentials"
        ):
            test_scanner = scanner.GitLocalRepoScanner(
                self.global_options, self.git_options, "."
            )

            for _ in test_scanner.chunks:
                pass

    @mock.patch("tartufo.scanner.GitScanner._iter_diff")
    @mock.patch("tartufo.util.get_repository")
    def test_all_branches_are_scanned_for_commits(
        self, mock_get_repo: mock.MagicMock, mock_iter_diff: mock.MagicMock
    ):
        mock_repo = mock.MagicMock()
        mock_repo.branches = {"foo": mock.MagicMock(), "bar": mock.MagicMock()}
        mock_get_repo.return_value = (Path("/foo"), mock_repo)

        test_scanner = scanner.GitLocalRepoScanner(
            self.global_options, self.git_options, "."
        )

        mock_commit_1 = mock.MagicMock()
        mock_commit_1.parents = None
        mock_commit_2 = mock.MagicMock()
        mock_commit_2.parents = [mock_commit_1]
        mock_commit_3 = mock.MagicMock()
        mock_commit_3.parents = [mock_commit_2]

        mock_repo.walk.return_value = [
            mock_commit_3,
            mock_commit_2,
            mock_commit_1,
        ]

        mock_iter_diff.return_value = []
        for _ in test_scanner.chunks:
            pass

        # TODO: Change this to expect a compare of mock_commit_1 to tree
        mock_repo.diff.assert_has_calls(
            (
                mock.call(mock_commit_3, mock_commit_2),
                mock.call(mock_commit_2, mock_commit_1),
                mock.call(mock_commit_3, mock_commit_2),
                mock.call(mock_commit_2, mock_commit_1),
            )
        )

    @mock.patch("tartufo.scanner.GitRepoScanner._iter_diff")
    @mock.patch("tartufo.util.get_repository")
    def test_all_commits_are_scanned_for_files(
        self, mock_get_repo: mock.MagicMock, mock_iter_diff: mock.MagicMock,
    ):
        print("******************************************************************")
        self.git_options.fetch = True
        mock_repo = mock.MagicMock()
        mock_repo.branches = {"foo": mock.MagicMock()}
        mock_get_repo.return_value = (Path("/foo"), mock_repo)

        test_scanner = scanner.GitLocalRepoScanner(
            self.global_options, self.git_options, "."
        )
        mock_commit_1 = mock.MagicMock()
        mock_commit_1.parents = None
        mock_commit_2 = mock.MagicMock()
        mock_commit_2.parents = [mock_commit_1]
        mock_commit_3 = mock.MagicMock()
        mock_commit_3.parents = [mock_commit_2]

        mock_repo.walk.return_value = [
            mock_commit_3,
            mock_commit_2,
            mock_commit_1,
        ]
        mock_iter_diff.return_value = []
        for _ in test_scanner.chunks:
            pass

        self.assertEqual(len(mock_iter_diff.mock_calls), 3)

    @mock.patch("tartufo.scanner.GitScanner._iter_diff")
    @mock.patch("tartufo.util.extract_commit_metadata")
    @mock.patch("tartufo.util.get_repository")
    def test_all_files_are_yielded_as_chunks(
        self,
        mock_get_repo: mock.MagicMock,
        mock_extract: mock.MagicMock,
        mock_iter_diff: mock.MagicMock,
    ):
        self.git_options.fetch = True
        mock_repo = mock.MagicMock()
        mock_repo.return_value.remotes.origin.fetch.return_value = ["foo"]
        mock_repo.branches = {"foo": mock.MagicMock()}
        mock_get_repo.return_value = (Path("/foo"), mock_repo)

        mock_repo.return_value.remotes.origin.fetch.return_value = ["foo"]
        test_scanner = scanner.GitLocalRepoScanner(
            self.global_options, self.git_options, "."
        )

        mock_commit_1 = mock.MagicMock()
        mock_commit_1.parents = None
        mock_commit_2 = mock.MagicMock()
        mock_commit_2.parents = [mock_commit_1]
        mock_commit_3 = mock.MagicMock()
        mock_commit_3.parents = [mock_commit_2]

        mock_repo.walk.return_value = [
            mock_commit_3,
            mock_commit_2,
            mock_commit_1,
        ]

        mock_iter_diff.return_value = [("foo", "bar.py"), ("baz", "blah.py")]
        chunks = list(test_scanner.chunks)
        # These get duplicated in this test, because `_iter_diff` is called
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
    @mock.patch("pygit2.Repository", new=mock.MagicMock())
    def test_binary_files_are_skipped(self):
        mock_diff = mock.MagicMock()
        mock_diff.delta.is_binary = True
        test_scanner = scanner.GitLocalRepoScanner(
            self.global_options, self.git_options, "."
        )
        diffs = list(test_scanner._iter_diff([mock_diff]))
        self.assertEqual(diffs, [])

    @mock.patch("pygit2.Repository", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.ScannerBase.should_scan")
    def test_excluded_files_are_not_scanned(self, mock_should: mock.MagicMock):
        mock_should.return_value = False
        mock_diff = mock.MagicMock()
        mock_diff.delta.is_binary = False
        test_scanner = scanner.GitLocalRepoScanner(
            self.global_options, self.git_options, "."
        )
        diffs = list(test_scanner._iter_diff([mock_diff]))
        self.assertEqual(diffs, [])
        mock_should.assert_called_once()

    @mock.patch("pygit2.Repository", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.ScannerBase.should_scan")
    def test_all_files_are_yielded(self, mock_should: mock.MagicMock):
        mock_should.return_value = True
        mock_diff_1 = mock.MagicMock()
        mock_diff_1.delta.is_binary = False
        mock_diff_1.text = "+ Ford Prefect"
        mock_diff_1.delta.new_file.path = "/foo"
        mock_diff_2 = mock.MagicMock()
        mock_diff_2.delta.is_binary = False
        mock_diff_2.text = "- Marvin"
        mock_diff_2.delta.new_file.path = "/bar"
        test_scanner = scanner.GitLocalRepoScanner(
            self.global_options, self.git_options, "."
        )
        diffs = list(test_scanner._iter_diff([mock_diff_1, mock_diff_2]))
        self.assertEqual(
            diffs, [("+ Ford Prefect", "/foo"), ("- Marvin", "/bar"),],
        )


class IterBranchCommitsTests(ScannerTestCase):
    @mock.patch("pygit2.Repository", new=mock.MagicMock())
    def test_all_commits_get_yielded_in_pairs(self):
        test_scanner = scanner.GitLocalRepoScanner(
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

    @mock.patch("pygit2.Repository", new=mock.MagicMock())
    def test_iteration_stops_when_since_commit_is_reached(self):
        self.git_options.since_commit = "42"
        test_scanner = scanner.GitLocalRepoScanner(
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
