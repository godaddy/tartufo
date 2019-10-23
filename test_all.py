# pylint: disable=C0330

import io
import json
import os
import re
import sys
from collections import namedtuple

import unittest
try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch  # type: ignore

from truffleHogRegexes.regexChecks import regexes as default_regexes
from tartufo import cli, config, scanner, util


class TestStringMethods(unittest.TestCase):  # pylint: disable=too-many-public-methods

    def test_main_exits_gracefully_with_empty_argv(self):
        return_val = cli.main([])
        self.assertEqual(return_val, 1)

    def test_parse_args_git_rules_repo(self):
        argv = ["--git-rules-repo", "git@github.test:test-owner/tartufo-test.git"]
        expected_git_rules_repo = "git@github.test:test-owner/tartufo-test.git"
        args = cli.parse_args(argv)
        self.assertEqual(expected_git_rules_repo, args.git_rules_repo)

    def test_parse_args_git_rules_not_specified(self):
        argv = []
        args = cli.parse_args(argv)
        self.assertEqual(0, len(args.git_rules_filenames), "args.git_rules_filenames should be empty")

    def test_parse_args_git_rules(self):
        argv = ["--git-rules", "file1", "file2"]
        expected_rules_filenames = ("file1", "file2")
        args = cli.parse_args(argv)
        self.assertCountEqual(expected_rules_filenames, args.git_rules_filenames,
                              "args.git_rules_filenames should be {}, is actually {}".
                              format(expected_rules_filenames, args.rules_filenames))

    def test_parse_args_git_rules_multiple_times(self):
        argv = ["--git-rules", "file1", "--git-rules", "file2"]
        expected_rules_filenames = ("file1", "file2")
        args = cli.parse_args(argv)
        self.assertCountEqual(expected_rules_filenames, args.git_rules_filenames,
                              "args.git_rules_filenames should be {}, is actually {}".
                              format(expected_rules_filenames, args.rules_filenames))

    def test_parse_args_rules_not_specified(self):
        argv = []
        args = cli.parse_args(argv)
        self.assertEqual(0, len(args.rules_filenames), "args.rules_filenames should be empty")

    def test_parse_args_rules(self):
        argv = ["--rules", "file1", "file2"]
        expected_rules_filenames = ("file1", "file2")
        args = cli.parse_args(argv)
        self.assertCountEqual(expected_rules_filenames, args.rules_filenames,
                              "args.rules_filenames should be {}, is actually {}".
                              format(expected_rules_filenames, args.rules_filenames))

    def test_parse_args_rules_multiple_times(self):
        argv = ["--rules", "file1", "--rules", "file2"]
        expected_rules_filenames = ("file1", "file2")
        args = cli.parse_args(argv)
        self.assertCountEqual(expected_rules_filenames, args.rules_filenames,
                              "args.rules_filenames should be {}, is actually {}".
                              format(expected_rules_filenames, args.rules_filenames))

    def test_parse_args_rules_default_regexes_set_to_false(self):
        argv = ["--default-regexes", "f"]
        args = cli.parse_args(argv)
        self.assertFalse(args.do_default_regexes, "args.do_default_regexes should be False, is actually {}".
                         format(args.do_default_regexes))

    def test_parse_args_rules_default_regexes_set_to_true(self):
        argv = ["--default-regexes", "t"]
        args = cli.parse_args(argv)
        self.assertTrue(args.do_default_regexes, "args.do_default_regexes should be True, is actually {}".
                        format(args.do_default_regexes))

    def test_parse_args_rules_default_regexes_specified_with_no_value(self):
        argv = ["--default-regexes", "--regex"]
        args = cli.parse_args(argv)
        self.assertTrue(args.do_default_regexes, "args.do_default_regexes should be True, is actually {}".
                        format(args.do_default_regexes))

    def test_parse_args_rules_default_regexes_unset(self):
        argv = []
        args = cli.parse_args(argv)
        self.assertTrue(args.do_default_regexes, "args.do_default_regexes should be True, is actually {}".
                        format(args.do_default_regexes))

    def test_configure_regexes_from_args_rules_files_without_defaults(self):
        rules_filenames = ["testRules.json"]
        expected_regexes = {"RSA private key 2": re.compile("-----BEGIN EC PRIVATE KEY-----")}

        Args = namedtuple("Args", ("do_regex", "git_rules_repo", "git_rules_filenames", "rules_filenames",
                                   "do_default_regexes"))
        args = Args(True, None, None, rules_filenames, False)
        actual_regexes = config.configure_regexes_from_args(args, default_regexes)

        self.assertEqual(len(expected_regexes), len(actual_regexes),
                         "The regexes dictionary should have the same length as the test rules " +
                         "(expected: {}, actual: {})".format(len(expected_regexes), len(actual_regexes)))
        for expected_key in expected_regexes:
            self.assertIn(expected_key, actual_regexes,
                          "The regexes dictionary should have the key '{}' from the rules file".format(expected_key))
            expected_regex = expected_regexes[expected_key]
            actual_regex = actual_regexes[expected_key]
            self.assertEqual(expected_regex.pattern, actual_regex.pattern,
                             "The regexes dictionary should have the compiled regex for '{}' in key '{}'".
                             format(expected_regex.pattern, expected_key))

    def test_configure_regexes_from_args_rules_files_with_defaults(self):
        rules_filenames = ["testRules.json"]
        expected_regexes = dict(default_regexes)
        expected_regexes["RSA private key 2"] = re.compile("-----BEGIN EC PRIVATE KEY-----")

        Args = namedtuple("Args", ("do_regex", "git_rules_repo", "git_rules_filenames", "rules_filenames",
                                   "do_default_regexes"))
        args = Args(True, None, None, rules_filenames, True)
        actual_regexes = config.configure_regexes_from_args(args, default_regexes)

        self.assertEqual(len(expected_regexes), len(actual_regexes),
                         "The regexes dictionary should have the same length as the test rules " +
                         "(expected: {}, actual: {})".format(len(expected_regexes), len(actual_regexes)))
        for expected_key in expected_regexes:
            self.assertIn(expected_key, actual_regexes,
                          "The regexes dictionary should have the key '{}' from the rules file".format(expected_key))
            expected_regex = expected_regexes[expected_key]
            actual_regex = actual_regexes[expected_key]
            self.assertEqual(expected_regex.pattern, actual_regex.pattern,
                             "The regexes dictionary should have the compiled regex for '{}' in key '{}'".
                             format(expected_regex.pattern, expected_key))

    def test_configure_regexes_from_args_no_do_regex(self):
        rules_filenames = ["testRules.json"]

        Args = namedtuple("Args", ("do_regex", "git_rules_repo", "git_rules_filenames", "rules_filenames",
                                   "do_default_regexes"))
        args = Args(False, None, None, rules_filenames, True)
        actual_regexes = config.configure_regexes_from_args(args, default_regexes)

        self.assertDictEqual({}, actual_regexes, "The regexes dictionary should be empty when do_regex is False")

    def test_configure_regexes_from_args_no_rules(self):
        rules_filenames = []
        expected_regexes = dict(default_regexes)

        Args = namedtuple("Args", ("do_regex", "git_rules_repo", "git_rules_filenames", "rules_filenames",
                                   "do_default_regexes"))
        args = Args(True, None, None, rules_filenames, False)
        actual_regexes = config.configure_regexes_from_args(args, default_regexes)

        self.assertDictEqual(expected_regexes, actual_regexes,
                             "The regexes dictionary should not have been changed when no rules files are specified")

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

    def test_cloning(self):
        project_path = util.clone_git_repo(
            "https://github.com/godaddy/tartufo.git"
        )
        license_file = os.path.join(project_path, "LICENSE")
        self.assertTrue(os.path.isfile(license_file))

    def test_unicode_expection(self):
        try:
            scanner.find_strings("https://github.com/dxa4481/tst.git")
        except UnicodeEncodeError:
            self.fail("Unicode print error")

    def test_return_correct_commit_hash(self):
        # Start at commit d15627104d07846ac2914a976e8e347a663bbd9b, which
        # is immediately followed by a secret inserting commit:
        # https://github.com/dxa4481/truffleHog/commit/9ed54617547cfca783e0f81f8dc5c927e3d1e345
        since_commit = "d15627104d07846ac2914a976e8e347a663bbd9b"
        commit_w_secret = "9ed54617547cfca783e0f81f8dc5c927e3d1e345"
        xcheck_commit_w_scrt_comment = "OH no a secret"

        if sys.version_info >= (3,):
            tmp_stdout = io.StringIO()
        else:
            tmp_stdout = io.BytesIO()
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

    # noinspection PyUnusedLocal
    @patch("tartufo.scanner.util.clone_git_repo")
    @patch("tartufo.scanner.Repo")
    @patch("shutil.rmtree")
    def test_branch(
        self, rmtree_mock, repo_const_mock, clone_git_repo
    ):  # pylint: disable=unused-argument
        repo = MagicMock()
        repo_const_mock.return_value = repo
        scanner.find_strings("test_repo", branch="testbranch")
        self.assertIsNone(
            repo.remotes.origin.fetch.assert_called_once_with("testbranch")
        )

    def test_path_included(self):
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

    # noinspection PyUnusedLocal
    @patch("tartufo.scanner.util.clone_git_repo")
    @patch("tartufo.scanner.Repo")
    @patch("shutil.rmtree")
    def test_repo_path(
        self, rmtree_mock, repo_const_mock, clone_git_repo
    ):  # pylint: disable=unused-argument
        scanner.find_strings("test_repo", repo_path="test/path/")
        self.assertIsNone(rmtree_mock.assert_not_called())
        self.assertIsNone(clone_git_repo.assert_not_called())

    # Between Python 2 and 3, the assertItemsEqual method was renamed to assertCountEqual, and the old method name
    # was removed. In order to maintain cross-version compatibility, we need to map assertCountEqual to
    # assertItemsEqual for pre-Python 3.
    if sys.version_info[0] < 3:
        def assertCountEqual(self, first, second, msg=None):
            return self.assertItemsEqual(first, second, msg=msg)  # pylint: disable=no-member


if __name__ == "__main__":
    unittest.main()
