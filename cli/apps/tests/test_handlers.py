import unittest

import httpx
import respx

from cli.apps.handlers import get_menu
from cli.apps.handlers import list_apps
from cli.apps.handlers import reset_menu
from cli.apps.handlers import set_menu
from cli.config.models import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel

_APP_KEY = "test-app"
_BASE = "https://industrial.api.ubidots.com/api/-/apps"
_MENU_URL = f"{_BASE}/{_APP_KEY}/menu"
_OAUTH2_CONFIG = ProfileConfigModel(
    auth_method=AuthHeaderTypeEnum.OAUTH2,
    access_token="oauth-token",
    refresh_token="r",
    expires_at=9999999999,
    oauth_client_id="ubidots-cli",
    api_domain="https://industrial.api.ubidots.com",
)
_TOKEN_CONFIG = ProfileConfigModel(
    auth_method=AuthHeaderTypeEnum.TOKEN,
    access_token="legacy-token",
    api_domain="https://industrial.api.ubidots.com",
)


class TestAuthHeaderDispatch(unittest.TestCase):
    @respx.mock
    def test_list_apps_token_sends_x_auth_token(self):
        route = respx.get(_BASE).mock(return_value=httpx.Response(200, json={"results": []}))
        list_apps(_TOKEN_CONFIG)
        self.assertTrue(route.called)
        headers = route.calls.last.request.headers
        self.assertEqual(headers["X-Auth-Token"], "legacy-token")
        self.assertNotIn("Authorization", headers)

    @respx.mock
    def test_list_apps_oauth2_sends_bearer(self):
        route = respx.get(_BASE).mock(return_value=httpx.Response(200, json={"results": []}))
        list_apps(_OAUTH2_CONFIG)
        self.assertTrue(route.called)
        headers = route.calls.last.request.headers
        self.assertEqual(headers["Authorization"], "Bearer oauth-token")
        self.assertNotIn("X-Auth-Token", headers)

    @respx.mock
    def test_get_menu_token_sends_x_auth_token(self):
        route = respx.get(_MENU_URL).mock(return_value=httpx.Response(200, json={}))
        get_menu(_TOKEN_CONFIG, _APP_KEY)
        self.assertTrue(route.called)
        headers = route.calls.last.request.headers
        self.assertEqual(headers["X-Auth-Token"], "legacy-token")
        self.assertNotIn("Authorization", headers)

    @respx.mock
    def test_get_menu_oauth2_sends_bearer(self):
        route = respx.get(_MENU_URL).mock(return_value=httpx.Response(200, json={}))
        get_menu(_OAUTH2_CONFIG, _APP_KEY)
        self.assertTrue(route.called)
        headers = route.calls.last.request.headers
        self.assertEqual(headers["Authorization"], "Bearer oauth-token")
        self.assertNotIn("X-Auth-Token", headers)

    @respx.mock
    def test_set_menu_token_sends_x_auth_token(self):
        route = respx.put(_MENU_URL).mock(return_value=httpx.Response(200, json={}))
        payload = {"menuMode": "default", "menuXml": "<menu/>", "menuAlignment": "left"}
        set_menu(_TOKEN_CONFIG, _APP_KEY, payload)
        self.assertTrue(route.called)
        headers = route.calls.last.request.headers
        self.assertEqual(headers["X-Auth-Token"], "legacy-token")
        self.assertNotIn("Authorization", headers)

    @respx.mock
    def test_set_menu_oauth2_sends_bearer(self):
        route = respx.put(_MENU_URL).mock(return_value=httpx.Response(200, json={}))
        payload = {"menuMode": "default", "menuXml": "<menu/>", "menuAlignment": "left"}
        set_menu(_OAUTH2_CONFIG, _APP_KEY, payload)
        self.assertTrue(route.called)
        headers = route.calls.last.request.headers
        self.assertEqual(headers["Authorization"], "Bearer oauth-token")
        self.assertNotIn("X-Auth-Token", headers)

    @respx.mock
    def test_reset_menu_token_sends_x_auth_token(self):
        route = respx.delete(_MENU_URL).mock(return_value=httpx.Response(204))
        reset_menu(_TOKEN_CONFIG, _APP_KEY)
        self.assertTrue(route.called)
        headers = route.calls.last.request.headers
        self.assertEqual(headers["X-Auth-Token"], "legacy-token")
        self.assertNotIn("Authorization", headers)

    @respx.mock
    def test_reset_menu_oauth2_sends_bearer(self):
        route = respx.delete(_MENU_URL).mock(return_value=httpx.Response(204))
        reset_menu(_OAUTH2_CONFIG, _APP_KEY)
        self.assertTrue(route.called)
        headers = route.calls.last.request.headers
        self.assertEqual(headers["Authorization"], "Bearer oauth-token")
        self.assertNotIn("X-Auth-Token", headers)
