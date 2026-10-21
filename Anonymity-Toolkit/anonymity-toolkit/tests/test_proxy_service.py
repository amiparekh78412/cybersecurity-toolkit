import logging
import unittest
from unittest.mock import MagicMock

import requests

from services.proxy_service import ProxyValidationError, parse_proxy_url, test_proxy

test_proxy.__test__ = False  # not a unittest test, just a name that starts with "test"

SECRET = "S3cr3t!pw"


def session(text="203.0.113.9", status=200, exc=None):
    s = MagicMock()
    if exc:
        s.get.side_effect = exc
    else:
        s.get.return_value = MagicMock(status_code=status, text=text)
    return s


class ValidationTests(unittest.TestCase):
    def test_valid_endpoints(self):
        cases = {
            "http://proxy.example.com:8080": "http://proxy.example.com:8080",
            "HTTPS://Proxy.Example.com:443/": "https://Proxy.Example.com:443",
            " http://192.0.2.5:3128 ": "http://192.0.2.5:3128",
            "http://[2001:db8::1]:8080": "http://[2001:db8::1]:8080",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_proxy_url(raw).safe_url.lower(), expected.lower())

    def test_invalid_endpoints(self):
        bad = [
            "", "   ", "proxy.example.com:8080", "ftp://host:21", "socks5://host:1080", "http://", "http://host",
            "http://host:0", "http://host:65536", "http://host:abc", "http://ho st:80", "http://bad_host!:80",
            "http://host:80/path", "http://host:80?x=1", "http://user:pw@host:80",
        ]
        for raw in bad:
            with self.subTest(raw=raw):
                with self.assertRaises(ProxyValidationError):
                    parse_proxy_url(raw)

    def test_password_without_username_rejected(self):
        with self.assertRaises(ProxyValidationError):
            parse_proxy_url("http://host:80", "", SECRET)


class CredentialSafetyTests(unittest.TestCase):
    def test_password_not_in_repr_result_or_logs(self):
        proxy = parse_proxy_url("http://host.example:8080", "alice", SECRET)
        self.assertNotIn(SECRET, repr(proxy))
        self.assertNotIn(SECRET, proxy.safe_url)
        # Simulate a library error whose text leaks the credentialed URL
        leaky = requests.exceptions.ProxyError(f"Cannot connect to proxy http://alice:{SECRET}@host.example:8080")
        with self.assertLogs(level="DEBUG") as logs:
            res = test_proxy(proxy, session(exc=leaky))
        self.assertNotIn(SECRET, str(res.to_dict()))
        self.assertNotIn(SECRET, res.message)
        self.assertNotIn(SECRET, "\n".join(logs.output))

    def test_credentials_are_sent_to_requests_but_url_encoded(self):
        s = session()
        test_proxy(parse_proxy_url("http://host:80", "al ice", "p@ss"), s)
        proxies = s.get.call_args.kwargs["proxies"]
        self.assertEqual(proxies["https"], "http://al%20ice:p%40ss@host:80")


class ProxyTestBehaviour(unittest.TestCase):
    def setUp(self):
        self.proxy = parse_proxy_url("http://host.example:8080")

    def test_success_reports_egress_ip_and_uses_proxy_and_timeouts(self):
        s = session("198.51.100.77")
        res = test_proxy(self.proxy, s)
        self.assertTrue(res.success)
        self.assertEqual((res.stage, res.http_status, res.egress_ip, res.origin), ("ok", 200, "198.51.100.77", "observed"))
        kwargs = s.get.call_args.kwargs
        self.assertEqual(kwargs["proxies"]["https"], "http://host.example:8080")
        connect, read = kwargs["timeout"]
        self.assertTrue(0 < connect <= 30 and 0 < read <= 60)
        self.assertTrue(s.get.call_args.args[0].startswith("https://"))

    def test_failure_classification(self):
        cases = [
            (dict(exc=requests.exceptions.ProxyError("refused")), "proxy_connection"),
            (dict(exc=requests.exceptions.ProxyError("Tunnel connection failed: 407 Proxy Authentication Required")), "proxy_auth"),
            (dict(exc=requests.exceptions.ConnectTimeout()), "timeout"),
            (dict(exc=requests.exceptions.ReadTimeout()), "timeout"),
            (dict(exc=requests.exceptions.SSLError()), "tls"),
            (dict(exc=requests.exceptions.ConnectionError()), "proxy_connection"),
            (dict(exc=requests.exceptions.RequestException()), "unexpected"),
            (dict(exc=RuntimeError("boom")), "unexpected"),
            (dict(status=407), "proxy_auth"),
            (dict(status=503), "destination_http"),
            (dict(text="<html>blocked</html>"), "invalid_response"),
        ]
        for kwargs, stage in cases:
            with self.subTest(stage=stage, case=str(kwargs)[:50]):
                res = test_proxy(self.proxy, session(**kwargs))
                self.assertFalse(res.success)
                self.assertEqual(res.stage, stage)
                self.assertIsNone(res.egress_ip)
                self.assertNotIn("Traceback", res.message)

    def test_destination_error_is_distinct_from_proxy_failure(self):
        self.assertNotEqual(test_proxy(self.proxy, session(status=500)).stage,
                            test_proxy(self.proxy, session(exc=requests.exceptions.ProxyError("x"))).stage)


if __name__ == "__main__":
    unittest.main()
