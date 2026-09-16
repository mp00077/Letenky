from io import BytesIO
import socket
import ssl
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from tests.support import ROOT
from letenky.domain.errors import InvalidResponse, ProviderError
from letenky.providers.ryanair.client import RyanairClient
from letenky.infrastructure.tls import create_tls_context


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

    def test_certificate_failure_is_reported_without_retry(self):
        for wrap in (lambda exc: exc, URLError):
            failure = wrap(ssl.SSLCertVerificationError(1, "CERTIFICATE_VERIFY_FAILED"))
            with self.subTest(wrapped=isinstance(failure, URLError)):
                with patch("letenky.providers.ryanair.client.urlopen", side_effect=failure) as open_url:
                    with patch("letenky.providers.ryanair.client.time.sleep") as sleep:
                        with self.assertRaisesRegex(ProviderError, "certifikát") as error:
                            RyanairClient().get("/test")
                        self.assertIs(error.exception.__cause__, failure)
                        self.assertEqual(open_url.call_count, 1)
                        sleep.assert_not_called()

    def test_network_failure_categories_and_bounded_retries(self):
        for reason, message, attempts in (
            (socket.gaierror(-2, "Name not known"), "DNS", 2),
            (TimeoutError("timed out"), "časový limit", 2),
            (ConnectionRefusedError("refused"), "odmítnuto", 2),
            (ssl.SSLError(1, "handshake failure"), "TLS", 1),
        ):
            with self.subTest(reason=type(reason).__name__):
                with patch("letenky.providers.ryanair.client.urlopen", side_effect=URLError(reason)) as open_url:
                    with patch("letenky.providers.ryanair.client.time.sleep"):
                        with self.assertRaisesRegex(ProviderError, message):
                            RyanairClient().get("/test")
                        self.assertEqual(open_url.call_count, attempts)

    def test_missing_certificate_bundle_does_not_attempt_request(self):
        with patch("letenky.providers.ryanair.client.create_tls_context", side_effect=FileNotFoundError("cacert.pem")):
            with patch("letenky.providers.ryanair.client.urlopen") as open_url:
                with self.assertRaisesRegex(ProviderError, "certifi"):
                    RyanairClient().get("/test")
                open_url.assert_not_called()

    def test_request_uses_verifying_context(self):
        with patch("letenky.providers.ryanair.client.urlopen", return_value=BytesIO(b'{"fares": []}')) as open_url:
            RyanairClient().get("/test")
            context = open_url.call_args.kwargs["context"]
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
            self.assertGreater(context.cert_store_stats()["x509_ca"], 0)

    def test_portable_roots_work_without_python_default_ca_store(self):
        # Reproduce the missing-CA configuration without requiring a Mac.
        empty_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.assertEqual(empty_context.cert_store_stats()["x509_ca"], 0)
        with patch("letenky.infrastructure.tls.ssl.create_default_context", return_value=empty_context):
            context = create_tls_context()
        self.assertGreater(context.cert_store_stats()["x509_ca"], 0)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
