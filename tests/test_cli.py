import unittest

from tartufo import cli


class CLITests(unittest.TestCase):

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
        expected_rules_filenames = ["file1", "file2"]
        args = cli.parse_args(argv)
        self.assertEqual(
            expected_rules_filenames, args.git_rules_filenames,
            "args.git_rules_filenames should be {}, is actually {}".format(
                expected_rules_filenames, args.rules_filenames
            )
        )

    def test_parse_args_git_rules_multiple_times(self):
        argv = ["--git-rules", "file1", "--git-rules", "file2"]
        expected_rules_filenames = ["file1", "file2"]
        args = cli.parse_args(argv)
        self.assertEqual(
            expected_rules_filenames, args.git_rules_filenames,
            "args.git_rules_filenames should be {}, is actually {}".format(
                expected_rules_filenames, args.rules_filenames
            )
        )

    def test_parse_args_rules_not_specified(self):
        argv = []
        args = cli.parse_args(argv)
        self.assertEqual(0, len(args.rules_filenames), "args.rules_filenames should be empty")

    def test_parse_args_rules(self):
        argv = ["--rules", "file1", "file2"]
        expected_rules_filenames = ["file1", "file2"]
        args = cli.parse_args(argv)
        self.assertEqual(
            expected_rules_filenames, args.rules_filenames,
            "args.rules_filenames should be {}, is actually {}".format(
                expected_rules_filenames, args.rules_filenames
            )
        )

    def test_parse_args_rules_multiple_times(self):
        argv = ["--rules", "file1", "--rules", "file2"]
        expected_rules_filenames = ["file1", "file2"]
        args = cli.parse_args(argv)
        self.assertEqual(
            expected_rules_filenames, args.rules_filenames,
            "args.rules_filenames should be {}, is actually {}".format(
                expected_rules_filenames, args.rules_filenames
            )
        )

    def test_parse_args_rules_default_regexes_set_to_false(self):
        argv = ["--default-regexes", "f"]
        args = cli.parse_args(argv)
        self.assertFalse(
            args.do_default_regexes,
            "args.do_default_regexes should be False, is actually {}".format(args.do_default_regexes)
        )

    def test_parse_args_rules_default_regexes_set_to_true(self):
        argv = ["--default-regexes", "t"]
        args = cli.parse_args(argv)
        self.assertTrue(
            args.do_default_regexes,
            "args.do_default_regexes should be True, is actually {}".format(args.do_default_regexes)
        )

    def test_parse_args_rules_default_regexes_specified_with_no_value(self):
        argv = ["--default-regexes", "--regex"]
        args = cli.parse_args(argv)
        self.assertTrue(
            args.do_default_regexes,
            "args.do_default_regexes should be True, is actually {}".format(args.do_default_regexes)
        )

    def test_parse_args_rules_default_regexes_unset(self):
        argv = []
        args = cli.parse_args(argv)
        self.assertTrue(
            args.do_default_regexes,
            "args.do_default_regexes should be True, is actually {}".format(args.do_default_regexes)
        )


if __name__ == "__main__":
    unittest.main()
