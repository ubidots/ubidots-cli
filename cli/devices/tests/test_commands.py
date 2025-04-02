import json
from unittest import TestCase
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import patch

from typer.testing import CliRunner

from cli.commons.enums import DefaultInstanceFieldEnum
from cli.devices.commands import app as device_app
from cli.settings import settings

runner = CliRunner()


@patch("cli.devices.commands.get_configuration", return_value=MagicMock())
@patch("cli.devices.commands.get_instance_key")
@patch("cli.devices.handlers.delete_device")
class TestDeleteCommand(TestCase):
    def test_delete_device_by_id(self, mock_delete_device, mock_get_instance_key, _):
        mock_get_instance_key.return_value = "device_key_from_id"
        result = runner.invoke(device_app, ["delete", "--id", "device123"])
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="device123", label=None)
        mock_delete_device.assert_called_once_with(
            active_config=ANY, device_key="device_key_from_id"
        )

    def test_delete_device_by_label(self, mock_delete_device, mock_get_instance_key, _):
        mock_get_instance_key.return_value = "device_key_from_label"
        result = runner.invoke(device_app, ["delete", "--label", "myDeviceLabel"])
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id=None, label="myDeviceLabel")
        mock_delete_device.assert_called_once_with(
            active_config=ANY, device_key="device_key_from_label"
        )

    def test_delete_device_both_id_and_label(
        self, mock_delete_device, mock_get_instance_key, _
    ):
        mock_get_instance_key.return_value = "device_key_from_id"
        result = runner.invoke(
            device_app, ["delete", "--id", "device123", "--label", "myDeviceLabel"]
        )
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(
            id="device123", label="myDeviceLabel"
        )
        mock_delete_device.assert_called_once_with(
            active_config=ANY, device_key="device_key_from_id"
        )


