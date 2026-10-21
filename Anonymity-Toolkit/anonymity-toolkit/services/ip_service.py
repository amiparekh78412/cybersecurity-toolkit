"""Public IP lookup service.

Responsibility:
    Ask an external HTTP service which public IP address it sees for this
    connection, validate the answer, and return a typed observation. All failures
    become `IpLookupError` with a user-friendly message (never a raw traceback).

Connections:
    Called by ui/ip_page.py through Controller.run_task (background thread).
    Does not import the GUI, so it is fully unit-testable with a mocked session.

Limitations:
    The result is what ONE lookup server observed at ONE moment. It does not
    prove anonymity, correct VPN routing, or absence of DNS/WebRTC leaks.
"""
from __future__ import annotations

import ipaddress
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import requests

log = logging.getLogger(__name__)

IPIFY_URL = "https://api.ipify.org"
SOURCE_NAME = "api.ipify.org"
CONNECT_TIMEOUT_S = 5
READ_TIMEOUT_S = 10
MAX_RESPONSE_CHARS = 45  # longest valid IPv6 text form is 45 characters


class IpLookupError(Exception):
    """Lookup failed. `kind` is machine-readable; str(error) is for the user."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass
class IpObservation:
    ip: str
    version: int            # 4 or 6
    timestamp: str          # ISO 8601, UTC
    source: str
    elapsed_ms: float
    origin: str = "observed"  # observed | simulated (kept explicit for reports)

    def to_dict(self) -> dict:
        return asdict(self)


def parse_ip(text: str) -> tuple[str, int]:
    """Validate `text` as an IP address; return (normalised text, version)."""
    cleaned = text.strip()
    if not cleaned or len(cleaned) > MAX_RESPONSE_CHARS:
        raise IpLookupError("invalid_response", "The lookup service returned an unexpected response.")
    try:
        addr = ipaddress.ip_address(cleaned)
    except ValueError:
        raise IpLookupError("invalid_response", "The lookup service did not return a valid IP address.") from None
    return str(addr), addr.version


def fetch_public_ip(session: requests.Session | None = None, url: str = IPIFY_URL) -> IpObservation:
    """Perform one lookup. Pass a mock `session` in tests."""
    http = session or requests
    started = time.perf_counter()
    try:
        response = http.get(url, timeout=(CONNECT_TIMEOUT_S, READ_TIMEOUT_S), allow_redirects=False)
        status = response.status_code
        body = response.text
    except requests.exceptions.SSLError:  # must precede ConnectionError (it is a subclass)
        raise IpLookupError("tls", "A secure (TLS) connection to the lookup service could not be established.") from None
    except requests.exceptions.Timeout:
        raise IpLookupError("timeout", "The lookup timed out. Check your connection and try again.") from None
    except requests.exceptions.ConnectionError:
        raise IpLookupError("connection", "Could not reach the lookup service. Are you connected to the internet?") from None
    except requests.exceptions.RequestException as exc:
        log.warning("Unexpected request error: %s", type(exc).__name__)
        raise IpLookupError("unexpected", "The lookup failed unexpectedly.") from None

    elapsed_ms = (time.perf_counter() - started) * 1000
    if status != 200:
        raise IpLookupError("http", f"The lookup service answered with HTTP status {status}.")

    ip, version = parse_ip(body)
    return IpObservation(
        ip=ip,
        version=version,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source=SOURCE_NAME,
        elapsed_ms=round(elapsed_ms, 1),
    )
