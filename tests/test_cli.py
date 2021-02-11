import unittest
from collections import namedtuple
from pathlib import Path
from unittest import mock

from click.testing import CliRunner
from tartufo import cli, scanner, types

from tests import helpers
from tests.commands import foo as command_foo


FakeFile = namedtuple("FakeFile", ["name"])


class GetCommandsTests(unittest.TestCase):
    _original_plugin_dir: Path
    _original_plugin_module: str

    @classmethod
    def setUpClass(cls) -> None:
        cls._original_plugin_dir = cli.PLUGIN_DIR
        cls._original_plugin_module = cli.PLUGIN_MODULE
        cli.PLUGIN_DIR = Path(__file__).parent / "commands"
        cli.PLUGIN_MODULE = "tests.commands"

    @classmethod
    def tearDownClass(cls) -> None:
        cli.PLUGIN_DIR = cls._original_plugin_dir
        cli.PLUGIN_MODULE = cls._original_plugin_module

    def test_get_command_returns_main_attribute_from_command_modules(self):
        command = cli.TartufoCLI().get_command(None, "foo")  # type: ignore
        self.assertEqual(command, command_foo.main)

    def test_get_command_fails_gracefully_on_invalid_commands(self):
        command = cli.TartufoCLI().get_command(None, "bar")  # type: ignore
        self.assertEqual(command, None)


class ListCommandTests(unittest.TestCase):
    @mock.patch("tartufo.cli.PLUGIN_DIR")
    def test_list_commands_excludes_init_py(self, mock_dir: mock.MagicMock):
        mock_dir.glob.return_value = [
            FakeFile("__init__.py"),
            FakeFile("foo.py"),
            FakeFile("bar.py"),
        ]
        commands = cli.TartufoCLI().list_commands(None)  # type: ignore
        self.assertNotIn("__init__", commands)

    @mock.patch("tartufo.cli.PLUGIN_DIR")
    def test_list_commands_only_looks_at_python_files(self, mock_dir: mock.MagicMock):
        mock_dir.glob.return_value = [
            FakeFile("__init__.py"),
            FakeFile("foo.py"),
            FakeFile("bar.py"),
        ]
        cli.TartufoCLI().list_commands(None)  # type: ignore
        mock_dir.glob.assert_called_once_with("*.py")

    @mock.patch("tartufo.cli.PLUGIN_DIR")
    def test_list_commands_strips_file_extensions(self, mock_dir: mock.MagicMock):
        mock_dir.glob.return_value = [
            FakeFile("foo.py"),
            FakeFile("bar.py"),
            FakeFile("baz.py"),
        ]
        commands = cli.TartufoCLI().list_commands(None)  # type: ignore
        self.assertEqual(commands, ["foo", "bar", "baz"])

    @mock.patch("tartufo.cli.PLUGIN_DIR")
    def test_list_commands_converts_underscore_to_hyphen(
        self, mock_dir: mock.MagicMock
    ):
        mock_dir.glob.return_value = [
            FakeFile("foo_bar.py"),
        ]
        commands = cli.TartufoCLI().list_commands(None)  # type: ignore
        self.assertEqual(commands, ["foo-bar"])


