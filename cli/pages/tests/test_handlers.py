import json
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx

from cli.commons.enums import OutputFormatFieldsEnum
from cli.pages.handlers import delete_page
from cli.pages.handlers import download_page_code
from cli.pages.handlers import list_pages
from cli.pages.handlers import retrieve_page
from cli.pages.handlers import upload_page_code


def _make_response(status_code: int, body: dict | None = None) -> MagicMock:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = body or {}
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=response,
        )
    else:
        response.raise_for_status.return_value = None
    return response


class TestListPages(unittest.TestCase):

    @patch("cli.pages.handlers.httpx.get")
    @patch("cli.pages.handlers.typer.echo")
    def test_json_format_echoes_results(self, mock_echo, mock_get):
        pages = [{"id": "1", "label": "page-one"}]
        mock_get.return_value = _make_response(200, {"results": pages})

        list_pages("http://api/pages", {}, OutputFormatFieldsEnum.JSON)

        mock_echo.assert_called_once_with(json.dumps(pages))

    @patch("cli.pages.handlers.httpx.get")
    @patch("cli.pages.handlers.print_colored_table")
    def test_table_format_calls_print_colored_table(self, mock_table, mock_get):
        pages = [{"id": "1", "label": "page-one"}]
        mock_get.return_value = _make_response(200, {"results": pages})

        list_pages("http://api/pages", {}, OutputFormatFieldsEnum.TABLE)

        mock_table.assert_called_once_with(results=pages)

    @patch("cli.pages.handlers.httpx.get")
    @patch("cli.pages.handlers.typer.echo")
    def test_missing_results_key_defaults_to_empty_list(self, mock_echo, mock_get):
        mock_get.return_value = _make_response(200, {"count": 0})

        list_pages("http://api/pages", {}, OutputFormatFieldsEnum.JSON)

        mock_echo.assert_called_once_with(json.dumps([]))

    @patch("cli.pages.handlers.httpx.get")
    def test_http_error_raises(self, mock_get):
        mock_get.return_value = _make_response(500)

        with self.assertRaises(httpx.HTTPStatusError):
            list_pages("http://api/pages", {}, OutputFormatFieldsEnum.JSON)

    @patch("cli.pages.handlers.httpx.get")
    def test_http_400_raises(self, mock_get):
        mock_get.return_value = _make_response(400, {"detail": "bad request"})

        with self.assertRaises(httpx.HTTPStatusError):
            list_pages("http://api/pages", {}, OutputFormatFieldsEnum.JSON)


class TestRetrievePage(unittest.TestCase):

    @patch("cli.pages.handlers.httpx.get")
    @patch("cli.pages.handlers.typer.echo")
    def test_json_format_echoes_page(self, mock_echo, mock_get):
        page = {"id": "abc123", "label": "my-page"}
        mock_get.return_value = _make_response(200, page)

        retrieve_page("http://api/pages/abc123", {}, OutputFormatFieldsEnum.JSON)

        mock_echo.assert_called_once_with(json.dumps(page))

    @patch("cli.pages.handlers.httpx.get")
    @patch("cli.pages.handlers.print_colored_table")
    def test_table_format_calls_print_colored_table(self, mock_table, mock_get):
        page = {"id": "abc123", "label": "my-page"}
        mock_get.return_value = _make_response(200, page)

        retrieve_page("http://api/pages/abc123", {}, OutputFormatFieldsEnum.TABLE)

        mock_table.assert_called_once_with(results=[page])

    @patch("cli.pages.handlers.httpx.get")
    def test_returns_response(self, mock_get):
        mock_response = _make_response(200, {"id": "abc123"})
        mock_get.return_value = mock_response

        result = retrieve_page(
            "http://api/pages/abc123", {}, OutputFormatFieldsEnum.JSON
        )

        self.assertEqual(result, mock_response)

    @patch("cli.pages.handlers.httpx.get")
    def test_http_error_raises(self, mock_get):
        mock_get.return_value = _make_response(404)

        with self.assertRaises(httpx.HTTPStatusError):
            retrieve_page("http://api/pages/missing", {}, OutputFormatFieldsEnum.JSON)

    @patch("cli.pages.handlers.httpx.get")
    def test_http_500_raises(self, mock_get):
        mock_get.return_value = _make_response(500)

        with self.assertRaises(httpx.HTTPStatusError):
            retrieve_page("http://api/pages/abc123", {}, OutputFormatFieldsEnum.JSON)


class TestDeletePage(unittest.TestCase):

    @patch("cli.pages.handlers.httpx.delete")
    def test_success(self, mock_delete):
        mock_delete.return_value = _make_response(204)

        result = delete_page("http://api/pages/abc123", {}, "abc123")

        self.assertIsNotNone(result)

    @patch("cli.pages.handlers.httpx.delete")
    def test_404_raises_http_status_error(self, mock_delete):
        mock_delete.return_value = _make_response(404)

        with self.assertRaises(httpx.HTTPStatusError):
            delete_page("http://api/pages/missing", {}, "missing")

    @patch("cli.pages.handlers.httpx.delete")
    def test_500_raises(self, mock_delete):
        mock_delete.return_value = _make_response(500)

        with self.assertRaises(httpx.HTTPStatusError):
            delete_page("http://api/pages/abc123", {}, "abc123")

    @patch("cli.pages.handlers.httpx.delete")
    def test_request_error_raises(self, mock_delete):
        mock_delete.side_effect = httpx.RequestError("connection failed")

        with self.assertRaises(httpx.RequestError):
            delete_page("http://api/pages/abc123", {}, "abc123")


class TestUploadPageCode(unittest.TestCase):

    @patch("cli.pages.handlers.httpx.Client")
    def test_sends_zip_file(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.post.return_value = _make_response(200)

        upload_page_code("http://api/pages/abc123/code", {}, b"zipdata", "my_page")

        mock_client.post.assert_called_once()
        _, kwargs = mock_client.post.call_args
        self.assertIn("zipFile", kwargs["files"])
        self.assertEqual(kwargs["files"]["zipFile"][0], "my_page.zip")
        self.assertEqual(kwargs["files"]["zipFile"][2], "application/zip")


class TestDownloadPageCode(unittest.TestCase):

    @patch("cli.pages.handlers.httpx.get")
    def test_returns_response(self, mock_get):
        mock_response = _make_response(200)
        mock_get.return_value = mock_response

        result = download_page_code("http://api/pages/abc123/code", {})

        self.assertEqual(result, mock_response)
        mock_get.assert_called_once_with(
            "http://api/pages/abc123/code", headers={}, follow_redirects=True
        )


if __name__ == "__main__":
    unittest.main()
