import json
from unittest import TestCase
from unittest.mock import patch

from typer.testing import CliRunner

from cli.commons.enums import DefaultInstanceFieldEnum
from cli.devices.commands import app as device_app
from cli.settings import settings

runner = CliRunner()


@patch("cli.devices.commands.get_instance_key")
@patch("cli.devices.handlers.delete_device")
class TestDeleteCommand(TestCase):
    def test_delete_device_by_id(self, mock_delete_device, mock_get_instance_key):
        # Setup
        mock_get_instance_key.return_value = "device_key_from_id"
        # Action
        result = runner.invoke(device_app, ["delete", "--id", "device123"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="device123", label=None)
        mock_delete_device.assert_called_once_with(device_key="device_key_from_id")

    def test_delete_device_by_label(self, mock_delete_device, mock_get_instance_key):
        # Setup
        mock_get_instance_key.return_value = "device_key_from_label"
        # Action
        result = runner.invoke(device_app, ["delete", "--label", "myDeviceLabel"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id=None, label="myDeviceLabel")
        mock_delete_device.assert_called_once_with(device_key="device_key_from_label")

    def test_delete_device_both_id_and_label(
        self, mock_delete_device, mock_get_instance_key
    ):
        # Setup
        mock_get_instance_key.return_value = "device_key_from_id"
        # Action
        result = runner.invoke(
            device_app, ["delete", "--id", "device123", "--label", "myDeviceLabel"]
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(
            id="device123", label="myDeviceLabel"
        )
        mock_delete_device.assert_called_once_with(device_key="device_key_from_id")


@patch("cli.devices.commands.get_instance_key")
@patch("cli.devices.handlers.retrieve_device")
class TestGetCommand(TestCase):
    def test_get_device_by_id(self, mock_retrieve_device, mock_get_instance_key):
        # Setup
        mock_get_instance_key.return_value = "device_key_from_id"
        # Action
        result = runner.invoke(device_app, ["get", "--id", "device123"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="device123", label=None)
        mock_retrieve_device.assert_called_once_with(
            device_key="device_key_from_id",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_get_device_by_label(self, mock_retrieve_device, mock_get_instance_key):
        # Setup
        mock_get_instance_key.return_value = "device_key_from_label"
        # Action
        result = runner.invoke(device_app, ["get", "--label", "myDeviceLabel"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id=None, label="myDeviceLabel")
        mock_retrieve_device.assert_called_once_with(
            device_key="device_key_from_label",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_get_device_both_id_and_label(
        self, mock_retrieve_device, mock_get_instance_key
    ):
        # Setup
        mock_get_instance_key.return_value = "device_key_from_id"
        # Action
        result = runner.invoke(
            device_app, ["get", "--id", "device123", "--label", "myDeviceLabel"]
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(
            id="device123", label="myDeviceLabel"
        )
        mock_retrieve_device.assert_called_once_with(
            device_key="device_key_from_id",
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_get_device_with_custom_fields(
        self, mock_retrieve_device, mock_get_instance_key
    ):
        # Setup
        mock_get_instance_key.return_value = "device_key_from_id"
        custom_fields = "name,location,status"
        # Action
        result = runner.invoke(
            device_app, ["get", "--id", "device123", "--fields", custom_fields]
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="device123", label=None)
        mock_retrieve_device.assert_called_once_with(
            device_key="device_key_from_id",
            fields=custom_fields,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )


@patch("cli.devices.handlers.list_devices")
class TestListCommand(TestCase):
    def test_list_devices_with_defaults(self, mock_list_devices):
        # Action
        result = runner.invoke(device_app, ["list"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_list_devices.assert_called_once_with(
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            filter=None,
            sort_by=None,
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_devices_with_custom_fields(self, mock_list_devices):
        # Setup
        custom_fields = "name,location,status"
        # Action
        result = runner.invoke(device_app, ["list", "--fields", custom_fields])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_list_devices.assert_called_once_with(
            fields=custom_fields,
            filter=None,
            sort_by=None,
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_devices_with_filter(self, mock_list_devices):
        # Setup
        filter_value = "isActive=true"
        # Action
        result = runner.invoke(device_app, ["list", "--filter", filter_value])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_list_devices.assert_called_once_with(
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            filter=filter_value,
            sort_by=None,
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_devices_with_sort(self, mock_list_devices):
        # Setup
        sort_by_value = "name"
        # Action
        result = runner.invoke(device_app, ["list", "--sort-by", sort_by_value])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_list_devices.assert_called_once_with(
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            filter=None,
            sort_by=sort_by_value,
            page_size=None,
            page=None,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_devices_with_pagination(self, mock_list_devices):
        # Setup
        page_size_value = 10
        page_value = 2
        # Action
        result = runner.invoke(
            device_app,
            ["list", "--page-size", str(page_size_value), "--page", str(page_value)],
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_list_devices.assert_called_once_with(
            fields=DefaultInstanceFieldEnum.get_default_fields(),
            filter=None,
            sort_by=None,
            page_size=page_size_value,
            page=page_value,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )

    def test_list_devices_with_all_options(self, mock_list_devices):
        # Setup
        custom_fields = "name,location,status"
        filter_value = "isActive=true"
        sort_by_value = "created_at"
        page_size_value = 20
        page_value = 1
        # Action
        result = runner.invoke(
            device_app,
            [
                "list",
                "--fields",
                custom_fields,
                "--filter",
                filter_value,
                "--sort-by",
                sort_by_value,
                "--page-size",
                str(page_size_value),
                "--page",
                str(page_value),
            ],
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_list_devices.assert_called_once_with(
            fields=custom_fields,
            filter=filter_value,
            sort_by=sort_by_value,
            page_size=page_size_value,
            page=page_value,
            format=settings.CONFIG.DEFAULT_OUTPUT_FORMAT,
        )


@patch("cli.devices.handlers.add_device")
class TestAddCommand(TestCase):
    def test_add_device_with_minimum_arguments(self, mock_add_device):
        # Action
        result = runner.invoke(device_app, ["add", "deviceLabel"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_add_device.assert_called_once_with(
            label="deviceLabel",
            name="",
            description="",
            organization="",
            tags="",
            properties={},
        )

    def test_add_device_with_all_options(self, mock_add_device):
        # Setup
        label = "deviceLabel"
        name = "DeviceName"
        description = "Test device description"
        organization = "~testOrg"
        tags = "tag1,tag2"
        properties = '{"key1": "value1", "key2": 123}'
        # Action
        result = runner.invoke(
            device_app,
            [
                "add",
                label,
                "--name",
                name,
                "--description",
                description,
                "--organization",
                organization,
                "--tags",
                tags,
                "--properties",
                properties,
            ],
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_add_device.assert_called_once_with(
            label=label,
            name=name,
            description=description,
            organization=organization,
            tags=tags,
            properties=json.loads(properties),
        )

    def test_add_device_with_invalid_json_properties(self, mock_add_device):
        # Setup
        label = "deviceLabel"
        invalid_properties = "{key1: value1, key2: 123}"  # Missing quotes
        # Action
        result = runner.invoke(
            device_app, ["add", label, "--properties", invalid_properties]
        )
        # Expected
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid JSON format.", result.stdout)
        mock_add_device.assert_not_called()


@patch("cli.devices.commands.get_instance_key")
@patch("cli.devices.handlers.update_device")
class TestUpdateCommand(TestCase):
    def test_update_device_by_id_with_minimum_arguments(
        self, mock_update_device, mock_get_instance_key
    ):
        # Setup
        mock_get_instance_key.return_value = "device_key_from_id"
        # Action
        result = runner.invoke(device_app, ["update", "--id", "device123"])
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id="device123", label=None)
        mock_update_device.assert_called_once_with(
            device_key="device_key_from_id",
            label="",
            name="",
            description="",
            organization="",
            tags="",
            properties={},
        )

    def test_update_device_with_all_options(
        self, mock_update_device, mock_get_instance_key
    ):
        # Setup
        mock_get_instance_key.return_value = "device_key_from_label"
        new_label = "newDeviceLabel"
        new_name = "UpdatedDeviceName"
        description = "Updated description"
        organization = "~updatedOrg"
        tags = "tagA,tagB"
        properties = '{"key1": "updatedValue", "key2": 456}'
        # Action
        result = runner.invoke(
            device_app,
            [
                "update",
                "--label",
                "oldDeviceLabel",
                "--new-label",
                new_label,
                "--new-name",
                new_name,
                "--description",
                description,
                "--organization",
                organization,
                "--tags",
                tags,
                "--properties",
                properties,
            ],
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(id=None, label="oldDeviceLabel")
        mock_update_device.assert_called_once_with(
            device_key="device_key_from_label",
            label=new_label,
            name=new_name,
            description=description,
            organization=organization,
            tags=tags,
            properties=json.loads(properties),
        )

    def test_update_device_with_invalid_json_properties(
        self, mock_update_device, mock_get_instance_key
    ):
        # Setup
        mock_get_instance_key.return_value = "device_key_from_id"
        invalid_properties = "{key1: updatedValue, key2: 456}"  # Invalid JSON
        # Action
        result = runner.invoke(
            device_app,
            ["update", "--id", "device123", "--properties", invalid_properties],
        )
        # Expected
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid JSON format.", result.stdout)
        mock_update_device.assert_not_called()

    def test_update_device_with_id_and_label(
        self, mock_update_device, mock_get_instance_key
    ):
        # Setup
        mock_get_instance_key.return_value = "device_key_from_id"
        # Action
        result = runner.invoke(
            device_app, ["update", "--id", "device123", "--label", "deviceLabel"]
        )
        # Expected
        self.assertEqual(result.exit_code, 0)
        mock_get_instance_key.assert_called_once_with(
            id="device123", label="deviceLabel"
        )
        mock_update_device.assert_called_once_with(
            device_key="device_key_from_id",
            label="",
            name="",
            description="",
            organization="",
            tags="",
            properties={},
        )
