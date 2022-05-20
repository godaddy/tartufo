import unittest
from pathlib import Path
from unittest import mock
from click.testing import CliRunner
from tartufo import cli, types
from tests import helpers
from hashlib import sha256
from pygit2 import Repository
from subprocess import call
from os import remove

class ScanLocalRepoTests(unittest.TestCase):
    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    def test_scan_exits_gracefully_on_scan_exception(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.side_effect = types.ScanException("Scan failed!")
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["scan-local-repo", "."])
        self.assertGreater(result.exit_code, 0)
        self.assertEqual(result.output, "Scan failed!\n")

    @unittest.skipIf(
        helpers.BROKEN_USER_PATHS, "Skipping due to truncated Windows usernames"
    )
    def test_scan_exits_gracefully_when_target_is_not_git_repo(self):
        runner = CliRunner()
        with runner.isolated_filesystem() as run_path:
            result = runner.invoke(cli.main, ["scan-local-repo", "."])
            self.assertEqual(
                str(result.exception),
                f"Repository not found at {Path(run_path).resolve()}",
            )

    def test_new_file_shows_up(self):
        runner = CliRunner()
        # Add file with high entropy
        secret_key = sha256(b"hello world")
        f = open("secret.key", "a")
        f.write(secret_key.hexdigest())
        f.close()
        repo = Repository(".")

        # Check that tartufo picks up on newly added files
        repo.index.add("tests/data/config/secret.key")
        repo.index.write() # This actually writes the index to disk. Without it, the tracked file is not actually staged.
        result_1 = runner.invoke(cli.main, ["--entropy-sensitivity", "1", "pre-commit"])
        self.assertNotEqual(result_1.exit_code, 0)

        # Check that tartufo does not flag non-added new files
        repo.index.remove("tests/data/config/secret.key")
        repo.index.write() # This actually writes the index to disk. Without it, secret.key will not return to being untracked.
        result_2 = runner.invoke(cli.main, ["--entropy-sensitivity", "1", "pre-commit"])
        self.assertEqual(result_2.exit_code, 0)

        # Cleanup
        remove("secret.key")
