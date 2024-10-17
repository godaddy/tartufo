# pylint: disable=protected-access
import pathlib
import re
import unittest
from unittest import mock

import pygit2

from tartufo import scanner, types
from tartufo.types import GlobalOptions, GitOptions, TartufoException, ConfigException
from tests.helpers import generate_options


class ScannerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.global_options = generate_options(GlobalOptions, exclude_signatures=())
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
        mock_repo.return_value.is_bare = False
        test_scanner.load_repo("../tartufo")
        mock_repo.assert_has_calls(
            [
                mock.call("."),
                mock.call().is_bare.__bool__(),  # pylint: disable=unnecessary-dunder-call
                mock.call("../tartufo"),
            ]
        )

    @mock.patch("pygit2.Repository")
    @mock.patch("tartufo.scanner.GitRepoScanner.filter_submodules")
    def test_load_repo_filters_submodules_when_specified(
        self, mock_filter: mock.MagicMock, mock_repo: mock.MagicMock
    ):
        self.git_options.include_submodules = False
        mock_repo.return_value.is_bare = False
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
        self.global_options.target_config = True
        mock_load.return_value = (
            self.data_dir / "pyproject.toml",
            {
                "include_path_patterns": (
                    {"path-pattern": "tartufo/", "reason": "Inclusion reason"},
                    {"path-pattern": "scripts/", "reason": "Inclusion reason"},
                )
            },
        )
        self.global_options.include_path_patterns = (
            {"path-pattern": "foo/", "reason": "Inclusion reason"},
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
        self.global_options.target_config = True
        mock_load.return_value = (
            self.data_dir / "pyproject.toml",
            {
                "exclude_path_patterns": (
                    {"path-pattern": "tests/", "reason": "Exclusion reason"},
                    {"path-pattern": r"\.venv/", "reason": "Exclusion reason"},
                    {"path-pattern": r".*\.egg-info/", "reason": "Exclusion reason"},
                )
            },
        )
        self.global_options.exclude_path_patterns = (
            {"path-pattern": "bar/", "reason": "Exclusion reason"},
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
        self.global_options.target_config = True
        mock_load.return_value = (
            self.data_dir / "pyproject.toml",
            {
                "exclude_signatures": [
                    {"signature": "foo", "reason": "Reason to exclude signature"}
                ]
            },
        )
        self.global_options.exclude_signatures = (
            {"signature": "bar", "reason": "Reason to exclude signature"},
        )
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, str(self.data_dir)
        )
        test_scanner.load_repo("../tartufo")
        self.assertCountEqual(test_scanner.excluded_signatures, ["bar", "foo"])

    @mock.patch("pygit2.Repository", new=mock.MagicMock())
    @mock.patch("tartufo.config.load_config_from_path")
    def test_pyproject_signatures_get_excluded(self, mock_load: mock.MagicMock):
        self.global_options.target_config = False
        mock_load.return_value = (
            self.data_dir / "pyproject.toml",
            {
                "exclude_signatures": [
                    {"signature": "foo", "reason": "Reason to exclude signature"}
                ]
            },
        )
        self.global_options.exclude_signatures = (
            {"signature": "bar", "reason": "Reason to exclude signature"},
        )
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, str(self.data_dir)
        )
        test_scanner.load_repo("../tartufo")
        self.assertCountEqual(test_scanner.excluded_signatures, ["bar"])


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
        mock_repo.return_value.is_bare = False
        mock_repo.return_value.listall_submodules.return_value = [
            "foo",
            "bar",
        ]
        mock_repo.return_value.lookup_submodule.side_effect = lambda x: {
            "foo": FakeSubmodule("foo"),
            "bar": FakeSubmodule("bar"),
        }[x]
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
        mock_repo.return_value.is_bare = False
        mock_repo.return_value.listall_submodules.return_value.__iter__.side_effect = (
            AttributeError
        )
        with self.assertRaisesRegex(
            TartufoException, "There was an error while parsing submodules"
        ):
            scanner.GitRepoScanner(self.global_options, self.git_options, ".")

    @mock.patch("pygit2.Repository")
    @mock.patch("tartufo.scanner.GitRepoScanner.filter_submodules")
    def test_filter_submodules_skipped_for_mirror_clones(
        self, mock_filter: mock.MagicMock, mock_repo: mock.MagicMock
    ):
        self.git_options.include_submodules = True
        mock_repo.return_value.is_bare = True

        scanner.GitRepoScanner(self.global_options, self.git_options, ".")
        mock_filter.assert_not_called()


