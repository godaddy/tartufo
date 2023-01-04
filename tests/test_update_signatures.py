import io
import textwrap
from os import remove
from pathlib import Path
from typing import Sequence, Set

from unittest import mock, TestCase
import tomlkit
from click.testing import CliRunner

from tartufo import cli, types
from tartufo.commands import update_signatures


class UpdateSignaturesTests(TestCase):
    @mock.patch("tartufo.commands.update_signatures.load_config_from_path")
    def test_with_no_signatures_in_config(
        self, mock_load_config: mock.MagicMock
    ) -> None:
        mock_load_config.return_value = Path("."), {"test": None}

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["update-signatures", "."])

        mock_load_config.assert_called_once()
        self.assertEqual(
            result.output, "No signatures found in configuration, exiting...\n"
        )

    @mock.patch("tartufo.commands.update_signatures.load_config_from_path")
    def test_with_no_config(self, mock_load_config: mock.MagicMock) -> None:
        mock_load_config.side_effect = FileNotFoundError()

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["update-signatures", "."])

        mock_load_config.assert_called_once()
        self.assertEqual(result.output, "No tartufo config found, exiting...\n")

    @mock.patch("tartufo.commands.update_signatures.GitRepoScanner")
    @mock.patch("tartufo.commands.update_signatures.load_config_from_path")
    def test_with_no_deprecated_signatures(
        self, mock_load_config: mock.MagicMock, mock_scanner: mock.MagicMock
    ) -> None:
        mock_load_config.return_value = Path("."), {
            "exclude_signatures": [{"signature": "a"}]
        }

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["update-signatures", "."])

        mock_scanner.assert_called_once()
        mock_load_config.assert_called_once()
        self.assertEqual(result.output, "Found 0 deprecated signatures.\n")

    @mock.patch("tartufo.commands.update_signatures.scan_local_repo")
    @mock.patch("tartufo.commands.update_signatures.load_config_from_path")
    def test_update_signatures_when_scanner_is_none(
        self, mock_load_config: mock.MagicMock, mock_scan_local: mock.MagicMock
    ) -> None:
        mock_scan_local.return_value = None, "b"
        mock_load_config.return_value = Path("."), {
            "exclude_signatures": [{"signature": "a"}]
        }

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["update-signatures", "."])

        mock_scan_local.assert_called_once()
        mock_load_config.assert_called_once()
        self.assertGreater(result.exit_code, 0)
        self.assertEqual(result.output, "Unable to update signatures\n")

    @mock.patch("tartufo.commands.update_signatures.write_updated_signatures")
    @mock.patch("tartufo.commands.update_signatures.get_deprecations")
    @mock.patch("tartufo.commands.update_signatures.remove_duplicated_entries")
    @mock.patch("tartufo.commands.update_signatures.scan_local_repo")
    @mock.patch("tartufo.commands.update_signatures.load_config_from_path")
    def test_when_no_remove_duplicates(
        self,
        mock_load_config: mock.MagicMock,
        mock_scan_local: mock.MagicMock,
        mock_remove_dups: mock.MagicMock,
        mock_get_deprecations: mock.MagicMock,
        mock_write: mock.MagicMock,
    ) -> None:
        mock_scanner = mock.MagicMock()
        mock_write.return_value = None
        mock_get_deprecations.return_value = {("123", "abc"), ("456", "def")}
        mock_scan_local.return_value = mock_scanner, "b"
        mock_load_config.return_value = Path("."), {
            "exclude_signatures": [{"signature": "a"}]
        }

        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(
                cli.main, ["update-signatures", ".", "--no-remove-duplicates"]
            )

        mock_get_deprecations.assert_called_once()
        mock_remove_dups.assert_not_called()
        mock_scan_local.assert_called_once()
        mock_load_config.assert_called_once()
        mock_write.assert_called_once()

    @mock.patch("tartufo.commands.update_signatures.write_updated_signatures")
    @mock.patch("tartufo.commands.update_signatures.get_deprecations")
    @mock.patch("tartufo.commands.update_signatures.remove_duplicated_entries")
    @mock.patch("tartufo.commands.update_signatures.scan_local_repo")
    @mock.patch("tartufo.commands.update_signatures.load_config_from_path")
    def test_when_remove_duplicates(
        self,
        mock_load_config: mock.MagicMock,
        mock_scan_local: mock.MagicMock,
        mock_remove_dups: mock.MagicMock,
        mock_get_deprecations: mock.MagicMock,
        mock_write: mock.MagicMock,
    ) -> None:
        mock_scanner = mock.MagicMock()
        mock_scan_local.return_value = mock_scanner, "b"
        mock_write.return_value = None
        mock_get_deprecations.return_value = {("123", "abc"), ("456", "def")}
        mock_load_config.return_value = Path("."), {
            "exclude_signatures": [{"signature": "a"}]
        }

        runner = CliRunner()
        with runner.isolated_filesystem():
            runner.invoke(cli.main, ["update-signatures", "."])

        mock_get_deprecations.assert_called_once()
        mock_remove_dups.assert_called_once()
        mock_scan_local.assert_called_once()
        mock_load_config.assert_called_once()
        mock_write.assert_called_once()

    @mock.patch("tartufo.commands.update_signatures.types.GlobalOptions")
    @mock.patch("tartufo.commands.update_signatures.util.process_issues")
    def test_scan_local_with_git_local_exc(
        self, mock_process_issues: mock.MagicMock, mock_global_options: mock.MagicMock
    ) -> None:
        mock_process_issues.side_effect = types.GitLocalException()

        scanner, stderr = update_signatures.scan_local_repo(
            mock_global_options, ".", None, 1, None, False
        )

        mock_process_issues.assert_called_once_with(".", scanner, mock_global_options)
        self.assertEqual(stderr.getvalue(), ". is not a valid git repository.\n")

    @mock.patch("tartufo.commands.update_signatures.types.GlobalOptions")
    @mock.patch("tartufo.commands.update_signatures.util.process_issues")
    def test_scan_local_with_tartufo_exc(
        self, mock_process_issues: mock.MagicMock, mock_global_options: mock.MagicMock
    ) -> None:
        mock_process_issues.side_effect = types.TartufoException("TARTUFO EXC")

        scanner, stderr = update_signatures.scan_local_repo(
            mock_global_options, ".", None, 1, None, False
        )

        mock_process_issues.assert_called_once_with(".", scanner, mock_global_options)
        self.assertEqual(stderr.getvalue(), "TARTUFO EXC\n")

    @mock.patch("tartufo.commands.update_signatures.write_updated_signatures")
    @mock.patch("tartufo.commands.update_signatures.get_deprecations")
    @mock.patch("tartufo.commands.update_signatures.scan_local_repo")
    @mock.patch("tartufo.commands.update_signatures.load_config_from_path")
    def test_found_output_with_signatures(
        self,
        mock_load_config: mock.MagicMock,
        mock_scan_local: mock.MagicMock,
        mock_get_deprecations: mock.MagicMock,
        mock_write: mock.MagicMock,
    ) -> None:
        mock_scanner = mock.MagicMock()
        mock_write.return_value = None
        mock_get_deprecations.return_value = {("123", "abc"), ("456", "def")}
        mock_scan_local.return_value = (
            mock_scanner,
            (
                "DeprecationWarning: Signature 123 was ... use signature abc instead.\n"
                "DeprecationWarning: Signature 456 was ... use signature def instead."
            ),
        )

        mock_load_config.return_value = Path("."), {
            "exclude_signatures": [{"signature": "123"}, {"signature": "456"}]
        }

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["update-signatures", "."])

        mock_write.assert_called_once()
        mock_get_deprecations.assert_called_once()
        mock_scan_local.assert_called_once()
        mock_load_config.assert_called_once()
        self.assertTrue(result.output.startswith("Found 2 deprecated signatures.\n"))

        # The numbers before the paren can vary so we leave them out of the test
        self.assertTrue(") '123' -> 'abc'\n" in result.output)
        self.assertTrue(") '456' -> 'def'\n" in result.output)
        self.assertTrue("Removed 0 duplicated signatures.\n" in result.output)
        self.assertTrue(result.output.endswith("Updated 2 deprecated signatures.\n"))

    @mock.patch("tartufo.commands.update_signatures.write_updated_signatures")
    @mock.patch("tartufo.commands.update_signatures.get_deprecations")
    @mock.patch("tartufo.commands.update_signatures.scan_local_repo")
    @mock.patch("tartufo.commands.update_signatures.load_config_from_path")
    def test_found_output_with_duplicated_signatures(
        self,
        mock_load_config: mock.MagicMock,
        mock_scan_local: mock.MagicMock,
        mock_get_deprecations: mock.MagicMock,
        mock_write: mock.MagicMock,
    ) -> None:
        mock_scanner = mock.MagicMock()
        mock_write.return_value = None
        mock_get_deprecations.return_value = {
            ("123", "abc"),
            ("456", "def"),
            ("789", "abc"),
        }

        mock_scan_local.return_value = (
            mock_scanner,
            (
                "DeprecationWarning: Signature 123 was ... use signature abc instead.\n"
                "DeprecationWarning: Signature 456 was ... use signature def instead.\n"
                "DeprecationWarning: Signature 789 was ... use signature abc instead."
            ),
        )

        mock_load_config.return_value = Path("."), {
            "exclude_signatures": [
                {"signature": "123"},
                {"signature": "456"},
                {"signature": "789"},
            ]
        }

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["update-signatures", "."])

        mock_write.assert_called_once()
        mock_get_deprecations.assert_called_once()
        mock_scan_local.assert_called_once()
        mock_load_config.assert_called_once()
        self.assertTrue(result.output.startswith("Found 3 deprecated signatures.\n"))

        # The numbers before the paren can vary so we leave them out of the test
        self.assertTrue(") '123' -> 'abc'\n" in result.output)
        self.assertTrue(") '456' -> 'def'\n" in result.output)
        self.assertTrue(") '789' -> 'abc'\n" in result.output)
        self.assertTrue("Removed 1 duplicated signature.\n" in result.output)
        self.assertTrue(result.output.endswith("Updated 3 deprecated signatures.\n"))

    @mock.patch("tartufo.commands.update_signatures.write_updated_signatures")
    @mock.patch("tartufo.commands.update_signatures.replace_deprecated_signatures")
    @mock.patch("tartufo.commands.update_signatures.get_deprecations")
    @mock.patch("tartufo.commands.update_signatures.scan_local_repo")
    @mock.patch("tartufo.commands.update_signatures.load_config_from_path")
    def test_found_output_with_no_signatures(
        self,
        mock_load_config: mock.MagicMock,
        mock_scan_local: mock.MagicMock,
        mock_get_deprecations: mock.MagicMock,
        mock_replace: mock.MagicMock,
        mock_write: mock.MagicMock,
    ) -> None:
        mock_scanner = mock.MagicMock()
        mock_write.return_value = None
        mock_replace.return_value = 2
        mock_get_deprecations.return_value = {}
        mock_scan_local.return_value = mock_scanner, ""
        mock_load_config.return_value = Path("."), {"exclude_signatures": "a"}

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.main, ["update-signatures", "."])

        mock_replace.assert_called_once()
        mock_get_deprecations.assert_called_once()
        mock_scan_local.assert_called_once()
        self.assertEqual(result.output, "Found 0 deprecated signatures.\n")

    def test_replace_deprecated_with_list_of_strings(self) -> None:
        deprecations: Set[Sequence[str]] = set()
        deprecations.update((("123", "abc"), ("456", "def")))
        config_data = {"exclude_signatures": ["123", "456"]}
        expected_result = {"exclude_signatures": ["abc", "def"]}

        count = update_signatures.replace_deprecated_signatures(
            deprecations, config_data
        )

        self.assertEqual(count, 2)
        self.assertEqual(config_data, expected_result)

    def test_remove_duplicated_entries(self) -> None:
        initial_data = {
            "exclude_signatures": [
                {"signature": "123", "reason": "first"},
                {"signature": "123", "reason": "second"},
                {"signature": "456"},
            ]
        }

        expected_data = {
            "exclude_signatures": [
                {"signature": "123", "reason": "first"},
                {"signature": "456"},
            ]
        }

        update_signatures.remove_duplicated_entries(initial_data)
        self.assertEqual(initial_data, expected_data)

    def test_get_deprecations_with_deprecations(self) -> None:
        expected_deprecations = {("123", "abc"), ("456", "def"), ("789", "ghi")}
        stderr = io.StringIO(
            "DeprecationWarning: Signature 123 was ... use signature abc instead.\n"
            "DeprecationWarning: Signature 456 was ... use signature def instead.\n"
            "DeprecationWarning: Signature 789 was ... use signature ghi instead."
        )

        deprecations = update_signatures.get_deprecations(stderr)

        self.assertEqual(len(deprecations), 3)
        self.assertTrue(isinstance(deprecations, set))
        self.assertEqual(deprecations, expected_deprecations)

    def test_get_deprecations_with_no_deprecations(self) -> None:
        stderr = io.StringIO("No deprecations here :).")

        deprecations = update_signatures.get_deprecations(stderr)

        self.assertTrue(isinstance(deprecations, set))
        self.assertEqual(len(deprecations), 0)

    def test_replace_deprecated_signatures(self) -> None:
        deprecations: Set[Sequence[str]] = set()
        deprecations.update((("123", "abc"), ("456", "def"), ("789", "ghi")))
        expected_result = {
            "exclude_signatures": [
                {"signature": "abc"},
                {"signature": "def"},
                {"signature": "ghi"},
            ]
        }

        config_data = {
            "exclude_signatures": [
                {"signature": "123"},
                {"signature": "456"},
                {"signature": "789"},
            ]
        }

        update_signatures.replace_deprecated_signatures(deprecations, config_data)
        self.assertEqual(config_data, expected_result)

    def test_write_updated_signatures(self) -> None:
        file_name = Path("test.toml")
        initial_file_content = textwrap.dedent(
            """[tool.tartufo]
            exclude-signatures = [
                {signature = '123'},
                {signature = '456'},
                {signature = '789'}
            ]
            """
        )

        expected_deprecations: Set[Sequence[str]] = set()
        expected_deprecations.update((("123", "abc"), ("456", "def"), ("789", "ghi")))
        config_data = {
            "exclude_signatures": [
                {"signature": "123"},
                {"signature": "456"},
                {"signature": "789"},
            ]
        }

        with open(file_name, "w") as config_file:
            config_file.write(initial_file_content)

        update_signatures.replace_deprecated_signatures(
            expected_deprecations, config_data
        )
        update_signatures.write_updated_signatures(file_name, config_data)

        result_config_data = {
            "tool": {
                "tartufo": {
                    key.replace("_", "-"): value for key, value in config_data.items()
                }
            }
        }

        with open(file_name, "r") as config_file:
            file_content = config_file.read()
            self.assertEqual(result_config_data, tomlkit.loads(file_content))

        remove(file_name)
