# pylint: disable=protected-access
import pathlib
import re
import unittest
from unittest import mock

import pygit2

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

    @mock.patch("pygit2.Repository")
    def test_repo_is_loaded_on_init(self, mock_repo: mock.MagicMock):
        scanner.GitRepoScanner(self.global_options, self.git_options, ".")
        mock_repo.assert_called_once_with(".")

    @mock.patch(
        "tartufo.scanner.GitRepoScanner.filter_submodules", new=mock.MagicMock()
    )
    @mock.patch("pygit2.Repository")
    def test_load_repo_loads_new_repo(self, mock_repo: mock.MagicMock):
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        test_scanner.load_repo("../tartufo")
        mock_repo.assert_has_calls((mock.call("."), mock.call("../tartufo")))

    @mock.patch("pygit2.Repository")
    @mock.patch("tartufo.scanner.GitRepoScanner.filter_submodules")
    def test_load_repo_filters_submodules_when_specified(
        self, mock_filter: mock.MagicMock, mock_repo: mock.MagicMock
    ):
        self.git_options.include_submodules = False
        scanner.GitRepoScanner(self.global_options, self.git_options, ".")
        mock_filter.assert_called_once_with(mock_repo.return_value)

    @mock.patch("pygit2.Repository", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.GitRepoScanner.filter_submodules")
    def test_load_repo_does_not_filter_submodules_when_requested(
        self, mock_filter: mock.MagicMock
    ):
        self.git_options.include_submodules = True
        scanner.GitRepoScanner(self.global_options, self.git_options, ".")
        mock_filter.assert_not_called()

    @mock.patch("pygit2.Repository", new=mock.MagicMock())
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

    @mock.patch("pygit2.Repository", new=mock.MagicMock())
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

    @mock.patch("pygit2.Repository", new=mock.MagicMock())
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
    @mock.patch("pygit2.Repository")
    def test_filter_submodules_adds_all_submodule_paths_to_exclusions(
        self, mock_repo: mock.MagicMock
    ):
        class FakeSubmodule:
            path: str

            def __init__(self, path: str):
                self.path = path

        self.git_options.include_submodules = False
        mock_repo.return_value.listall_submodules.return_value = [
            FakeSubmodule("foo"),
            FakeSubmodule("bar"),
        ]
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        self.assertCountEqual(
            test_scanner.excluded_paths, [re.compile("^foo"), re.compile("^bar")]
        )

    @mock.patch("pygit2.Repository")
    def test_filter_submodules_handles_broken_submodules_explicitly(
        self, mock_repo: mock.MagicMock
    ):
        self.git_options.include_submodules = False
        mock_repo.return_value.listall_submodules.return_value.__iter__.side_effect = (
            AttributeError
        )
        with self.assertRaisesRegex(
            TartufoException, "There was an error while parsing submodules"
        ):
            scanner.GitRepoScanner(self.global_options, self.git_options, ".")


class ChunkGeneratorTests(ScannerTestCase):
    @mock.patch("tartufo.scanner.GitScanner._iter_diff_index")
    @mock.patch("pygit2.Repository")
    def test_all_branches_are_scanned_for_commits(
        self, mock_repo: mock.MagicMock, mock_iter_diff: mock.MagicMock
    ):
        mock_branch_foo = mock.MagicMock()
        mock_branch_bar = mock.MagicMock()
        mock_repo.return_value.branches = {
            "foo": mock_branch_foo,
            "bar": mock_branch_bar,
        }
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )

        mock_commit_1 = mock.MagicMock()
        mock_commit_1.parents = None
        mock_commit_2 = mock.MagicMock()
        mock_commit_2.parents = [mock_commit_1]
        mock_commit_3 = mock.MagicMock()
        mock_commit_3.parents = [mock_commit_2]

        mock_repo.return_value.walk.return_value = [
            mock_commit_3,
            mock_commit_2,
            mock_commit_1,
        ]

        mock_iter_diff.return_value = []
        for _ in test_scanner.chunks:
            pass

        mock_repo.return_value.walk.assert_has_calls(
            (
                mock.call(
                    mock_branch_foo.resolve().target, pygit2.GIT_SORT_TOPOLOGICAL
                ),
                mock.call(
                    mock_branch_bar.resolve().target, pygit2.GIT_SORT_TOPOLOGICAL
                ),
            )
        )

    @mock.patch("tartufo.scanner.GitRepoScanner._iter_diff_index")
    @mock.patch("pygit2.Repository")
    def test_all_commits_are_scanned_for_files(
        self,
        mock_repo: mock.MagicMock,
        mock_iter_diff: mock.MagicMock,
    ):
        mock_repo.return_value.branches = {"foo": mock.MagicMock()}
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        mock_commit_1 = mock.MagicMock(name="commit1")
        mock_commit_1.parents = None
        mock_commit_2 = mock.MagicMock(name="commit2")
        mock_commit_2.parents = [mock_commit_1]
        mock_commit_3 = mock.MagicMock(name="commit3")
        mock_commit_3.parents = [mock_commit_2]
        mock_repo.return_value.walk.return_value = [
            mock_commit_3,
            mock_commit_2,
            mock_commit_1,
        ]
        mock_iter_diff.return_value = []
        for _ in test_scanner.chunks:
            pass
        mock_repo.return_value.diff.assert_has_calls(
            (
                mock.call(mock_commit_2, mock_commit_3),
                mock.call(mock_commit_1, mock_commit_2),
            )
        )
        mock_iter_diff.assert_has_calls(
            (
                mock.call(mock_repo.return_value.diff(mock_commit_3, mock_commit_2)),
                mock.call(mock_repo.return_value.diff(mock_commit_2, mock_commit_1)),
                mock.call(mock_repo.return_value.revparse_single().tree.diff_to_tree()),
            )
        )

    @mock.patch("tartufo.scanner.GitRepoScanner._iter_diff_index")
    @mock.patch("tartufo.util.extract_commit_metadata")
    @mock.patch("pygit2.Repository")
    def test_all_files_are_yielded_as_chunks(
        self,
        mock_repo: mock.MagicMock,
        mock_extract: mock.MagicMock,
        mock_iter_diff: mock.MagicMock,
    ):
        mock_repo.return_value.branches = {"foo": mock.MagicMock()}
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        mock_commit_1 = mock.MagicMock()
        mock_commit_1.parents = None
        mock_commit_2 = mock.MagicMock()
        mock_commit_2.parents = [mock_commit_1]
        mock_repo.return_value.walk.return_value = [
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
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        diffs = list(test_scanner._iter_diff_index([mock_diff]))
        self.assertEqual(diffs, [])

    @mock.patch("pygit2.Repository", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.ScannerBase.should_scan")
    def test_excluded_files_are_not_scanned(self, mock_should: mock.MagicMock):
        mock_should.return_value = False
        mock_diff = mock.MagicMock()
        mock_diff.delta.is_binary = False
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        diffs = list(test_scanner._iter_diff_index([mock_diff]))
        self.assertEqual(diffs, [])
        mock_should.assert_called_once()

    @mock.patch("pygit2.Repository", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.ScannerBase.should_scan")
    def test_all_files_are_yielded(self, mock_should: mock.MagicMock):
        mock_should.return_value = True
        mock_diff_1 = mock.MagicMock()
        mock_diff_1.delta.is_binary = False
        mock_diff_1.text = (
            "meta_line_1\nmeta_line_2\nmeta_line_3\nmeta_line_4\n+ Ford Prefect"
        )
        mock_diff_1.delta.new_file.path = "/foo"
        mock_diff_2 = mock.MagicMock()
        mock_diff_2.delta.is_binary = False
        mock_diff_2.text = (
            "meta_line_1\nmeta_line_2\nmeta_line_3\nmeta_line_4\n- Marvin"
        )
        mock_diff_2.delta.new_file.path = "/bar"
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        diffs = list(test_scanner._iter_diff_index([mock_diff_1, mock_diff_2]))
        self.assertEqual(
            diffs,
            [
                ("+ Ford Prefect", "/foo"),
                ("- Marvin", "/bar"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
