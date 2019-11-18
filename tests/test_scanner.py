import json
import re
import sys
import unittest
from collections import namedtuple

import six
from tartufo import scanner

try:
    from unittest import mock
except ImportError:
    import mock  # type: ignore


class EntropyTests(unittest.TestCase):
    def test_shannon(self):
        random_string_b64 = (
            "ZWVTjPQSdhwRgl204Hc51YCsritMIzn8B=/p9UyeX7xu6KkAGqfm3FJ+oObLDNEva"
        )
        random_string_hex = "b3A0a1FDfe86dcCE945B72"
        self.assertGreater(
            scanner.shannon_entropy(random_string_b64, scanner.BASE64_CHARS), 4.5
        )
        self.assertGreater(
            scanner.shannon_entropy(random_string_hex, scanner.HEX_CHARS), 3
        )


class ScannerTests(unittest.TestCase):
    @mock.patch("tartufo.scanner.hashlib", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.tempfile", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.git.Repo")
    @mock.patch("tartufo.scanner.util.clone_git_repo")
    @mock.patch("tartufo.scanner.util.shutil.rmtree")
    def test_find_strings_works_against_already_cloned_repo(
        self, mock_rmtree, mock_clone, mock_repo
    ):
        scanner.find_strings("find_repo", repo_path="/test/path")
        mock_repo.assert_called_once_with("/test/path")
        mock_rmtree.assert_not_called()
        mock_clone.assert_not_called()

    @mock.patch("tartufo.scanner.util.clone_git_repo", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.util.shutil.rmtree", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.tempfile", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.git.Repo")
    def test_find_strings_checks_out_branch_when_specified(self, mock_repo):
        scanner.find_strings("test_repo", branch="testbranch")
        mock_repo.return_value.remotes.origin.fetch.assert_called_once_with(
            "testbranch"
        )

    @mock.patch("tartufo.scanner.tempfile", new=mock.MagicMock())
    @mock.patch("tartufo.scanner.git.Repo")
    @mock.patch("tartufo.scanner.diff_worker")
    def test_all_commits_are_passed_to_diff_worker(self, mock_worker, mock_repo):
        # Expose a "master" branch for our "repo"
        branches = mock_repo.return_value.remotes.origin.fetch
        master_branch = mock.MagicMock(name="master")
        branches.side_effect = [[master_branch]]
        # Expose 3 commits for our "repo"
        commit_1 = mock.MagicMock(name="third commit")
        commit_2 = mock.MagicMock(name="second commit")
        commit_3 = mock.MagicMock(name="first commit")
        mock_repo.return_value.iter_commits.return_value = [
            commit_1,
            commit_2,
            commit_3,
        ]

        scanner.find_strings(
            "git://fake/repo.git",
            repo_path="/fake/repo",
            print_json=True,
            suppress_output=False,
        )

        call_1 = mock.call(
            commit_1.diff.return_value,
            None,
            True,
            False,
            True,
            False,
            None,
            None,
            commit_1,
            master_branch.name,
        )
        call_2 = mock.call(
            commit_2.diff.return_value,
            None,
            True,
            False,
            True,
            False,
            None,
            None,
            commit_2,
            master_branch.name,
        )
        call_3 = mock.call(
            commit_3.diff.return_value,
            None,
            True,
            False,
            True,
            False,
            None,
            None,
            commit_3,
            master_branch.name,
        )
        mock_worker.assert_has_calls((call_1, call_2, call_3), any_order=True)

    def test_unicode_expection(self):
        """FIXME: What is this test actually testing?

        How can we test the same thing without cloning an external repo?
        """
        try:
            scanner.find_strings("https://github.com/dxa4481/tst.git")
        except UnicodeEncodeError:
            self.fail("Unicode print error")

    def test_return_correct_commit_hash(self):
        """FIXME: Split this test out into multiple smaller tests w/o real clone

        Necessary:
            * Make sure all commits are checked (done)
            * Make sure all branches are checked
            * Make sure `diff_worker` flags bad diffs
            * Make sure all bad diffs are returned
        """
        # Start at commit d15627104d07846ac2914a976e8e347a663bbd9b, which
        # is immediately followed by a secret inserting commit:
        # https://github.com/dxa4481/truffleHog/commit/9ed54617547cfca783e0f81f8dc5c927e3d1e345
        since_commit = "d15627104d07846ac2914a976e8e347a663bbd9b"
        commit_w_secret = "9ed54617547cfca783e0f81f8dc5c927e3d1e345"
        xcheck_commit_w_scrt_comment = "OH no a secret"

        tmp_stdout = six.StringIO()
        bak_stdout = sys.stdout

        # Redirect STDOUT, run scan and re-establish STDOUT
        sys.stdout = tmp_stdout
        try:
            scanner.find_strings(
                "https://github.com/godaddy/tartufo.git",
                since_commit=since_commit,
                print_json=True,
                suppress_output=False,
            )
        finally:
            sys.stdout = bak_stdout

        json_result_list = tmp_stdout.getvalue().split("\n")
        results = [json.loads(r) for r in json_result_list if bool(r.strip())]
        filtered_results = [
            result for result in results if result["commit_hash"] == commit_w_secret
        ]
        self.assertEqual(1, len(filtered_results))
        self.assertEqual(commit_w_secret, filtered_results[0]["commit_hash"])
        # Additionally, we cross-validate the commit comment matches the expected comment
        self.assertEqual(
            xcheck_commit_w_scrt_comment, filtered_results[0]["commit"].strip()
        )

    def test_path_included(self):
        """FIXME: This has WAAAAAAY too many asserts.

        This needs to be split up into many smaller tests.
        It also needs to be made to work without a real clone.
        """
        blob = namedtuple("Blob", ("a_path", "b_path"))
        blobs = {
            "file-root-dir": blob("file", "file"),
            "file-sub-dir": blob("sub-dir/file", "sub-dir/file"),
            "new-file-root-dir": blob(None, "new-file"),
            "new-file-sub-dir": blob(None, "sub-dir/new-file"),
            "deleted-file-root-dir": blob("deleted-file", None),
            "deleted-file-sub-dir": blob("sub-dir/deleted-file", None),
            "renamed-file-root-dir": blob("file", "renamed-file"),
            "renamed-file-sub-dir": blob("sub-dir/file", "sub-dir/renamed-file"),
            "moved-file-root-dir-to-sub-dir": blob("moved-file", "sub-dir/moved-file"),
            "moved-file-sub-dir-to-root-dir": blob("sub-dir/moved-file", "moved-file"),
            "moved-file-sub-dir-to-sub-dir": blob(
                "sub-dir/moved-file", "moved/moved-file"
            ),
        }
        src_paths = set(
            blob.a_path for blob in blobs.values() if blob.a_path is not None
        )
        dest_paths = set(
            blob.b_path for blob in blobs.values() if blob.b_path is not None
        )
        all_paths = src_paths.union(dest_paths)
        all_paths_patterns = [re.compile(re.escape(p)) for p in all_paths]
        overlap_patterns = [
            re.compile(r"sub-dir/.*"),
            re.compile(r"moved/"),
            re.compile(r"[^/]*file$"),
        ]
        sub_dirs_patterns = [re.compile(r".+/.+")]
        deleted_paths_patterns = [re.compile(r"(.*/)?deleted-file$")]
        for name, blob in blobs.items():
            self.assertTrue(
                scanner.path_included(blob),
                "{} should be included by default".format(blob),
            )
            self.assertTrue(
                scanner.path_included(blob, include_patterns=all_paths_patterns),
                "{} should be included with include_patterns: {}".format(
                    blob, all_paths_patterns
                ),
            )
            self.assertFalse(
                scanner.path_included(blob, exclude_patterns=all_paths_patterns),
                "{} should be excluded with exclude_patterns: {}".format(
                    blob, all_paths_patterns
                ),
            )
            # pylint: disable=W1308
            self.assertFalse(
                scanner.path_included(
                    blob,
                    include_patterns=all_paths_patterns,
                    exclude_patterns=all_paths_patterns,
                ),
                "{} should be excluded with overlapping patterns: \n\tinclude: {}\n\texclude: {}".format(
                    blob, all_paths_patterns, all_paths_patterns
                ),
            )
            self.assertFalse(
                scanner.path_included(
                    blob,
                    include_patterns=overlap_patterns,
                    exclude_patterns=all_paths_patterns,
                ),
                "{} should be excluded with overlapping patterns: \n\tinclude: {}\n\texclude: {}".format(
                    blob, overlap_patterns, all_paths_patterns
                ),
            )
            self.assertFalse(
                scanner.path_included(
                    blob,
                    include_patterns=all_paths_patterns,
                    exclude_patterns=overlap_patterns,
                ),
                "{} should be excluded with overlapping patterns: \n\tinclude: {}\n\texclude: {}".format(
                    blob, all_paths_patterns, overlap_patterns
                ),
            )
            path = blob.b_path if blob.b_path else blob.a_path
            if "/" in path:
                self.assertTrue(
                    scanner.path_included(blob, include_patterns=sub_dirs_patterns),
                    "{}: inclusion should include sub directory paths: {}".format(
                        blob, sub_dirs_patterns
                    ),
                )
                self.assertFalse(
                    scanner.path_included(blob, exclude_patterns=sub_dirs_patterns),
                    "{}: exclusion should exclude sub directory paths: {}".format(
                        blob, sub_dirs_patterns
                    ),
                )
            else:
                self.assertFalse(
                    scanner.path_included(blob, include_patterns=sub_dirs_patterns),
                    "{}: inclusion should exclude root directory paths: {}".format(
                        blob, sub_dirs_patterns
                    ),
                )
                self.assertTrue(
                    scanner.path_included(blob, exclude_patterns=sub_dirs_patterns),
                    "{}: exclusion should include root directory paths: {}".format(
                        blob, sub_dirs_patterns
                    ),
                )
            if name.startswith("deleted-file-"):
                self.assertTrue(
                    scanner.path_included(
                        blob, include_patterns=deleted_paths_patterns
                    ),
                    "{}: inclusion should match deleted paths: {}".format(
                        blob, deleted_paths_patterns
                    ),
                )
                self.assertFalse(
                    scanner.path_included(
                        blob, exclude_patterns=deleted_paths_patterns
                    ),
                    "{}: exclusion should match deleted paths: {}".format(
                        blob, deleted_paths_patterns
                    ),
                )


if __name__ == "__main__":
    unittest.main()
