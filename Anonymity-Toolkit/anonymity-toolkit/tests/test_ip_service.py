import unittest
from unittest.mock import MagicMock

import requests

from services.ip_service import IpLookupError, fetch_public_ip, parse_ip


def fake_session(text="203.0.113.7", status=200, exc=None):
    session = MagicMock()
    if exc:
        session.get.side_effect = exc
    else:
        session.get.return_value = MagicMock(status_code=status, text=text)
    return session


class ParseIpTests(unittest.TestCase):
    def test_valid_ipv4_and_ipv6(self):
        self.assertEqual(parse_ip("203.0.113.7"), ("203.0.113.7", 4))
        self.assertEqual(parse_ip("2001:db8::1"), ("2001:db8::1", 6))

    def test_whitespace_is_stripped(self):
        self.assertEqual(parse_ip(" 203.0.113.7\n"), ("203.0.113.7", 4))

    def test_invalid_values_rejected(self):
        for bad in ["", "   ", "999.1.1.1", "<html>error</html>", "not an ip", "1.2.3", "a" * 100]:
            with self.subTest(bad=bad[:20]):
                with self.assertRaises(IpLookupError) as ctx:
                    parse_ip(bad)
                self.assertEqual(ctx.exception.kind, "invalid_response")


class FetchPublicIpTests(unittest.TestCase):
    def test_success_returns_observation(self):
        obs = fetch_public_ip(fake_session("198.51.100.4"))
        self.assertEqual((obs.ip, obs.version, obs.source, obs.origin), ("198.51.100.4", 4, "api.ipify.org", "observed"))
        self.assertGreaterEqual(obs.elapsed_ms, 0)
        self.assertTrue(obs.timestamp.endswith("+00:00"))

    def test_finite_timeouts_always_passed(self):
        session = fake_session()
        fetch_public_ip(session)
        _, kwargs = session.get.call_args
        connect, read = kwargs["timeout"]
        self.assertTrue(0 < connect <= 30 and 0 < read <= 60)

    def test_http_error_status(self):
        with self.assertRaises(IpLookupError) as ctx:
            fetch_public_ip(fake_session(status=503))
        self.assertEqual(ctx.exception.kind, "http")
        self.assertIn("503", str(ctx.exception))

    def test_garbage_body_with_200(self):
        with self.assertRaises(IpLookupError) as ctx:
            fetch_public_ip(fake_session("Service Unavailable"))
        self.assertEqual(ctx.exception.kind, "invalid_response")

    def test_exception_mapping(self):
        cases = [
            (requests.exceptions.ConnectTimeout(), "timeout"),
            (requests.exceptions.ReadTimeout(), "timeout"),
            (requests.exceptions.SSLError(), "tls"),  # SSLError must not be reported as plain connection error
            (requests.exceptions.ConnectionError(), "connection"),
            (requests.exceptions.RequestException(), "unexpected"),
        ]
        for exc, kind in cases:
            with self.subTest(kind=kind, exc=type(exc).__name__):
                with self.assertRaises(IpLookupError) as ctx:
                    fetch_public_ip(fake_session(exc=exc))
                self.assertEqual(ctx.exception.kind, kind)
                self.assertNotIn("Traceback", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
