from io import BytesIO
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from tests.support import ROOT
from letenky.domain.errors import InvalidResponse, ProviderError
from letenky.providers.ryanair.client import RyanairClient


class HttpTests(unittest.TestCase):
    def test_temporary_failure_retries_once(self):
        with patch("letenky.providers.ryanair.client.urlopen", side_effect=[URLError("offline"), BytesIO(b'{"fares": []}')]) as open_url:
            with patch("letenky.providers.ryanair.client.time.sleep"):
                self.assertEqual(RyanairClient().get("/test"), {"fares": []})
            self.assertEqual(open_url.call_count, 2)

    def test_rate_limit_and_access_denial_do_not_retry(self):
        for code in (403, 409, 429):
            with self.subTest(code=code):
                with patch("letenky.providers.ryanair.client.urlopen", side_effect=HTTPError("https://www.ryanair.com", code, "error", {}, None)) as open_url:
                    with self.assertRaises(ProviderError) as error:
                        RyanairClient().get("/test")
                    self.assertIn(str(code), str(error.exception))
                    self.assertEqual(open_url.call_count, 1)

    def test_html_response_does_not_look_like_empty_fares(self):
        with patch("letenky.providers.ryanair.client.urlopen", return_value=BytesIO(b'<html>Unavailable</html>')):
            with self.assertRaises(InvalidResponse):
                RyanairClient().get("/test")