class ProcessIssuesTest(unittest.TestCase):
    @unittest.skipIf(
        helpers.BROKEN_USER_PATHS, "Skipping due to truncated Windows usernames"
    )
    @mock.patch("tartufo.cli.datetime")
    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    @mock.patch("tartufo.util.echo_result", new=mock.MagicMock())
    @mock.patch("tartufo.util.write_outputs", new=mock.MagicMock())
    def test_output_dir_is_called_out(
        self, mock_scanner: mock.MagicMock, mock_dt: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = [
            scanner.Issue(
                types.IssueType.Entropy, "foo", types.Chunk("foo", "/bar", {})
            )
        ]
        mock_dt.now.return_value.isoformat.return_value = "nownownow"
        runner = CliRunner()
        with runner.isolated_filesystem() as dirname:
            result = runner.invoke(
                cli.main, ["--output-dir", "./foo", "scan-local-repo", "."]
            )
        output_dir = (
            Path(dirname) / "foo" / "tartufo-scan-results-nownownow"
        ).resolve()
        self.assertEqual(
            result.output,
            f"Results have been saved in {output_dir}\n",
        )

    @unittest.skipUnless(helpers.WINDOWS, "Test is Windows-only")
    @unittest.skipIf(
        helpers.BROKEN_USER_PATHS, "Skipping due to truncated Windows usernames"
    )
    @mock.patch("tartufo.cli.datetime")
    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    @mock.patch("tartufo.util.echo_result", new=mock.MagicMock())
    @mock.patch("tartufo.util.write_outputs", new=mock.MagicMock())
    def test_output_dir_is_valid_name_in_windows(
        self, mock_scanner: mock.MagicMock, mock_dt: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = [
            scanner.Issue(
                types.IssueType.Entropy, "foo", types.Chunk("foo", "/bar", {})
            )
        ]
        mock_dt.now.return_value.isoformat.return_value = "now:now:now"
        runner = CliRunner()
        with runner.isolated_filesystem() as dirname:
            result = runner.invoke(
                cli.main, ["--output-dir", "./foo", "scan-local-repo", "."]
            )
        output_dir = (
            Path(dirname) / "foo" / "tartufo-scan-results-nownownow"
        ).resolve()
        self.assertEqual(
            result.output,
            f"Results have been saved in {output_dir}\n",
        )

    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    @mock.patch("tartufo.util.echo_result", new=mock.MagicMock())
    @mock.patch("tartufo.util.write_outputs", new=mock.MagicMock())
    def test_output_dir_is_not_called_out_when_outputting_json(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = [
            scanner.Issue(
                types.IssueType.Entropy, "foo", types.Chunk("foo", "/bar", {})
            )
        ]
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main, ["--output-dir", "./foo", "--json", "scan-local-repo", "."]
            )
        # All other outputs are mocked, so this is ensuring that the
        #   "Results have been saved in ..." message is not output.
        self.assertEqual(result.output, "")

    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    @mock.patch("tartufo.util.echo_result", new=mock.MagicMock())
    @mock.patch("tartufo.util.write_outputs", new=mock.MagicMock())
    def test_output_dir_is_created_if_it_does_not_exist(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = [
            scanner.Issue(
                types.IssueType.Entropy, "foo", types.Chunk("foo", "/bar", {})
            )
        ]
        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main, ["--output-dir", "./foo", "--json", "scan-local-repo", "."]
            )
            self.assertTrue(Path("./foo").exists())

    @mock.patch("tartufo.util.write_outputs", new=mock.MagicMock())
    @mock.patch("tartufo.util.echo_result", new=mock.MagicMock())
    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    def test_command_exits_with_positive_return_code_when_issues_are_found(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = [
            scanner.Issue(
                types.IssueType.Entropy, "foo", types.Chunk("foo", "/bar", {})
            )
        ]
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["scan-local-repo", "."])
        self.assertGreater(result.exit_code, 0)

    @mock.patch("tartufo.util.write_outputs", new=mock.MagicMock())
    @mock.patch("tartufo.util.echo_result", new=mock.MagicMock())
    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    def test_command_exits_with_zero_return_code_when_no_issues_are_found(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.issues = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["scan-local-repo", "."])
        self.assertEqual(result.exit_code, 0)

    @mock.patch("tartufo.util.write_outputs", new=mock.MagicMock())
    @mock.patch("tartufo.util.echo_result", new=mock.MagicMock())
    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    def test_command_raises_error_when_quiet_and_verbose_simultaneously(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.issues = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["-q", "-v", "scan-local-repo", "."])
        self.assertEqual(result.exit_code, 2)

    @mock.patch("tartufo.util.write_outputs", new=mock.MagicMock())
    @mock.patch("tartufo.util.echo_result", new=mock.MagicMock())
    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    def test_command_returns_with_zero_when_quiet_only(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.issues = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["-q", "scan-local-repo", "."])
        self.assertEqual(result.exit_code, 0)

    @mock.patch("tartufo.util.write_outputs", new=mock.MagicMock())
    @mock.patch("tartufo.util.echo_result", new=mock.MagicMock())
    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    def test_command_returns_with_zero_when_verbose_only(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.issues = []
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["-v", "scan-local-repo", "."])
        self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
