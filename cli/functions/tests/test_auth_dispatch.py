import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx
import respx

from cli.config.enums import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel
from cli.functions import executor

_API_DOMAIN = "https://industrial.api.ubidots.com"
_FUNCTION_ID = "abc123def456abc123def456"
_FUNCTION_LABEL = "my-func"
_FUNCTION_DETAIL = {
    "id": _FUNCTION_ID,
    "label": _FUNCTION_LABEL,
    "name": "my-func",
    "createdAt": "2024-01-01T00:00:00Z",
    "serverless": {
        "runtime": "python3.11:lite",
        "isRawFunction": False,
        "timeout": 30,
        "authToken": {},
        "params": {},
    },
    "triggers": {
        "httpMethods": ["GET"],
        "httpHasCors": False,
        "httpIsInsecure": False,
        "httpEnabled": True,
        "schedulerCron": "",
        "schedulerEnabled": False,
    },
}
_INVOKE_RESPONSE = {
    "response": {"result": {"status": "ok"}},
    "logs": [],
    "start": 0,
    "end": 10,
}
_LIST_RESPONSE = {"results": [_FUNCTION_DETAIL]}
_LOGS_LIST_RESPONSE = {"results": [{"activationId": "act-001"}]}
_LOG_DETAIL_RESPONSE = {"logs": ["log line 1"], "_activation_id": "act-001"}
_OAUTH2_PROFILE = ProfileConfigModel(
    auth_method=AuthHeaderTypeEnum.OAUTH2,
    access_token="oauth-token",
    refresh_token="r",
    expires_at=9999999999,
    oauth_client_id="ubidots-cli",
    api_domain=_API_DOMAIN,
)
_TOKEN_PROFILE = ProfileConfigModel(
    auth_method=AuthHeaderTypeEnum.TOKEN,
    access_token="legacy-token",
    api_domain=_API_DOMAIN,
)
_PROFILES = [_TOKEN_PROFILE, _OAUTH2_PROFILE]


def _assert_auth_headers(test_case: unittest.TestCase, request: httpx.Request, profile: ProfileConfigModel):
    headers = dict(request.headers)
    if profile.auth_method == AuthHeaderTypeEnum.TOKEN:
        test_case.assertEqual(
            headers.get("x-auth-token"),
            "legacy-token",
            "TOKEN: X-Auth-Token header missing or wrong",
        )
        test_case.assertNotIn("authorization", headers, "TOKEN: Authorization header must not be present")
    else:
        auth = headers.get("authorization", "")
        test_case.assertTrue(
            auth.startswith("Bearer "),
            f"OAUTH2: Authorization header missing/wrong: {auth}",
        )
        test_case.assertEqual(auth, "Bearer oauth-token")
        test_case.assertNotIn("x-auth-token", headers, "OAUTH2: X-Auth-Token header must not be present")


