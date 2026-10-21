"""Remove secrets from text before it is logged or written to a report.

Responsibility:
    One shared function, `redact_credentials`, used by the logging setup and the
    report generator. It errs on the side of redacting too much.

Limitations:
    Pattern based. It catches URL credentials (scheme://user:pass@host),
    Authorization / Proxy-Authorization headers and key=value pairs such as
    password=..., but it cannot recognise a secret written in free text.
"""
from __future__ import annotations

import re

_URL_USERINFO = re.compile(r"(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*://)[^/\s:@]+(?::[^/\s@]*)?@")
_AUTH_HEADER = re.compile(r"(?i)\b(proxy-authorization|authorization)\s*[:=]\s*(?:(?:basic|bearer|digest)\s+)?[^\s,;]+")
_KEY_VALUE = re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*[^\s,;&]+")


def redact_credentials(text: str) -> str:
    text = _URL_USERINFO.sub(r"\g<scheme>[redacted]@", text)
    text = _AUTH_HEADER.sub(lambda m: f"{m.group(1)}: [redacted]", text)
    text = _KEY_VALUE.sub(lambda m: f"{m.group(1)}=[redacted]", text)
    return text