@patch("cli.devices.commands.get_configuration", return_value=MagicMock())
@patch("cli.devices.commands.get_instance_key")
@patch("cli.devices.handlers.retrieve_device")
class TestGetCommand(TestCase):
    def test_get_device_by_id(self, mock_retrieve_device, mock_get_instance_key, _):
        mock_get_instance_key.return_value = "device_key_from_id"
        result = runner.invoke(device_app, ["get", "--id", "device123"])
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="device123", label=None)
        mock_retrieve_device.assert_called_once_with(
            active_config=ANY,
            device_key="device_key_from_id",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_get_device_by_label(self, mock_retrieve_device, mock_get_instance_key, _):
        mock_get_instance_key.return_value = "device_key_from_label"
        result = runner.invoke(device_app, ["get", "--label", "myDeviceLabel"])
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id=None, label="myDeviceLabel")
        mock_retrieve_device.assert_called_once_with(
            active_config=ANY,
            device_key="device_key_from_label",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_get_device_both_id_and_label(
        self, mock_retrieve_device, mock_get_instance_key, _
    ):
        mock_get_instance_key.return_value = "device_key_from_id"
        result = runner.invoke(
            device_app, ["get", "--id", "device123", "--label", "myDeviceLabel"]
        )
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(
            id="device123", label="myDeviceLabel"
        )
        mock_retrieve_device.assert_called_once_with(
            active_config=ANY,
            device_key="device_key_from_id",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_get_device_with_custom_fields(
        self, mock_retrieve_device, mock_get_instance_key, _
    ):
        mock_get_instance_key.return_value = "device_key_from_id"
        custom_fields = "name,location,status"
        result = runner.invoke(
            device_app, ["get", "--id", "device123", "--fields", custom_fields]
        )
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="device123", label=None)
        mock_retrieve_device.assert_called_once_with(
            active_config=ANY,
            device_key="device_key_from_id",
            fields=custom_fields,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )


@patch("cli.devices.commands.get_configuration", return_value=MagicMock())
@patch("cli.devices.handlers.list_devices")
class TestListCommand(TestCase):
    def test_list_devices_with_defaults(self, mock_list_devices, _):
        result = runner.invoke(device_app, ["list"])
        self.assertEqual(result.exit_code, 0)
        mock_list_devices.assert_called_once_with(
            active_config=ANY,
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            filter=None,
            sort_by=None,
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_devices_with_custom_fields(self, mock_list_devices, _):
        custom_fields = "name,location,status"
        result = runner.invoke(device_app, ["list", "--fields", custom_fields])
        self.assertEqual(result.exit_code, 0)
        mock_list_devices.assert_called_once_with(
            active_config=ANY,
            fields=custom_fields,
            filter=None,
            sort_by=None,
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_devices_with_filter(self, mock_list_devices, _):
        filter_value = "isActive=true"
        result = runner.invoke(device_app, ["list", "--filter", filter_value])
        self.assertEqual(result.exit_code, 0)
        mock_list_devices.assert_called_once_with(
            active_config=ANY,
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            filter=filter_value,
            sort_by=None,
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_devices_with_sort(self, mock_list_devices, _):
        sort_by_value = "name"
        result = runner.invoke(device_app, ["list", "--sort-by", sort_by_value])
        self.assertEqual(result.exit_code, 0)
        mock_list_devices.assert_called_once_with(
            active_config=ANY,
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            filter=None,
            sort_by=sort_by_value,
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_devices_with_pagination(self, mock_list_devices, _):
        result = runner.invoke(device_app, ["list", "--page-size", "10", "--page", "2"])
        self.assertEqual(result.exit_code, 0)
        mock_list_devices.assert_called_once_with(
            active_config=ANY,
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            filter=None,
            sort_by=None,
            page_size=10,
            page=2,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_devices_with_all_options(self, mock_list_devices, _):
        result = runner.invoke(
            device_app,
            [
                "list",
                "--fields",
                "name,location,status",
                "--filter",
                "isActive=true",
                "--sort-by",
                "created_at",
                "--page-size",
                "20",
                "--page",
                "1",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        mock_list_devices.assert_called_once_with(
            active_config=ANY,
            fields="name,location,status",
            filter="isActive=true",
            sort_by="created_at",
            page_size=20,
            page=1,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )


@patch("cli.devices.commands.get_configuration", return_value=MagicMock())
@patch("cli.devices.handlers.add_device")
class TestAddCommand(TestCase):
    def test_add_device_with_minimum_arguments(self, mock_add_device, _):
        result = runner.invoke(device_app, ["add", "deviceLabel"])
        self.assertEqual(result.exit_code, 0)
        mock_add_device.assert_called_once_with(
            active_config=ANY,
            label="deviceLabel",
            name="",
            description="",
            organization="",
            tags="",
            properties={},
        )

    def test_add_device_with_all_options(self, mock_add_device, _):
        properties = '{"key1": "value1", "key2": 123}'
        result = runner.invoke(
            device_app,
            [
                "add",
                "deviceLabel",
                "--name",
                "DeviceName",
                "--description",
                "Test device description",
                "--organization",
                "~testOrg",
                "--tags",
                "tag1,tag2",
                "--properties",
                properties,
            ],
        )
        self.assertEqual(result.exit_code, 0)
        mock_add_device.assert_called_once_with(
            active_config=ANY,
            label="deviceLabel",
            name="DeviceName",
            description="Test device description",
            organization="~testOrg",
            tags="tag1,tag2",
            properties=json.loads(properties),
        )

    def test_add_device_with_invalid_json_properties(self, mock_add_device, _):
        result = runner.invoke(
            device_app, ["add", "deviceLabel", "--properties", "{key1: value1}"]
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid JSON format.", result.stdout)
        mock_add_device.assert_not_called()


@patch("cli.devices.commands.get_configuration", return_value=MagicMock())
@patch("cli.devices.commands.get_instance_key")
@patch("cli.devices.handlers.update_device")
class TestUpdateCommand(TestCase):
    def test_update_device_by_id_with_minimum_arguments(
        self, mock_update_device, mock_get_instance_key, _
    ):
        mock_get_instance_key.return_value = "device_key_from_id"
        result = runner.invoke(device_app, ["update", "--id", "device123"])
        self.assertEqual(result.exit_code, 0)
        mock_update_device.assert_called_once_with(
            active_config=ANY,
            device_key="device_key_from_id",
            label="",
            name="",
            description="",
            organization="",
            tags="",
            properties={},
        )

    def test_update_device_with_all_options(
        self, mock_update_device, mock_get_instance_key, _
    ):
        mock_get_instance_key.return_value = "device_key_from_label"
        properties = '{"key1": "updatedValue", "key2": 456}'
        result = runner.invoke(
            device_app,
            [
                "update",
                "--label",
                "oldDeviceLabel",
                "--new-label",
                "newDeviceLabel",
                "--new-name",
                "UpdatedDeviceName",
                "--description",
                "Updated description",
                "--organization",
                "~updatedOrg",
                "--tags",
                "tagA,tagB",
                "--properties",
                properties,
            ],
        )
        self.assertEqual(result.exit_code, 0)
        mock_update_device.assert_called_once_with(
            active_config=ANY,
            device_key="device_key_from_label",
            label="newDeviceLabel",
            name="UpdatedDeviceName",
            description="Updated description",
            organization="~updatedOrg",
            tags="tagA,tagB",
            properties=json.loads(properties),
        )

    def test_update_device_with_invalid_json_properties(
        self, mock_update_device, mock_get_instance_key, _
    ):
        mock_get_instance_key.return_value = "device_key_from_id"
        result = runner.invoke(
            device_app,
            ["update", "--id", "device123", "--properties", "{key1: value}"],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid JSON format.", result.stdout)
        mock_update_device.assert_not_called()

    def test_update_device_with_id_and_label(
        self, mock_update_device, mock_get_instance_key, _
    ):
        mock_get_instance_key.return_value = "device_key_from_id"
        result = runner.invoke(
            device_app, ["update", "--id", "device123", "--label", "deviceLabel"]
        )
        self.assertEqual(result.exit_code, 0)
        mock_update_device.assert_called_once_with(
            active_config=ANY,
            device_key="device_key_from_id",
            label="",
            name="",
            description="",
            organization="",
            tags="",
            properties={},
        )