class TestAuthHeaderDispatch(unittest.TestCase):
    def _run_list_functions(self, profile: ProfileConfigModel):
        base_url = f"{_API_DOMAIN}/api/-/functions"
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(url__startswith=base_url).mock(return_value=httpx.Response(200, json=_LIST_RESPONSE))
            formatter = MagicMock()
            formatter.emit_results = MagicMock()
            with patch("cli.functions.pipelines.get_configuration", return_value=profile):
                executor.list_functions(
                    profile="",
                    fields="id,label",
                    filter=None,
                    sort_by=None,
                    page_size=None,
                    page=None,
                    formatter=formatter,
                )
            self.assertTrue(route.called, "list_functions: HTTP GET was not called")
            _assert_auth_headers(self, route.calls.last.request, profile)

    def test_list_functions_token(self):
        self._run_list_functions(_TOKEN_PROFILE)

    def test_list_functions_oauth2(self):
        self._run_list_functions(_OAUTH2_PROFILE)

    def _run_get_function(self, profile: ProfileConfigModel):
        detail_url = f"{_API_DOMAIN}/api/-/functions/{_FUNCTION_ID}"
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(detail_url).mock(return_value=httpx.Response(200, json=_FUNCTION_DETAIL))
            formatter = MagicMock()
            formatter.emit_results = MagicMock()
            with patch("cli.functions.pipelines.get_configuration", return_value=profile):
                executor.get_function(
                    function_key=_FUNCTION_ID,
                    profile="",
                    verbose=False,
                    formatter=formatter,
                    fields="id,label",
                )
            self.assertTrue(route.called, "get_function: HTTP GET was not called")
            _assert_auth_headers(self, route.calls.last.request, profile)

    def test_get_function_token(self):
        self._run_get_function(_TOKEN_PROFILE)

    def test_get_function_oauth2(self):
        self._run_get_function(_OAUTH2_PROFILE)

    def _run_delete_function(self, profile: ProfileConfigModel):
        detail_url = f"{_API_DOMAIN}/api/-/functions/{_FUNCTION_ID}"
        with respx.mock(assert_all_called=False) as mock:
            route = mock.delete(detail_url).mock(return_value=httpx.Response(200, json={}))
            formatter = MagicMock()
            with patch("cli.functions.pipelines.get_configuration", return_value=profile):
                executor.delete_function(
                    function_key=_FUNCTION_ID,
                    profile="",
                    confirm=True,
                    verbose=False,
                    formatter=formatter,
                )
            self.assertTrue(route.called, "delete_function: HTTP DELETE was not called")
            _assert_auth_headers(self, route.calls.last.request, profile)

    def test_delete_function_token(self):
        self._run_delete_function(_TOKEN_PROFILE)

    def test_delete_function_oauth2(self):
        self._run_delete_function(_OAUTH2_PROFILE)

    def _run_add_function(self, profile: ProfileConfigModel):
        base_url = f"{_API_DOMAIN}/api/-/functions"
        zip_url = f"{_API_DOMAIN}/api/-/functions/{_FUNCTION_ID}/zip-file"
        with respx.mock(assert_all_called=False) as mock:
            post_route = mock.post(base_url).mock(
                return_value=httpx.Response(201, json={"id": _FUNCTION_ID, "label": _FUNCTION_LABEL})
            )
            zip_route = mock.post(zip_url).mock(return_value=httpx.Response(200, json={}))
            formatter = MagicMock()
            with (
                patch("cli.functions.pipelines.get_configuration", return_value=profile),
                patch("builtins.open", unittest.mock.mock_open(read_data=b"")),
            ):
                executor.add_function(
                    profile="",
                    name="my-func",
                    label="my-func",
                    runtime="python3.11:lite",
                    is_raw=False,
                    http_methods=["GET"],
                    http_has_cors=False,
                    scheduler_cron="",
                    timeout=30,
                    environment="[]",
                    formatter=formatter,
                )
            self.assertTrue(post_route.called, "add_function: HTTP POST was not called")
            self.assertTrue(zip_route.called, "add_function: HTTP POST to zip-file was not called")
            _assert_auth_headers(self, post_route.calls.last.request, profile)
            _assert_auth_headers(self, zip_route.calls.last.request, profile)
            zip_content_type = zip_route.calls.last.request.headers.get("content-type", "")
            self.assertIn("multipart/form-data", zip_content_type, "zip upload must use multipart/form-data")
            self.assertNotIn(
                "application/json",
                zip_content_type,
                "zip upload must not send Content-Type: application/json",
            )

    def test_add_function_token(self):
        self._run_add_function(_TOKEN_PROFILE)

    def test_add_function_oauth2(self):
        self._run_add_function(_OAUTH2_PROFILE)

    def _run_update_function(self, profile: ProfileConfigModel):
        detail_url = f"{_API_DOMAIN}/api/-/functions/{_FUNCTION_ID}"
        with respx.mock(assert_all_called=False) as mock:
            get_route = mock.get(detail_url).mock(return_value=httpx.Response(200, json=_FUNCTION_DETAIL))
            patch_route = mock.patch(detail_url).mock(return_value=httpx.Response(200, json=_FUNCTION_DETAIL))
            formatter = MagicMock()
            with patch("cli.functions.pipelines.get_configuration", return_value=profile):
                executor.update_function(
                    function_key=_FUNCTION_ID,
                    profile="",
                    name="new-name",
                    label="new-label",
                    http_methods=None,
                    http_has_cors=None,
                    scheduler_cron=None,
                    runtime=None,
                    is_raw=None,
                    timeout=None,
                    environment=None,
                    formatter=formatter,
                )
            self.assertTrue(get_route.called, "update_function: HTTP GET was not called")
            self.assertTrue(patch_route.called, "update_function: HTTP PATCH was not called")
            _assert_auth_headers(self, get_route.calls.last.request, profile)
            _assert_auth_headers(self, patch_route.calls.last.request, profile)

    def test_update_function_token(self):
        self._run_update_function(_TOKEN_PROFILE)

    def test_update_function_oauth2(self):
        self._run_update_function(_OAUTH2_PROFILE)

    def _run_run_function(self, profile: ProfileConfigModel):
        invoke_url = f"{_API_DOMAIN}/api/-/functions/{_FUNCTION_ID}/_/invoke/"
        with respx.mock(assert_all_called=False) as mock:
            route = mock.post(invoke_url).mock(return_value=httpx.Response(200, json=_INVOKE_RESPONSE))
            formatter = MagicMock()
            with patch("cli.functions.pipelines.get_configuration", return_value=profile):
                executor.run_function(
                    function_key=_FUNCTION_ID,
                    payload={},
                    profile="",
                    verbose=False,
                    formatter=formatter,
                )
            self.assertTrue(route.called, "run_function: HTTP POST was not called")
            _assert_auth_headers(self, route.calls.last.request, profile)

    def test_run_function_token(self):
        self._run_run_function(_TOKEN_PROFILE)

    def test_run_function_oauth2(self):
        self._run_run_function(_OAUTH2_PROFILE)

    def _run_logs_function_remote(self, profile: ProfileConfigModel):
        logs_url = f"{_API_DOMAIN}/api/-/functions/{_FUNCTION_ID}/logs"
        log_detail_url = f"{_API_DOMAIN}/api/-/functions/{_FUNCTION_ID}/logs/act-001"
        with respx.mock(assert_all_called=False) as mock:
            logs_route = mock.get(logs_url).mock(return_value=httpx.Response(200, json=_LOGS_LIST_RESPONSE))
            detail_route = mock.get(log_detail_url).mock(return_value=httpx.Response(200, json=_LOG_DETAIL_RESPONSE))
            formatter = MagicMock()
            with patch("cli.functions.pipelines.get_configuration", return_value=profile):
                executor.logs_function(
                    tail=1,
                    follow=False,
                    profile="",
                    remote=True,
                    verbose=False,
                    formatter=formatter,
                    function_key=_FUNCTION_ID,
                )
            self.assertTrue(logs_route.called, "logs_function: HTTP GET (logs list) was not called")
            _assert_auth_headers(self, logs_route.calls.last.request, profile)
            self.assertTrue(
                detail_route.called,
                "logs_function: HTTP GET (log detail) was not called",
            )
            _assert_auth_headers(self, detail_route.calls.last.request, profile)

    def test_logs_function_remote_token(self):
        self._run_logs_function_remote(_TOKEN_PROFILE)

    def test_logs_function_remote_oauth2(self):
        self._run_logs_function_remote(_OAUTH2_PROFILE)
