import unittest
from collections import namedtuple
from unittest import mock

from click.testing import CliRunner
from tartufo import cli, scanner, types


FakeFile = namedtuple("FakeFile", ["name"])


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
    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    @mock.patch("tartufo.util.echo_issues", new=mock.MagicMock())
    @mock.patch("tartufo.util.write_outputs", new=mock.MagicMock())
    def test_output_dir_is_called_out(self, mock_scanner: mock.MagicMock):
        mock_scanner.return_value.scan.return_value = [
            scanner.Issue(types.IssueType.Entropy, "foo", types.Chunk("foo", "/bar"))
        ]
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main, ["--output-dir", "/foo", "scan-local-repo", "."]
            )
        self.assertEqual(result.output, "Results have been saved in /foo\n")

    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    @mock.patch("tartufo.util.echo_issues", new=mock.MagicMock())
    @mock.patch("tartufo.util.write_outputs", new=mock.MagicMock())
    def test_output_dir_is_not_called_out_when_outputting_json(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = [
            scanner.Issue(types.IssueType.Entropy, "foo", types.Chunk("foo", "/bar"))
        ]
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cli.main, ["--output-dir", "/foo", "--json", "scan-local-repo", "."]
            )
        # All other outputs are mocked, so this is ensuring that the
        #   "Results have been saved in ..." message is not output.
        self.assertEqual(result.output, "")

    @mock.patch("tartufo.util.write_outputs", new=mock.MagicMock())
    @mock.patch("tartufo.util.echo_issues", new=mock.MagicMock())
    @mock.patch("tartufo.commands.scan_local_repo.GitRepoScanner")
    def test_command_exits_with_positive_return_code_when_issues_are_found(
        self, mock_scanner: mock.MagicMock
    ):
        mock_scanner.return_value.scan.return_value = [
            scanner.Issue(types.IssueType.Entropy, "foo", types.Chunk("foo", "/bar"))
        ]
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["scan-local-repo", "."])
        self.assertGreater(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
