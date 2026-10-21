import io
import logging
import unittest

from services.redaction import redact_credentials


class RedactionTests(unittest.TestCase):
    def test_url_credentials_removed(self):
        out = redact_credentials("Cannot connect to http://alice:S3cr3t!pw@proxy.example:8080 now")
        self.assertNotIn("S3cr3t", out)
        self.assertNotIn("alice", out)
        self.assertIn("proxy.example:8080", out)

    def test_username_only_and_https(self):
        self.assertNotIn("bob", redact_credentials("https://bob@host:443"))

    def test_headers_and_key_values(self):
        for text in ["Proxy-Authorization: Basic dXNlcjpwYXNz", "authorization=Bearer abc123", "password=hunter2", "api_key: XYZ"]:
            with self.subTest(text=text):
                out = redact_credentials(text)
                for secret in ("dXNlcjpwYXNz", "abc123", "hunter2", "XYZ"):
                    self.assertNotIn(secret, out)
                self.assertIn("[redacted]", out)

    def test_ordinary_text_untouched(self):
        for text in ["Lookup succeeded at 2026-10-03T10:00:00+00:00", "email me at user@example.com", "http://host:8080"]:
            self.assertEqual(redact_credentials(text), text)


class LoggingFilterTests(unittest.TestCase):
    def test_filter_redacts_messages_and_tracebacks(self):
        from app.logging_setup import RedactingFilter

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.addFilter(RedactingFilter())
        logger = logging.getLogger("redaction-test")
        logger.propagate = False
        logger.addHandler(handler)
        logger.warning("proxy %s failed", "http://u:TOPSECRET@h:80")
        try:
            raise RuntimeError("bad http://u:TOPSECRET2@h:80")
        except RuntimeError:
            logger.exception("boom")
        self.assertNotIn("TOPSECRET", stream.getvalue())
        self.assertIn("[redacted]", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
