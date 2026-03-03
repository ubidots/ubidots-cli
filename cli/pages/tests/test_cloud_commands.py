import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from cli.commons.enums import DefaultInstanceFieldEnum
from cli.commons.enums import OutputFormatFieldsEnum
from cli.pages.commands import app
from cli.settings import settings


class TestListCloudCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch("cli.pages.commands.executor.list_pages_cloud")
    def test_list_cloud_default(self, mock_list_pages_cloud):
        result = self.runner.invoke(app, ["list"])

        self.assertEqual(result.exit_code, 0)
        mock_list_pages_cloud.assert_called_once_with(
            profile="",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            sort_by=None,
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    @patch("cli.pages.commands.executor.list_pages_cloud")
    def test_list_cloud_with_fields(self, mock_list_pages_cloud):
        result = self.runner.invoke(app, ["list", "--fields", "id,label,url"])

        self.assertEqual(result.exit_code, 0)
        mock_list_pages_cloud.assert_called_once_with(
            profile="",
            fields="id,label,url",
            sort_by=None,
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    @patch("cli.pages.commands.executor.list_pages_cloud")
    def test_list_cloud_with_json_format(self, mock_list_pages_cloud):
        result = self.runner.invoke(app, ["list", "--format", "json"])

        self.assertEqual(result.exit_code, 0)
        mock_list_pages_cloud.assert_called_once_with(
            profile="",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            sort_by=None,
            page_size=None,
            page=None,
            format=OutputFormatFieldsEnum.JSON,
        )

    @patch("cli.pages.commands.executor.list_pages_cloud")
    def test_list_cloud_with_sort_by(self, mock_list_pages_cloud):
        result = self.runner.invoke(app, ["list", "--sort-by", "createdAt"])

        self.assertEqual(result.exit_code, 0)
        mock_list_pages_cloud.assert_called_once_with(
            profile="",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            sort_by="createdAt",
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    @patch("cli.pages.commands.executor.list_pages_cloud")
    def test_list_cloud_with_pagination(self, mock_list_pages_cloud):
        result = self.runner.invoke(app, ["list", "--page-size", "10", "--page", "2"])

        self.assertEqual(result.exit_code, 0)
        mock_list_pages_cloud.assert_called_once_with(
            profile="",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            sort_by=None,
            page_size=10,
            page=2,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )


@patch("cli.commons.pipelines.Pipeline.run")
@patch("cli.pages.commands.get_instance_key")
class TestGetCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_get_page_by_id(self, mock_get_instance_key, mock_pipeline_run):
        mock_get_instance_key.return_value = "66e9a2aae24bae000e144c28"
        mock_pipeline_run.side_effect = lambda _: None

        result = self.runner.invoke(app, ["get", "--id", "66e9a2aae24bae000e144c28"])

        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(
            id="66e9a2aae24bae000e144c28", label=None
        )

    def test_get_page_by_label(self, mock_get_instance_key, mock_pipeline_run):
        mock_get_instance_key.return_value = "~my-page"
        mock_pipeline_run.side_effect = lambda _: None

        result = self.runner.invoke(app, ["get", "--label", "my-page"])

        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id=None, label="my-page")

    def test_get_page_requires_id_or_label(
        self, mock_get_instance_key, mock_pipeline_run
    ):
        mock_get_instance_key.side_effect = Exception(
            "Providing an '--id' or '--label' is required."
        )

        result = self.runner.invoke(app, ["get"])

        self.assertNotEqual(result.exit_code, 0)

    def test_get_page_with_custom_fields(
        self, mock_get_instance_key, mock_pipeline_run
    ):
        mock_get_instance_key.return_value = "66e9a2aae24bae000e144c28"
        mock_pipeline_run.side_effect = lambda _: None

        result = self.runner.invoke(
            app,
            ["get", "--id", "66e9a2aae24bae000e144c28", "--fields", "id,label,url"],
        )

        self.assertEqual(result.exit_code, 0)

    def test_get_page_with_json_format(self, mock_get_instance_key, mock_pipeline_run):
        mock_get_instance_key.return_value = "66e9a2aae24bae000e144c28"
        mock_pipeline_run.side_effect = lambda _: None

        result = self.runner.invoke(
            app,
            ["get", "--id", "66e9a2aae24bae000e144c28", "--format", "json"],
        )

        self.assertEqual(result.exit_code, 0)


@patch("cli.commons.pipelines.Pipeline.run")
class TestAddCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_add_page_with_name(self, mock_pipeline_run):
        mock_pipeline_run.return_value = None

        result = self.runner.invoke(app, ["add", "My Dashboard"])

        self.assertEqual(result.exit_code, 0)
        mock_pipeline_run.assert_called_once_with(
            {
                "profile": "",
                "name": "My Dashboard",
                "label": "my-dashboard",
                "root": "add_page_cloud",
            }
        )

    def test_add_page_with_name_and_label(self, mock_pipeline_run):
        mock_pipeline_run.return_value = None

        result = self.runner.invoke(
            app, ["add", "My Dashboard", "--label", "custom-dash"]
        )

        self.assertEqual(result.exit_code, 0)
        mock_pipeline_run.assert_called_once_with(
            {
                "profile": "",
                "name": "My Dashboard",
                "label": "custom-dash",
                "root": "add_page_cloud",
            }
        )

    def test_add_page_with_profile(self, mock_pipeline_run):
        mock_pipeline_run.return_value = None

        result = self.runner.invoke(
            app, ["add", "My Dashboard", "--profile", "production"]
        )

        self.assertEqual(result.exit_code, 0)
        mock_pipeline_run.assert_called_once_with(
            {
                "profile": "production",
                "name": "My Dashboard",
                "label": "my-dashboard",
                "root": "add_page_cloud",
            }
        )


@patch("cli.pages.commands.get_instance_key")
@patch("cli.pages.executor.Pipeline.run")
@patch("typer.confirm", return_value=True)
class TestDeleteCommand(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_delete_page_by_id(
        self, mock_confirm, mock_pipeline_run, mock_get_instance_key
    ):
        mock_get_instance_key.return_value = "valid_page_key"
        mock_pipeline_run.return_value = None

        result = self.runner.invoke(
            app, ["delete", "--id", "66e9a2aae24bae000e144c28", "--yes"]
        )

        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(
            id="66e9a2aae24bae000e144c28", label=None
        )
        mock_pipeline_run.assert_called_once_with(
            {
                "overwrite": {
                    "confirm": True,
                    "message": "Are you sure you want to delete the page?",
                },
                "profile": "",
                "page_key": "valid_page_key",
                "verbose": False,
                "root": "delete_page_cloud",
            }
        )

    def test_delete_page_by_label(
        self, mock_confirm, mock_pipeline_run, mock_get_instance_key
    ):
        mock_get_instance_key.return_value = "valid_page_key"
        mock_pipeline_run.return_value = None

        result = self.runner.invoke(app, ["delete", "--label", "my-page", "--yes"])

        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id=None, label="my-page")
        mock_pipeline_run.assert_called_once_with(
            {
                "overwrite": {
                    "confirm": True,
                    "message": "Are you sure you want to delete the page?",
                },
                "profile": "",
                "page_key": "valid_page_key",
                "verbose": False,
                "root": "delete_page_cloud",
            }
        )

    def test_delete_page_requires_id_or_label(
        self, mock_confirm, mock_pipeline_run, mock_get_instance_key
    ):
        mock_get_instance_key.side_effect = Exception(
            "Providing an '--id' or '--label' is required."
        )

        result = self.runner.invoke(app, ["delete"])

        self.assertNotEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
