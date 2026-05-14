import re
from pathlib import Path
from unittest import TestCase

from cli.commons.http_auth import get_auth_headers
from cli.commons.http_auth import get_token_auth_headers
from cli.config.models import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel


class TestGetAuthHeaders(TestCase):
    def test_token_profile_returns_x_auth_token_header_set(self):
        # Setup
        config = ProfileConfigModel(
            auth_method=AuthHeaderTypeEnum.TOKEN,
            access_token="legacy-token",
        )
        expected_headers = {
            "X-Auth-Token": "legacy-token",
            "Content-Type": "application/json",
        }
        # Action
        actual_headers = get_auth_headers(config)
        # Expected
        self.assertEqual(actual_headers, expected_headers)

    def test_oauth_profile_returns_bearer_header_set(self):
        # Setup
        config = ProfileConfigModel(
            auth_method=AuthHeaderTypeEnum.OAUTH2,
            access_token="jwt-token",
            refresh_token="r",
            expires_at=1,
            oauth_client_id="ubidots-cli",
        )
        expected_headers = {
            "Authorization": "Bearer jwt-token",
            "Content-Type": "application/json",
        }
        # Action
        actual_headers = get_auth_headers(config)
        # Expected
        self.assertEqual(actual_headers, expected_headers)

    def test_token_helper_returns_static_token_header_set(self):
        # Setup
        expected_headers = {
            "X-Auth-Token": "any-token",
            "Content-Type": "application/json",
        }
        # Action
        actual_headers = get_token_auth_headers("any-token")
        # Expected
        self.assertEqual(actual_headers, expected_headers)


class TestNoHardcodedAuthHeader(TestCase):
    # Rruntime code should not contain "X-Auth-Token" outside the enum definition, the central helper, and the CORS
    # allowlist consumed by UbiFunctions (which is not a CLI auth header).
    EXCLUDED_FILES = {
        "cli/config/enums.py",
        "cli/config/models.py",
        "cli/commons/http_auth.py",
        "cli/functions/engines/models.py",
    }

    def test_no_hardcoded_x_auth_token_in_runtime_code(self) -> None:
        # Setup
        cli_dir = Path(__file__).resolve().parents[2]
        pattern = re.compile(r"X-Auth-Token")
        expected_offenders: list[str] = []
        # Action
        actual_offenders: list[str] = []
        for path in cli_dir.rglob("*.py"):
            relative = path.relative_to(cli_dir.parent).as_posix()
            if "/tests/" in relative:
                continue
            if relative in self.EXCLUDED_FILES:
                continue
            text = path.read_text(encoding="utf-8")
            if pattern.search(text):
                actual_offenders.append(relative)
        # Expected
        self.assertEqual(actual_offenders, expected_offenders)
