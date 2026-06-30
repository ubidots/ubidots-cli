import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import respx

from cli.commons.endpoint import build_endpoint
from cli.config.models import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel
from cli.pages.constants import PAGE_API_ROUTES
from cli.pages.executor import delete_page_from_cloud_platform
from cli.pages.executor import get_page_from_cloud_platform
from cli.pages.executor import list_pages_from_cloud_platform
from cli.pages.handlers import add_page
from cli.pages.handlers import update_page
from cli.pages.handlers import upload_page_code

_BASE_URL = "https://industrial.api.ubidots.com"
_PAGE_KEY = "abc123"
_PATCH_GET_CONFIG = "cli.pages.pipelines.dev_scaffold.get_configuration"
_TOKEN_CONFIG = ProfileConfigModel(
    auth_method=AuthHeaderTypeEnum.TOKEN,
    access_token="legacy-token",
    api_domain=_BASE_URL,
)
_OAUTH2_CONFIG = ProfileConfigModel(
    auth_method=AuthHeaderTypeEnum.OAUTH2,
    access_token="oauth-token",
    refresh_token="r",
    expires_at=9999999999,
    oauth_client_id="ubidots-cli",
    api_domain=_BASE_URL,
)
_PROFILES = [
    ("token", _TOKEN_CONFIG, "X-Auth-Token", "legacy-token"),
    ("oauth2", _OAUTH2_CONFIG, "Authorization", "Bearer oauth-token"),
]


