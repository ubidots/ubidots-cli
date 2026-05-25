import sys
from io import StringIO
from unittest import TestCase
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import patch

from typer.testing import CliRunner

from cli.organizations.commands import app as organizations_app

runner = CliRunner()


# ---------------------------------------------------------------------------
# organizations list
# ---------------------------------------------------------------------------


@patch("cli.organizations.commands.get_configuration", return_value=MagicMock())
@patch("cli.organizations.handlers.list_organizations")
class TestListCommand(TestCase):
    def test_list_with_defaults(self, mock_list, _):
        result = runner.invoke(organizations_app, ["list"])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_list.assert_called_once_with(
            active_config=ANY,
            fields="id,name,label,createdAt",
            page_size=None,
            page=None,
            formatter=ANY,
        )

    def test_list_with_format_json(self, mock_list, _):
        result = runner.invoke(organizations_app, ["list", "--format", "json"])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_list.assert_called_once()

    def test_list_with_pagination(self, mock_list, _):
        result = runner.invoke(organizations_app, ["list", "--page", "2", "--page-size", "5"])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_list.assert_called_once_with(
            active_config=ANY,
            fields=ANY,
            page_size=5,
            page=2,
            formatter=ANY,
        )

    def test_list_with_invalid_page_size_string(self, mock_list, _):
        result = runner.invoke(organizations_app, ["list", "--page-size", "abc"])
        self.assertNotEqual(result.exit_code, 0)
        mock_list.assert_not_called()

    def test_list_with_custom_fields(self, mock_list, _):
        result = runner.invoke(organizations_app, ["list", "--fields", "id,name"])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_list.assert_called_once_with(
            active_config=ANY,
            fields="id,name",
            page_size=None,
            page=None,
            formatter=ANY,
        )


# ---------------------------------------------------------------------------
# organizations get
# ---------------------------------------------------------------------------


@patch("cli.organizations.commands.get_configuration", return_value=MagicMock())
@patch("cli.organizations.handlers.get_organization")
class TestGetCommand(TestCase):
    def test_get_by_id(self, mock_get, _):
        result = runner.invoke(organizations_app, ["get", "--id", "org123"])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_get.assert_called_once_with(
            org_id="org123",
            active_config=ANY,
            formatter=ANY,
        )

    def test_get_by_label(self, mock_get, _):
        result = runner.invoke(organizations_app, ["get", "--label", "acme"])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_get.assert_called_once_with(
            org_id="~acme",
            active_config=ANY,
            formatter=ANY,
        )

    def test_get_both_id_and_label_is_error(self, mock_get, _):
        result = runner.invoke(organizations_app, ["get", "--id", "org123", "--label", "acme"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("mutually exclusive", result.output)
        mock_get.assert_not_called()

    def test_get_no_flags_is_error(self, mock_get, _):
        result = runner.invoke(organizations_app, ["get"])
        self.assertEqual(result.exit_code, 1)
        mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# organizations create
# ---------------------------------------------------------------------------


@patch("cli.organizations.commands.get_configuration", return_value=MagicMock())
@patch("cli.organizations.handlers.create_organization")
class TestCreateCommand(TestCase):
    def test_create_with_name(self, mock_create, _):
        result = runner.invoke(organizations_app, ["create", "--name", "Acme"])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_create.assert_called_once_with(
            name="Acme",
            active_config=ANY,
            formatter=ANY,
        )

    def test_create_without_name_is_error(self, mock_create, _):
        result = runner.invoke(organizations_app, ["create"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("--name is required", result.output)
        mock_create.assert_not_called()


# ---------------------------------------------------------------------------
# organizations update
# ---------------------------------------------------------------------------


@patch("cli.organizations.commands.get_configuration", return_value=MagicMock())
@patch("cli.organizations.handlers.update_organization")
class TestUpdateCommand(TestCase):
    def test_update_with_name(self, mock_update, _):
        result = runner.invoke(organizations_app, ["update", "--id", "org123", "--name", "New Name"])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_update.assert_called_once_with(
            org_id="org123",
            name="New Name",
            active_config=ANY,
            formatter=ANY,
        )

    def test_update_without_fields_is_error(self, mock_update, _):
        result = runner.invoke(organizations_app, ["update", "--id", "org123"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("at least one field to update must be provided", result.output)
        mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# organizations delete
# ---------------------------------------------------------------------------


@patch("cli.organizations.commands.get_configuration", return_value=MagicMock())
@patch("cli.organizations.handlers.delete_organization")
class TestDeleteCommand(TestCase):
    def test_delete_with_yes_flag(self, mock_delete, _):
        result = runner.invoke(organizations_app, ["delete", "--id", "org123", "--yes"])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_delete.assert_called_once_with(
            org_id="org123",
            active_config=ANY,
            formatter=ANY,
        )

    def test_delete_interactive_confirm_yes(self, mock_delete, _):
        with patch("cli.organizations.commands.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = True
            result = runner.invoke(organizations_app, ["delete", "--id", "org123"], input="y\n")
        self.assertEqual(result.exit_code, 0, result.output)
        mock_delete.assert_called_once()

    def test_delete_interactive_confirm_no(self, mock_delete, _):
        with patch("cli.organizations.commands.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = True
            result = runner.invoke(organizations_app, ["delete", "--id", "org123"], input="n\n")
        self.assertEqual(result.exit_code, 0)
        mock_delete.assert_not_called()

    def test_delete_non_interactive_without_yes_is_error(self, mock_delete, _):
        # CliRunner stdin.isatty() is always False -- command should exit 1
        result = runner.invoke(organizations_app, ["delete", "--id", "org123"])
        self.assertEqual(result.exit_code, 1)
        mock_delete.assert_not_called()


# ---------------------------------------------------------------------------
# organizations users list
# ---------------------------------------------------------------------------


@patch("cli.organizations.commands.get_configuration", return_value=MagicMock())
@patch("cli.organizations.handlers.list_organization_users")
class TestUsersListCommand(TestCase):
    def test_users_list(self, mock_list_users, _):
        result = runner.invoke(organizations_app, ["users", "list", "--id", "org123"])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_list_users.assert_called_once_with(
            org_id="org123",
            active_config=ANY,
            formatter=ANY,
        )

    def test_users_list_with_format_json(self, mock_list_users, _):
        result = runner.invoke(organizations_app, ["users", "list", "--id", "org123", "--format", "json"])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_list_users.assert_called_once()


# ---------------------------------------------------------------------------
# organizations users add
# ---------------------------------------------------------------------------


@patch("cli.organizations.commands.get_configuration", return_value=MagicMock())
@patch("cli.organizations.handlers.add_organization_user")
class TestUsersAddCommand(TestCase):
    def test_users_add(self, mock_add_user, _):
        result = runner.invoke(
            organizations_app, ["users", "add", "--id", "org123", "--user", "user456"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        mock_add_user.assert_called_once_with(
            org_id="org123",
            user_id="user456",
            active_config=ANY,
            formatter=ANY,
        )
