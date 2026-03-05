import unittest

import httpx
import respx

from cli.pages.handlers import upload_page_code


class TestUploadPageCode(unittest.TestCase):

    @respx.mock
    def test_sends_zip_file(self):
        route = respx.post("http://api/pages/abc123/code").mock(return_value=httpx.Response(200))

        upload_page_code("http://api/pages/abc123/code", {}, b"zipdata", "my_page")

        self.assertTrue(route.called)
        request_content = route.calls.last.request.content.decode()
        self.assertIn("my_page.zip", request_content)
        self.assertIn("application/zip", request_content)