class ChunkGeneratorTests(ScannerTestCase):
    def setUp(self) -> None:
        self.diff_patcher = mock.patch("tartufo.scanner.GitScanner._iter_diff_index")
        self.repo_patcher = mock.patch("pygit2.Repository")
        self.shallow_patcher = mock.patch("tartufo.scanner.util.is_shallow_clone")

        self.mock_iter_diff = self.diff_patcher.start()
        self.mock_repo = self.repo_patcher.start()
        self.mock_shallow = self.shallow_patcher.start()

        self.mock_shallow.return_value = False

        self.addCleanup(self.diff_patcher.stop)
        self.addCleanup(self.repo_patcher.stop)
        self.addCleanup(self.shallow_patcher.stop)
        return super().setUp()

    def test_single_branch_is_loaded_if_specified(self):
        self.git_options.branch = "foo"
        mock_branch_foo = mock.MagicMock()
        mock_branch_bar = mock.MagicMock()
        self.mock_repo.return_value.listall_branches.return_value = ["foo", "bar"]
        self.mock_repo.return_value.branches = {
            "foo": mock_branch_foo,
            "bar": mock_branch_bar,
        }
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )

        self.mock_iter_diff.return_value = []
        for _ in test_scanner.chunks:
            pass
        self.mock_repo.return_value.walk.assert_called_once_with(
            mock_branch_foo.resolve().target, pygit2.GIT_SORT_TOPOLOGICAL
        )

    def test_runs_scans_with_progressbar_enabled(self):
        mock_branch_foo = mock.MagicMock()
        mock_branch_bar = mock.MagicMock()
        self.mock_repo.return_value.listall_branches.return_value = ["foo", "bar"]
        self.mock_repo.return_value.branches = {
            "foo": mock_branch_foo,
            "bar": mock_branch_bar,
        }
        self.git_options.progress = True
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )

        mock_commit_1 = mock.MagicMock()
        mock_commit_1.parents = None
        mock_commit_2 = mock.MagicMock()
        mock_commit_2.parents = [mock_commit_1]
        mock_commit_3 = mock.MagicMock()
        mock_commit_3.parents = [mock_commit_2]

        self.mock_repo.return_value.walk.return_value = [
            mock_commit_3,
            mock_commit_2,
            mock_commit_1,
        ]

        self.mock_iter_diff.return_value = []
        for _ in test_scanner.chunks:
            pass

        self.mock_repo.return_value.walk.assert_has_calls(
            (
                mock.call(
                    mock_branch_foo.resolve().target, pygit2.GIT_SORT_TOPOLOGICAL
                ),
                mock.call(
                    mock_branch_bar.resolve().target, pygit2.GIT_SORT_TOPOLOGICAL
                ),
            )
        )

        self.mock_iter_diff.assert_called()

    def test_all_branches_are_scanned_for_commits(self):
        mock_branch_foo = mock.MagicMock()
        mock_branch_bar = mock.MagicMock()
        self.mock_repo.return_value.listall_branches.return_value = ["foo", "bar"]
        self.mock_repo.return_value.branches = {
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

        self.mock_repo.return_value.walk.return_value = [
            mock_commit_3,
            mock_commit_2,
            mock_commit_1,
        ]

        self.mock_iter_diff.return_value = []
        for _ in test_scanner.chunks:
            pass

        self.mock_repo.return_value.walk.assert_has_calls(
            (
                mock.call(
                    mock_branch_foo.resolve().target, pygit2.GIT_SORT_TOPOLOGICAL
                ),
                mock.call(
                    mock_branch_bar.resolve().target, pygit2.GIT_SORT_TOPOLOGICAL
                ),
            )
        )

        self.mock_iter_diff.assert_called()

    def test_all_commits_are_scanned_for_files(self):
        self.mock_repo.return_value.branches = {"foo": mock.MagicMock()}
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        mock_commit_1 = mock.MagicMock(name="commit1")
        mock_commit_1.parents = None
        mock_commit_2 = mock.MagicMock(name="commit2")
        mock_commit_2.parents = [mock_commit_1]
        mock_commit_3 = mock.MagicMock(name="commit3")
        mock_commit_3.parents = [mock_commit_2]
        self.mock_repo.return_value.walk.return_value = [
            mock_commit_3,
            mock_commit_2,
            mock_commit_1,
        ]
        self.mock_iter_diff.return_value = []
        for _ in test_scanner.chunks:
            pass
        self.mock_repo.return_value.diff.assert_has_calls(
            (
                mock.call(mock_commit_2, mock_commit_3),
                mock.call().find_similar(),
                mock.call(mock_commit_1, mock_commit_2),
                mock.call().find_similar(),
            )
        )
        self.mock_iter_diff.assert_has_calls(
            (
                mock.call(
                    self.mock_repo.return_value.diff(mock_commit_3, mock_commit_2),
                ),
                mock.call(
                    self.mock_repo.return_value.diff(mock_commit_2, mock_commit_1),
                ),
                mock.call(
                    self.mock_repo.return_value.revparse_single().tree.diff_to_tree(),
                ),
            )
        )

    @mock.patch("tartufo.util.extract_commit_metadata")
    def test_all_files_are_yielded_as_chunks(
        self,
        mock_extract: mock.MagicMock,
    ):
        self.mock_repo.return_value.branches = {"foo": mock.MagicMock()}
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        mock_commit_1 = mock.MagicMock()
        mock_commit_1.parents = None
        mock_commit_2 = mock.MagicMock()
        mock_commit_2.parents = [mock_commit_1]
        self.mock_repo.return_value.walk.return_value = [
            mock_commit_2,
            mock_commit_1,
        ]
        self.mock_iter_diff.return_value = [("foo", "bar.py"), ("baz", "blah.py")]
        chunks = list(test_scanner.chunks)

        # These get duplicated in this test, because `_iter_diff` is called
        # both in the normal branch/commit iteration, and then once more afterward
        # to capture the first commit on the branch
        self.assertEqual(
            chunks,
            [
                types.Chunk("foo", "bar.py", mock_extract.return_value, True),
                types.Chunk("baz", "blah.py", mock_extract.return_value, True),
                types.Chunk("foo", "bar.py", mock_extract.return_value, True),
                types.Chunk("baz", "blah.py", mock_extract.return_value, True),
            ],
        )

    def test_error_is_raised_when_specified_branch_is_not_found(self):
        self.git_options.branch = "foo"
        self.mock_repo.return_value.branches = {}

        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        with self.assertRaisesRegex(
            types.BranchNotFoundException, "Branch foo was not found."
        ):
            for _ in test_scanner.chunks:
                pass

    def test_head_is_scanned_when_shallow_clone_is_found(self):
        self.mock_shallow.return_value = True
        self.mock_iter_diff.return_value = []
        self.mock_repo.return_value.head.target = "commit-hash"
        mock_head = mock.MagicMock(spec=pygit2.Commit)
        self.mock_repo.return_value.get.return_value = mock_head

        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )

        for _ in test_scanner.chunks:
            pass

        # This is all the stuff that happens for yielding the "first commit".
        self.mock_repo.return_value.get.assert_called_once_with("commit-hash")
        revparse = self.mock_repo.return_value.revparse_single
        revparse.assert_called_once_with(str(mock_head.id))
        tree = revparse.return_value.tree.diff_to_tree
        tree.assert_called_once_with(swap=True)
        self.mock_iter_diff.assert_called_with(tree.return_value)


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
        diffs = list(test_scanner._iter_diff_index([mock_diff]))  # type: ignore[arg-type]
        self.assertEqual(diffs, [])
        mock_should.assert_called_once()

    @mock.patch("pygit2.Repository", new=mock.MagicMock())
    @mock.patch(
        "tartufo.scanner.GitScanner.header_length",
        mock.MagicMock(side_effect=[52, 52, 0]),
    )
    @mock.patch("tartufo.scanner.ScannerBase.should_scan")
    def test_all_files_are_yielded(self, mock_should: mock.MagicMock):
        mock_should.return_value = True
        mock_diff_1 = mock.MagicMock()
        mock_diff_1.delta.is_binary = False
        mock_diff_1.text = (
            "meta_line_1\nmeta_line_2\nmeta_line_3\n+++ meta_line_4\n+ Ford Prefect"
        )
        mock_diff_1.delta.new_file.path = "/foo"
        mock_diff_2 = mock.MagicMock()
        mock_diff_2.delta.is_binary = False
        mock_diff_2.text = (
            "meta_line_1\nmeta_line_2\nmeta_line_3\n+++ meta_line_4\n- Marvin"
        )
        mock_diff_2.delta.new_file.path = "/bar"
        mock_diff_3 = mock.MagicMock()
        mock_diff_3.delta.is_binary = False
        mock_diff_3.text = (
            "meta_line_1\nsimilarity index 100%\nrename from file1\nrename to file1"
        )
        mock_diff_3.delta.new_file.path = "/bar"
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        diffs = list(test_scanner._iter_diff_index([mock_diff_1, mock_diff_2]))  # type: ignore[arg-type]
        self.assertEqual(
            diffs,
            [
                ("+ Ford Prefect", "/foo"),
                ("- Marvin", "/bar"),
            ],
        )