class TestAuthHeaderDispatch(unittest.TestCase):
    def test_list_token(self):
        with patch(_PATCH_GET_CONFIG, return_value=_TOKEN_CONFIG), respx.mock:
            route = respx.get(url__startswith=f"{_BASE_URL}/api/v2.0/pages/").mock(
                return_value=httpx.Response(200, json={"results": []})
            )
            list_pages_from_cloud_platform(
                profile="",
                fields=None,
                sort_by=None,
                page_size=None,
                page=None,
                formatter=MagicMock(),
            )
            self.assertTrue(route.called)
            req = route.calls.last.request
            self.assertEqual(req.headers.get("X-Auth-Token"), "legacy-token")
            self.assertNotIn("Authorization", req.headers)

    def test_list_oauth2(self):
        with patch(_PATCH_GET_CONFIG, return_value=_OAUTH2_CONFIG), respx.mock:
            route = respx.get(url__startswith=f"{_BASE_URL}/api/v2.0/pages/").mock(
                return_value=httpx.Response(200, json={"results": []})
            )
            list_pages_from_cloud_platform(
                profile="",
                fields=None,
                sort_by=None,
                page_size=None,
                page=None,
                formatter=MagicMock(),
            )
            self.assertTrue(route.called)
            req = route.calls.last.request
            self.assertEqual(req.headers.get("Authorization"), "Bearer oauth-token")
            self.assertNotIn("X-Auth-Token", req.headers)

    def test_get_token(self):
        with patch(_PATCH_GET_CONFIG, return_value=_TOKEN_CONFIG), respx.mock:
            route = respx.get(f"{_BASE_URL}/api/v2.0/pages/{_PAGE_KEY}/").mock(
                return_value=httpx.Response(200, json={"id": _PAGE_KEY})
            )
            get_page_from_cloud_platform(
                page_key=_PAGE_KEY,
                profile="",
                verbose=False,
                formatter=MagicMock(),
                fields=None,
            )
            self.assertTrue(route.called)
            req = route.calls.last.request
            self.assertEqual(req.headers.get("X-Auth-Token"), "legacy-token")
            self.assertNotIn("Authorization", req.headers)

    def test_get_oauth2(self):
        with patch(_PATCH_GET_CONFIG, return_value=_OAUTH2_CONFIG), respx.mock:
            route = respx.get(f"{_BASE_URL}/api/v2.0/pages/{_PAGE_KEY}/").mock(
                return_value=httpx.Response(200, json={"id": _PAGE_KEY})
            )
            get_page_from_cloud_platform(
                page_key=_PAGE_KEY,
                profile="",
                verbose=False,
                formatter=MagicMock(),
                fields=None,
            )
            self.assertTrue(route.called)
            req = route.calls.last.request
            self.assertEqual(req.headers.get("Authorization"), "Bearer oauth-token")
            self.assertNotIn("X-Auth-Token", req.headers)

    @respx.mock
    def test_add_token(self):
        route = respx.post(f"{_BASE_URL}/api/v2.0/pages/").mock(
            return_value=httpx.Response(201, json={"id": _PAGE_KEY, "label": "my_page"})
        )
        add_page(active_config=_TOKEN_CONFIG, name="My Page", label="my_page")
        self.assertTrue(route.called)
        req = route.calls.last.request
        self.assertEqual(req.headers.get("X-Auth-Token"), "legacy-token")
        self.assertNotIn("Authorization", req.headers)

    @respx.mock
    def test_add_oauth2(self):
        route = respx.post(f"{_BASE_URL}/api/v2.0/pages/").mock(
            return_value=httpx.Response(201, json={"id": _PAGE_KEY, "label": "my_page"})
        )
        add_page(active_config=_OAUTH2_CONFIG, name="My Page", label="my_page")
        self.assertTrue(route.called)
        req = route.calls.last.request
        self.assertEqual(req.headers.get("Authorization"), "Bearer oauth-token")
        self.assertNotIn("X-Auth-Token", req.headers)

    def test_delete_token(self):
        with patch(_PATCH_GET_CONFIG, return_value=_TOKEN_CONFIG), respx.mock:
            route = respx.delete(f"{_BASE_URL}/api/v2.0/pages/{_PAGE_KEY}/").mock(return_value=httpx.Response(204))
            delete_page_from_cloud_platform(
                page_key=_PAGE_KEY,
                profile="",
                confirm=True,
                verbose=False,
                formatter=MagicMock(),
            )
            self.assertTrue(route.called)
            req = route.calls.last.request
            self.assertEqual(req.headers.get("X-Auth-Token"), "legacy-token")
            self.assertNotIn("Authorization", req.headers)

    def test_delete_oauth2(self):
        with patch(_PATCH_GET_CONFIG, return_value=_OAUTH2_CONFIG), respx.mock:
            route = respx.delete(f"{_BASE_URL}/api/v2.0/pages/{_PAGE_KEY}/").mock(return_value=httpx.Response(204))
            delete_page_from_cloud_platform(
                page_key=_PAGE_KEY,
                profile="",
                confirm=True,
                verbose=False,
                formatter=MagicMock(),
            )
            self.assertTrue(route.called)
            req = route.calls.last.request
            self.assertEqual(req.headers.get("Authorization"), "Bearer oauth-token")
            self.assertNotIn("X-Auth-Token", req.headers)

    @respx.mock
    def test_update_token(self):
        route = respx.patch(f"{_BASE_URL}/api/v2.0/pages/{_PAGE_KEY}/").mock(
            return_value=httpx.Response(200, json={"id": _PAGE_KEY})
        )
        update_page(active_config=_TOKEN_CONFIG, page_key=_PAGE_KEY, name="New Name")
        self.assertTrue(route.called)
        req = route.calls.last.request
        self.assertEqual(req.headers.get("X-Auth-Token"), "legacy-token")
        self.assertNotIn("Authorization", req.headers)

    @respx.mock
    def test_update_oauth2(self):
        route = respx.patch(f"{_BASE_URL}/api/v2.0/pages/{_PAGE_KEY}/").mock(
            return_value=httpx.Response(200, json={"id": _PAGE_KEY})
        )
        update_page(active_config=_OAUTH2_CONFIG, page_key=_PAGE_KEY, name="New Name")
        self.assertTrue(route.called)
        req = route.calls.last.request
        self.assertEqual(req.headers.get("Authorization"), "Bearer oauth-token")
        self.assertNotIn("X-Auth-Token", req.headers)

    @respx.mock
    def test_push_token(self):
        url = f"{_BASE_URL}/api/v2.0/pages/{_PAGE_KEY}/code/"
        route = respx.post(url).mock(return_value=httpx.Response(200))
        _, headers = build_endpoint(
            route=PAGE_API_ROUTES["code"],
            page_key=_PAGE_KEY,
            active_config=_TOKEN_CONFIG,
        )
        upload_page_code(url=url, headers=headers, zip_file=b"zip", page_name="page")
        self.assertTrue(route.called)
        req = route.calls.last.request
        self.assertEqual(req.headers.get("X-Auth-Token"), "legacy-token")
        self.assertNotIn("Authorization", req.headers)

    @respx.mock
    def test_push_oauth2(self):
        url = f"{_BASE_URL}/api/v2.0/pages/{_PAGE_KEY}/code/"
        route = respx.post(url).mock(return_value=httpx.Response(200))
        _, headers = build_endpoint(
            route=PAGE_API_ROUTES["code"],
            page_key=_PAGE_KEY,
            active_config=_OAUTH2_CONFIG,
        )
        upload_page_code(url=url, headers=headers, zip_file=b"zip", page_name="page")
        self.assertTrue(route.called)
        req = route.calls.last.request
        self.assertEqual(req.headers.get("Authorization"), "Bearer oauth-token")
        self.assertNotIn("X-Auth-Token", req.headers)


class TestUploadPageCode(unittest.TestCase):
    @respx.mock
    def test_sends_zip_file(self):
        route = respx.post("http://api/pages/abc123/code").mock(return_value=httpx.Response(200))

        upload_page_code("http://api/pages/abc123/code", {}, b"zipdata", "my_page")
        self.assertTrue(route.called)
        request_content = route.calls.last.request.content.decode()
        self.assertIn("my_page.zip", request_content)
        self.assertIn("application/zip", request_content)

    @respx.mock
    def test_does_not_send_json_content_type(self):
        route = respx.post("http://api/pages/abc123/code").mock(return_value=httpx.Response(200))

        headers = {"X-Auth-Token": "token", "Content-Type": "application/json"}
        upload_page_code("http://api/pages/abc123/code", headers, b"zipdata", "my_page")

        self.assertTrue(route.called)
        content_type = route.calls.last.request.headers.get("content-type", "")
        self.assertIn("multipart/form-data", content_type, "upload must use multipart/form-data")
        self.assertNotIn("application/json", content_type, "upload must not send Content-Type: application/json")
