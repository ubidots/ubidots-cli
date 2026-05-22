import unittest
from unittest.mock import MagicMock

import httpx
import respx

from cli.config.models import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel
from cli.variables import handlers

_API_DOMAIN = "https://industrial.api.ubidots.com"
_TOKEN_PROFILE = ProfileConfigModel(
    auth_method=AuthHeaderTypeEnum.TOKEN,
    access_token="legacy-token",
    api_domain=_API_DOMAIN,
)
_OAUTH2_PROFILE = ProfileConfigModel(
    auth_method=AuthHeaderTypeEnum.OAUTH2,
    access_token="oauth-token",
    refresh_token="r",
    expires_at=9999999999,
    oauth_client_id="ubidots-cli",
    api_domain=_API_DOMAIN,
)
_PROFILES = [_TOKEN_PROFILE, _OAUTH2_PROFILE]


def _assert_auth_headers(
    test_case: unittest.TestCase,
    request: httpx.Request,
    profile: ProfileConfigModel,
) -> None:
    if profile.auth_method == AuthHeaderTypeEnum.TOKEN:
        test_case.assertEqual(request.headers.get("X-Auth-Token"), profile.access_token)
        test_case.assertNotIn("Authorization", request.headers)
    else:
        test_case.assertEqual(request.headers.get("Authorization"), f"Bearer {profile.access_token}")
        test_case.assertNotIn("X-Auth-Token", request.headers)


class TestAuthHeaderDispatch(unittest.TestCase):
    def test_list_variable(self):
        for profile in _PROFILES:
            with self.subTest(auth_method=profile.auth_method), respx.mock:
                route = respx.get(f"{_API_DOMAIN}/api/v2.0/variables/").mock(
                    return_value=httpx.Response(200, json={"results": [], "count": 0})
                )
                formatter = MagicMock()
                handlers.list_variable(
                    fields="id,label",
                    filter=None,
                    sort_by=None,
                    page_size=None,
                    page=None,
                    formatter=formatter,
                    active_config=profile,
                )
                self.assertTrue(route.called)
                _assert_auth_headers(self, route.calls.last.request, profile)

    def test_retrieve_variable(self):
        for profile in _PROFILES:
            with self.subTest(auth_method=profile.auth_method):
                variable_key = "abc123"
                with respx.mock:
                    route = respx.get(f"{_API_DOMAIN}/api/v2.0/variables/{variable_key}/").mock(
                        return_value=httpx.Response(200, json={"id": variable_key})
                    )
                    formatter = MagicMock()
                    handlers.retrieve_variable(
                        variable_key=variable_key,
                        fields="id,label",
                        formatter=formatter,
                        active_config=profile,
                    )
                    self.assertTrue(route.called)
                    _assert_auth_headers(self, route.calls.last.request, profile)

    def test_add_variable(self):
        for profile in _PROFILES:
            with self.subTest(auth_method=profile.auth_method), respx.mock:
                route = respx.post(f"{_API_DOMAIN}/api/v2.0/variables/").mock(
                    return_value=httpx.Response(
                        201,
                        json={
                            "id": "new-var-id",
                            "label": "temp",
                            "device": {"id": "dev-id", "label": "my-device"},
                        },
                    )
                )
                formatter = MagicMock()
                handlers.add_variable(
                    active_config=profile,
                    formatter=formatter,
                    label="temp",
                    name="Temperature",
                    description="",
                    device="dev-id",
                    type="raw",
                    unit="",
                    synthetic_expression="",
                    tags="",
                    properties={},
                    min=None,
                    max=None,
                )
                self.assertTrue(route.called)
                _assert_auth_headers(self, route.calls.last.request, profile)

    def test_update_variable(self):
        for profile in _PROFILES:
            with self.subTest(auth_method=profile.auth_method):
                variable_key = "abc123"
                with respx.mock:
                    route = respx.patch(f"{_API_DOMAIN}/api/v2.0/variables/{variable_key}/").mock(
                        return_value=httpx.Response(200, json={"id": variable_key, "label": "temp"})
                    )
                    formatter = MagicMock()
                    handlers.update_variable(
                        variable_key=variable_key,
                        active_config=profile,
                        formatter=formatter,
                        label="temp",
                        name="Temperature",
                        description="",
                        type="raw",
                        unit="",
                        synthetic_expression="",
                        tags="",
                        properties={},
                        min=None,
                        max=None,
                    )
                    self.assertTrue(route.called)
                    _assert_auth_headers(self, route.calls.last.request, profile)

    def test_delete_variable(self):
        for profile in _PROFILES:
            with self.subTest(auth_method=profile.auth_method):
                variable_key = "abc123"
                with respx.mock:
                    route = respx.delete(f"{_API_DOMAIN}/api/v2.0/variables/{variable_key}/").mock(
                        return_value=httpx.Response(204)
                    )
                    formatter = MagicMock()
                    handlers.delete_variable(
                        variable_key=variable_key,
                        active_config=profile,
                        formatter=formatter,
                    )
                    self.assertTrue(route.called)
                    _assert_auth_headers(self, route.calls.last.request, profile)