class HeaderLineCountTests(ScannerTestCase):
    def test_detects_there_are_four_header_lines(self):
        diff = "meta_line_1\nmeta_line_2\nmeta_line_3\n+++ meta_line_4\n+ Ford Prefect"
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        actual_diff_header_length = test_scanner.header_length(diff)
        self.assertEqual(52, actual_diff_header_length)

    def test_detects_there_are_five_header_lines(self):
        diff = "meta_line_1\nmeta_line_2\nmeta_line_3\nmeta_line_4\n+++ meta_line_4\n+ Ford Prefect"
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        actual_diff_header_length = test_scanner.header_length(diff)
        self.assertEqual(64, actual_diff_header_length)

    def test_returns_entire_header_length_when_no_header_match(self):
        diff = "meta_line_1\nmeta_line_2\nmeta_line_3\nmeta_line_4\nmeta_line_4\n+ Ford Prefect"
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        actual_diff_header_length = test_scanner.header_length(diff)
        self.assertEqual(len(diff), actual_diff_header_length)


class ScanFilenameTests(ScannerTestCase):
    @mock.patch("tartufo.scanner.GitScanner.header_length")
    def test_scan_filename_disabled(self, mock_header_length):
        mock_diff = mock.MagicMock()
        mock_diff.delta.is_binary = False
        mock_diff.text = "meta_line_1\nmeta_line_2\nmeta_line_3\nmeta_line_4\nmeta_line_4\n+ Ford Prefect"
        self.global_options.scan_filenames = False
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )

        for _ in test_scanner._iter_diff_index([mock_diff]):
            pass

        mock_header_length.assert_called_once_with(mock_diff.text)

    @mock.patch("tartufo.scanner.GitScanner.header_length")
    def test_scan_filename_enabled(self, mock_header_length):
        mock_diff = mock.MagicMock()
        mock_diff.delta.is_binary = False
        mock_diff.text = "meta_line_1\nmeta_line_2\nmeta_line_3\nmeta_line_4\nmeta_line_4\n+ Ford Prefect"
        self.global_options.scan_filenames = True
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )

        for _ in test_scanner._iter_diff_index([mock_diff]):
            pass

        mock_header_length.assert_not_called()


