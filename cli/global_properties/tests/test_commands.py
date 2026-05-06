from unittest import TestCase
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import patch

from typer.testing import CliRunner

from cli.commons.enums import DefaultInstanceFieldEnum
from cli.global_properties.commands import app as global_properties_app
from cli.settings import settings

runner = CliRunner()


@patch("cli.global_properties.commands.get_configuration", return_value=MagicMock())
@patch("cli.global_properties.handlers.list_properties")
class TestListCommand(TestCase):
    def test_list_with_defaults(self, mock_list, _):
        result = runner.invoke(global_properties_app, ["list"])
        self.assertEqual(result.exit_code, 0)
        mock_list.assert_called_once_with(
            active_config=ANY,
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            search=None,
            sort_by=None,
            page_size=None,
            page=None,
            created_after=None,
            updated_after=None,
            output_format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_with_search(self, mock_list, _):
        result = runner.invoke(global_properties_app, ["list", "--search", "api"])
        self.assertEqual(result.exit_code, 0)
        mock_list.assert_called_once_with(
            active_config=ANY,
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            search="api",
            sort_by=None,
            page_size=None,
            page=None,
            created_after=None,
            updated_after=None,
            output_format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_with_date_filters_and_pagination(self, mock_list, _):
        result = runner.invoke(
            global_properties_app,
            [
                "list",
                "--created-after",
                "2026-01-01T00:00:00Z",
                "--updated-after",
                "2026-04-01T00:00:00Z",
                "--page-size",
                "20",
                "--page",
                "2",
                "--sort-by",
                "createdAt",
                "--format",
                "json",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        mock_list.assert_called_once_with(
            active_config=ANY,
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            search=None,
            sort_by="createdAt",
            page_size=20,
            page=2,
            created_after="2026-01-01T00:00:00Z",
            updated_after="2026-04-01T00:00:00Z",
            output_format=ANY,
        )


@patch("cli.global_properties.commands.get_configuration", return_value=MagicMock())
@patch("cli.global_properties.handlers.retrieve_property")
class TestGetCommand(TestCase):
    def test_get_by_label(self, mock_retrieve, _):
        result = runner.invoke(global_properties_app, ["get", "api_key"])
        self.assertEqual(result.exit_code, 0)
        mock_retrieve.assert_called_once_with(
            active_config=ANY,
            property_key="api_key",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            output_format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_get_by_id_with_custom_fields(self, mock_retrieve, _):
        result = runner.invoke(
            global_properties_app,
            ["get", "5df2b8bf1d8472535a742e53", "--fields", "id,label,value,isSecret"],
        )
        self.assertEqual(result.exit_code, 0)
        mock_retrieve.assert_called_once_with(
            active_config=ANY,
            property_key="5df2b8bf1d8472535a742e53",
            fields="id,label,value,isSecret",
            output_format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_get_requires_key(self, mock_retrieve, _):
        result = runner.invoke(global_properties_app, ["get"])
        self.assertNotEqual(result.exit_code, 0)
        mock_retrieve.assert_not_called()


@patch("cli.global_properties.commands.get_configuration", return_value=MagicMock())
@patch("cli.global_properties.handlers.add_property")
class TestAddCommand(TestCase):
    def test_add_minimum_arguments(self, mock_add, _):
        result = runner.invoke(
            global_properties_app,
            ["add", "--label", "api_key", "--value", "abc123"],
        )
        self.assertEqual(result.exit_code, 0)
        _, kwargs = mock_add.call_args
        payload = kwargs["payload"]
        self.assertEqual(payload["label"], "api_key")
        self.assertEqual(payload["value"], "abc123")
        self.assertEqual(payload["format"], "string")
        self.assertFalse(payload["isSecret"])
        self.assertNotIn("scope", payload)
        self.assertNotIn("name", payload)
        self.assertNotIn("description", payload)

    def test_add_with_all_options(self, mock_add, _):
        result = runner.invoke(
            global_properties_app,
            [
                "add",
                "--label",
                "max_retries",
                "--value",
                "5",
                "--format",
                "int",
                "--name",
                "Max Retries",
                "--description",
                "Retry budget for outbound calls",
                "--scope",
                "functions,pages",
                "--secret",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        _, kwargs = mock_add.call_args
        payload = kwargs["payload"]
        self.assertEqual(payload["label"], "max_retries")
        self.assertEqual(payload["value"], 5)
        self.assertEqual(payload["format"], "int")
        self.assertEqual(payload["name"], "Max Retries")
        self.assertEqual(payload["description"], "Retry budget for outbound calls")
        self.assertEqual(payload["scope"], ["functions", "pages"])
        self.assertTrue(payload["isSecret"])

    def test_add_rejects_int_value_that_is_not_integer(self, mock_add, _):
        result = runner.invoke(
            global_properties_app,
            [
                "add",
                "--label",
                "max_retries",
                "--value",
                "notanumber",
                "--format",
                "int",
            ],
        )
        self.assertNotEqual(result.exit_code, 0)
        mock_add.assert_not_called()

    def test_add_rejects_invalid_json_value(self, mock_add, _):
        result = runner.invoke(
            global_properties_app,
            [
                "add",
                "--label",
                "config_blob",
                "--value",
                "{not: valid",
                "--format",
                "json",
            ],
        )
        self.assertNotEqual(result.exit_code, 0)
        mock_add.assert_not_called()

    def test_add_bool_coerces_true_false(self, mock_add, _):
        result = runner.invoke(
            global_properties_app,
            [
                "add",
                "--label",
                "feature_flag",
                "--value",
                "true",
                "--format",
                "bool",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        _, kwargs = mock_add.call_args
        self.assertIs(kwargs["payload"]["value"], True)

    def test_add_requires_label_and_value(self, mock_add, _):
        result = runner.invoke(global_properties_app, ["add", "--label", "only_label"])
        self.assertNotEqual(result.exit_code, 0)
        mock_add.assert_not_called()


@patch("cli.global_properties.commands.get_configuration", return_value=MagicMock())
@patch("cli.global_properties.handlers.update_property")
class TestUpdateCommand(TestCase):
    def test_update_without_value_does_not_touch_value(self, mock_update, _):
        result = runner.invoke(
            global_properties_app,
            ["update", "api_key", "--description", "rotated 2026-05"],
        )
        self.assertEqual(result.exit_code, 0)
        _, kwargs = mock_update.call_args
        payload = kwargs["payload"]
        self.assertNotIn("value", payload)
        self.assertNotIn("format", payload)
        self.assertEqual(payload["description"], "rotated 2026-05")
        self.assertEqual(kwargs["property_key"], "api_key")

    def test_update_with_value_requires_format(self, mock_update, _):
        result = runner.invoke(
            global_properties_app,
            ["update", "api_key", "--value", "newval"],
        )
        self.assertNotEqual(result.exit_code, 0)
        mock_update.assert_not_called()

    def test_update_with_value_and_format_coerces(self, mock_update, _):
        result = runner.invoke(
            global_properties_app,
            ["update", "max_retries", "--value", "10", "--format", "int"],
        )
        self.assertEqual(result.exit_code, 0)
        _, kwargs = mock_update.call_args
        payload = kwargs["payload"]
        self.assertEqual(payload["value"], 10)
        self.assertEqual(payload["format"], "int")

    def test_update_clear_scope_with_empty_string(self, mock_update, _):
        result = runner.invoke(
            global_properties_app,
            ["update", "api_key", "--scope", ""],
        )
        self.assertEqual(result.exit_code, 0)
        _, kwargs = mock_update.call_args
        self.assertEqual(kwargs["payload"]["scope"], [])

    def test_update_toggle_secret_off(self, mock_update, _):
        result = runner.invoke(
            global_properties_app,
            ["update", "api_key", "--no-secret"],
        )
        self.assertEqual(result.exit_code, 0)
        _, kwargs = mock_update.call_args
        self.assertIs(kwargs["payload"]["isSecret"], False)

    def test_update_requires_key(self, mock_update, _):
        result = runner.invoke(global_properties_app, ["update"])
        self.assertNotEqual(result.exit_code, 0)
        mock_update.assert_not_called()


@patch("cli.global_properties.commands.get_configuration", return_value=MagicMock())
@patch("cli.global_properties.handlers.delete_property")
class TestDeleteCommand(TestCase):
    def test_delete_with_yes_skips_prompt(self, mock_delete, _):
        result = runner.invoke(global_properties_app, ["delete", "api_key", "--yes"])
        self.assertEqual(result.exit_code, 0)
        mock_delete.assert_called_once_with(active_config=ANY, property_key="api_key")

    def test_delete_aborts_when_user_declines(self, mock_delete, _):
        result = runner.invoke(
            global_properties_app, ["delete", "api_key"], input="n\n"
        )
        self.assertNotEqual(result.exit_code, 0)
        mock_delete.assert_not_called()

    def test_delete_requires_key(self, mock_delete, _):
        result = runner.invoke(global_properties_app, ["delete"])
        self.assertNotEqual(result.exit_code, 0)
        mock_delete.assert_not_called()


class TestHelp(TestCase):
    def test_top_level_help_lists_commands(self):
        result = runner.invoke(global_properties_app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        for cmd in ("list", "get", "add", "update", "delete"):
            self.assertIn(cmd, result.output)
