import unittest
from unittest.mock import MagicMock

import httpx
import respx

from cli.config.models import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel
from cli.devices.handlers import add_device
from cli.devices.handlers import delete_device
from cli.devices.handlers import list_devices
from cli.devices.handlers import retrieve_device
from cli.devices.handlers import update_device

_BASE_URL = "https://industrial.api.ubidots.com"
_OAUTH2_CONFIG = ProfileConfigModel(
    auth_method=AuthHeaderTypeEnum.OAUTH2,
    access_token="oauth-token",
    refresh_token="r",
    expires_at=9999999999,
    oauth_client_id="ubidots-cli",
    api_domain=_BASE_URL,
)
_TOKEN_CONFIG = ProfileConfigModel(
    auth_method=AuthHeaderTypeEnum.TOKEN,
    access_token="legacy-token",
    api_domain=_BASE_URL,
)


def _assert_auth_headers(
    test_case: unittest.TestCase,
    request: httpx.Request,
    config: ProfileConfigModel,
) -> None:
    headers = dict(request.headers)
    if config.auth_method == AuthHeaderTypeEnum.TOKEN:
        test_case.assertEqual(
            headers.get("x-auth-token"),
            "legacy-token",
            f"Expected X-Auth-Token header, got: {headers}",
        )
        test_case.assertNotIn(
            "authorization",
            headers,
            f"TOKEN profile must not send Authorization header, got: {headers}",
        )
    else:
        test_case.assertEqual(
            headers.get("authorization"),
            "Bearer oauth-token",
            f"Expected Authorization: Bearer header, got: {headers}",
        )
        test_case.assertNotIn(
            "x-auth-token",
            headers,
            f"OAUTH2 profile must not send X-Auth-Token header, got: {headers}",
        )


class TestAuthHeaderDispatch(unittest.TestCase):
    def _run_list_devices(self, config: ProfileConfigModel) -> None:
        with respx.mock:
            route = respx.get(f"{_BASE_URL}/api/v2.0/devices/").mock(
                return_value=httpx.Response(200, json={"results": [], "count": 0})
            )
            formatter = MagicMock()
            list_devices(
                fields="id,label",
                filter_by=None,
                sort_by=None,
                page_size=None,
                page=None,
                formatter=formatter,
                active_config=config,
            )
            self.assertTrue(route.called)
            _assert_auth_headers(self, route.calls.last.request, config)

    def _run_retrieve_device(self, config: ProfileConfigModel) -> None:
        with respx.mock:
            route = respx.get(f"{_BASE_URL}/api/v2.0/devices/test-device/").mock(
                return_value=httpx.Response(
                    200,
                    json={"id": "abc", "label": "test-device"},
                )
            )
            formatter = MagicMock()
            retrieve_device(
                device_key="test-device",
                fields="id,label",
                formatter=formatter,
                active_config=config,
            )
            self.assertTrue(route.called)
            _assert_auth_headers(self, route.calls.last.request, config)

    def _run_add_device(self, config: ProfileConfigModel) -> None:
        with respx.mock:
            route = respx.post(f"{_BASE_URL}/api/v2.0/devices/").mock(
                return_value=httpx.Response(201, json={"id": "new-id", "label": "new-device"})
            )
            formatter = MagicMock()
            add_device(
                active_config=config,
                formatter=formatter,
                label="new-device",
                name="",
                description="",
                organization="",
                tags="",
                properties="{}",
            )
            self.assertTrue(route.called)
            _assert_auth_headers(self, route.calls.last.request, config)

    def _run_update_device(self, config: ProfileConfigModel) -> None:
        with respx.mock:
            route = respx.patch(f"{_BASE_URL}/api/v2.0/devices/test-device/").mock(
                return_value=httpx.Response(200, json={"id": "abc", "label": "test-device"})
            )
            formatter = MagicMock()
            update_device(
                device_key="test-device",
                active_config=config,
                formatter=formatter,
                label="",
                name="",
                description="",
                organization="",
                tags="",
                properties="{}",
            )
            self.assertTrue(route.called)
            _assert_auth_headers(self, route.calls.last.request, config)

    def _run_delete_device(self, config: ProfileConfigModel) -> None:
        with respx.mock:
            route = respx.delete(f"{_BASE_URL}/api/v2.0/devices/test-device/").mock(return_value=httpx.Response(204))
            formatter = MagicMock()
            delete_device(
                device_key="test-device",
                active_config=config,
                formatter=formatter,
            )
            self.assertTrue(route.called)
            _assert_auth_headers(self, route.calls.last.request, config)

    def test_list_devices_token_auth_header(self):
        self._run_list_devices(_TOKEN_CONFIG)

    def test_list_devices_oauth2_auth_header(self):
        self._run_list_devices(_OAUTH2_CONFIG)

    def test_retrieve_device_token_auth_header(self):
        self._run_retrieve_device(_TOKEN_CONFIG)

    def test_retrieve_device_oauth2_auth_header(self):
        self._run_retrieve_device(_OAUTH2_CONFIG)

    def test_add_device_token_auth_header(self):
        self._run_add_device(_TOKEN_CONFIG)

    def test_add_device_oauth2_auth_header(self):
        self._run_add_device(_OAUTH2_CONFIG)

    def test_update_device_token_auth_header(self):
        self._run_update_device(_TOKEN_CONFIG)

    def test_update_device_oauth2_auth_header(self):
        self._run_update_device(_OAUTH2_CONFIG)

    def test_delete_device_token_auth_header(self):
        self._run_delete_device(_TOKEN_CONFIG)

    def test_delete_device_oauth2_auth_header(self):
        self._run_delete_device(_OAUTH2_CONFIG)
