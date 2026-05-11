from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import patch

from typer.testing import CliRunner

from cli.apps.commands import app as apps_app

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def _ok_response(json_body):
    resp = MagicMock()
    resp.is_success = True
    resp.status_code = 200
    resp.json.return_value = json_body
    return resp


def _error_response(status, json_body=None):
    resp = MagicMock()
    resp.is_success = False
    resp.status_code = status
    resp.text = "error"
    resp.reason_phrase = "Unauthorized"
    resp.json.return_value = json_body or {"detail": "invalid token"}
    resp.request = MagicMock()
    return resp


@patch("cli.apps.commands.get_configuration", return_value=MagicMock())
@patch("cli.apps.handlers.list_apps")
class TestListAppsCommand(TestCase):
    def test_list_defaults(self, mock_list, _):
        mock_list.return_value = _ok_response(
            {"results": [{"id": "abc", "label": "iotexpo", "name": "IoT Expo"}]}
        )
        result = runner.invoke(apps_app, ["list"])
        self.assertEqual(result.exit_code, 0)
        mock_list.assert_called_once_with(
            active_config=ANY,
            fields=ANY,
            filter=None,
            sort_by=None,
            page_size=None,
            page=None,
        )

    def test_list_json_format(self, mock_list, _):
        mock_list.return_value = _ok_response(
            {"results": [{"id": "abc", "label": "iotexpo"}]}
        )
        result = runner.invoke(apps_app, ["list", "--format", "json"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("iotexpo", result.output)

    def test_list_unauthorized_exits_non_zero(self, mock_list, _):
        mock_list.return_value = _error_response(401)
        result = runner.invoke(apps_app, ["list"])
        self.assertNotEqual(result.exit_code, 0)


@patch("cli.apps.commands.get_configuration", return_value=MagicMock())
@patch("cli.apps.handlers.get_menu")
class TestMenuGetCommand(TestCase):
    def test_get_by_id(self, mock_get, _):
        mock_get.return_value = _ok_response(
            {"menuMode": "custom", "menuXml": "<tree/>", "menuAlignment": "left"}
        )
        result = runner.invoke(
            apps_app, ["menu", "get", "--id", "5df2b8bf1d8472535a742e53"]
        )
        self.assertEqual(result.exit_code, 0)
        mock_get.assert_called_once_with(
            active_config=ANY,
            app_key="5df2b8bf1d8472535a742e53",
        )
        self.assertIn("<tree/>", result.output)

    def test_get_by_label(self, mock_get, _):
        mock_get.return_value = _ok_response(
            {"menuMode": "custom", "menuXml": "<tree/>", "menuAlignment": "left"}
        )
        result = runner.invoke(
            apps_app, ["menu", "get", "--label", "iotexpo_ubidots_app"]
        )
        self.assertEqual(result.exit_code, 0)
        mock_get.assert_called_once_with(
            active_config=ANY,
            app_key="~iotexpo_ubidots_app",
        )

    def test_get_missing_selector_errors(self, mock_get, _):
        result = runner.invoke(apps_app, ["menu", "get"])
        self.assertNotEqual(result.exit_code, 0)
        mock_get.assert_not_called()

    def test_get_writes_to_output_file(self, mock_get, _):
        mock_get.return_value = _ok_response(
            {"menuMode": "custom", "menuXml": "<tree/>", "menuAlignment": "left"}
        )
        with TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "menu.json"
            result = runner.invoke(
                apps_app,
                [
                    "menu",
                    "get",
                    "--id",
                    "5df2b8bf1d8472535a742e53",
                    "--format",
                    "json",
                    "--output",
                    str(output_path),
                ],
            )
            self.assertEqual(result.exit_code, 0)
            self.assertIn("<tree/>", output_path.read_text())


@patch("cli.apps.commands.get_configuration", return_value=MagicMock())
@patch("cli.apps.handlers.set_menu")
class TestMenuSetCommand(TestCase):
    def test_set_happy_path_with_valid_xml(self, mock_set, _):
        mock_set.return_value = _ok_response({})
        result = runner.invoke(
            apps_app,
            [
                "menu",
                "set",
                "--label",
                "iotexpo_ubidots_app",
                "--file",
                str(FIXTURES / "menu_valid.xml"),
                "--alignment",
                "left",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        mock_set.assert_called_once()
        _, kwargs = mock_set.call_args
        payload = kwargs["payload"]
        self.assertEqual(payload["menuAlignment"], "left")
        self.assertEqual(payload["menuMode"], "custom")
        self.assertIn("<tree>", payload["menuXml"])

    def test_set_rejects_invalid_xml_without_calling_api(self, mock_set, _):
        result = runner.invoke(
            apps_app,
            [
                "menu",
                "set",
                "--id",
                "5df2b8bf1d8472535a742e53",
                "--file",
                str(FIXTURES / "menu_invalid.xml"),
            ],
        )
        self.assertNotEqual(result.exit_code, 0)
        mock_set.assert_not_called()

    def test_set_rejects_bad_alignment(self, mock_set, _):
        result = runner.invoke(
            apps_app,
            [
                "menu",
                "set",
                "--id",
                "5df2b8bf1d8472535a742e53",
                "--file",
                str(FIXTURES / "menu_valid.xml"),
                "--alignment",
                "diagonal",
            ],
        )
        self.assertNotEqual(result.exit_code, 0)
        mock_set.assert_not_called()

    def test_set_requires_file(self, mock_set, _):
        result = runner.invoke(
            apps_app,
            ["menu", "set", "--id", "5df2b8bf1d8472535a742e53"],
        )
        self.assertNotEqual(result.exit_code, 0)
        mock_set.assert_not_called()


@patch("cli.apps.commands.get_configuration", return_value=MagicMock())
@patch("cli.apps.handlers.reset_menu")
class TestMenuResetCommand(TestCase):
    def test_reset_with_yes_skips_prompt(self, mock_reset, _):
        mock_reset.return_value = _ok_response({})
        result = runner.invoke(
            apps_app,
            ["menu", "reset", "--id", "5df2b8bf1d8472535a742e53", "--yes"],
        )
        self.assertEqual(result.exit_code, 0)
        mock_reset.assert_called_once_with(
            active_config=ANY,
            app_key="5df2b8bf1d8472535a742e53",
        )

    def test_reset_aborts_when_user_declines(self, mock_reset, _):
        result = runner.invoke(
            apps_app,
            ["menu", "reset", "--id", "5df2b8bf1d8472535a742e53"],
            input="n\n",
        )
        self.assertNotEqual(result.exit_code, 0)
        mock_reset.assert_not_called()


class TestMenuDefaultCommand(TestCase):
    def test_default_prints_bundled_menu_offline(self):
        result = runner.invoke(apps_app, ["menu", "default"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("<tree>", result.output)
        self.assertIn("Devices", result.output)

    def test_default_json_format_wraps_with_metadata(self):
        result = runner.invoke(apps_app, ["menu", "default", "--format", "json"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('"menuMode": "default"', result.output)
        self.assertIn('"menuXml":', result.output)


class TestMenuSchemaCommand(TestCase):
    def test_schema_prints_dtd_offline(self):
        result = runner.invoke(apps_app, ["menu", "schema"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("<!ELEMENT tree", result.output)


class TestAppsHelp(TestCase):
    def test_apps_help_mentions_list_and_schema(self):
        result = runner.invoke(apps_app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("list", result.output.lower())
        self.assertIn("schema", result.output.lower())

    def test_menu_help_mentions_schema(self):
        result = runner.invoke(apps_app, ["menu", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("schema", result.output.lower())
