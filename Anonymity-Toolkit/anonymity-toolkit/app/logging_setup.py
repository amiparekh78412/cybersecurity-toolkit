"""Logging that never writes secrets.

A filter on the handler redacts credentials in messages AND in formatted
tracebacks, using the shared `redact_credentials` function.
"""
from __future__ import annotations

import logging
import traceback

from services.redaction import redact_credentials


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # malformed log call: never crash the app because of logging
            message = str(record.msg)
        record.msg = redact_credentials(message)
        record.args = ()
        if record.exc_info:
            text = "".join(traceback.format_exception(*record.exc_info))
            record.exc_text = redact_credentials(text)
            record.exc_info = None  # exc_text is printed instead of the raw traceback
        elif record.exc_text:
            record.exc_text = redact_credentials(record.exc_text)
        return True


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