class ExcludedSignaturesTests(ScannerTestCase):
    def test_new_style_signatures_are_processed(self):
        self.global_options.exclude_signatures = (
            {"signature": "bar/", "reason": "path pattern"},
        )
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        self.assertEqual(test_scanner.excluded_signatures, ("bar/",))

    def test_error_is_raised_when_string_signature_is_used(self):
        self.global_options.exclude_signatures = [
            "foo/",
            {"signature": "bar/", "reason": "path pattern"},
        ]
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        with self.assertRaisesRegex(
            ConfigException, "str signature is illegal in exclude-signatures"
        ):
            self.assertIsNone(test_scanner.excluded_signatures)


class IncludedPathsTests(ScannerTestCase):
    def test_new_style_included_paths_are_processed(self):
        self.global_options.include_path_patterns = (
            {"path-pattern": "bar/", "reason": "path pattern"},
        )
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        self.assertEqual(test_scanner.included_paths, [re.compile("bar/")])

    def test_error_is_raised_when_string_include_path_is_used(self):
        self.global_options.include_path_patterns = [
            "foo/",
            {"path-pattern": "bar/", "reason": "path pattern"},
        ]
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        with self.assertRaisesRegex(
            ConfigException, "str pattern is illegal in include-path-patterns"
        ):
            self.assertIsNone(test_scanner.included_paths)


class ExcludedPathsTests(ScannerTestCase):
    def test_new_style_excluded_paths_are_processed(self):
        self.global_options.exclude_path_patterns = (
            {"path-pattern": "bar/", "reason": "path pattern"},
        )
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        self.assertEqual(test_scanner.excluded_paths, [re.compile("bar/")])

    @mock.patch("tartufo.scanner.GitScanner.filter_submodules", mock.MagicMock())
    def test_error_is_raised_when_string_exclude_path_is_used(self):
        self.global_options.exclude_path_patterns = [
            "foo/",
            {"path-pattern": "bar/", "reason": "path pattern"},
        ]
        test_scanner = scanner.GitRepoScanner(
            self.global_options, self.git_options, "."
        )
        with self.assertRaisesRegex(
            ConfigException, "str pattern is illegal in exclude-path-patterns"
        ):
            self.assertIsNone(test_scanner.excluded_paths)


if __name__ == "__main__":
    unittest.main()
