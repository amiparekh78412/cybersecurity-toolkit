"""Proxy diagnostic service.

Responsibility:
    1. Validate a proxy endpoint (scheme, host, port).
    2. Send ONE request to a known HTTPS destination through that proxy and report
       what happened, separating proxy-side problems from destination-side ones
       where the evidence allows.

Security rules enforced here:
    * Credentials are held only inside the ParsedProxy object for one test. They
      are excluded from repr(), from results, and from log messages.
    * Error text from `requests` is never shown or logged (it can embed the proxy
      URL, including credentials). Only the exception TYPE is used.
    * Credentials cannot be typed inside the URL; they are separate arguments.
    * One endpoint, one request. No discovery, scanning or credential guessing.

Limitations:
    A successful test shows that ONE request through the proxy worked. It does not
    show that other applications use the proxy, nor that DNS or other traffic is
    protected.
"""
from __future__ import annotations

import ipaddress
import logging
import re
import time
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from urllib.parse import quote, urlparse

import requests

from services.ip_service import IPIFY_URL, SOURCE_NAME, IpLookupError, parse_ip

log = logging.getLogger(__name__)

CONNECT_TIMEOUT_S = 8
READ_TIMEOUT_S = 12
ALLOWED_SCHEMES = ("http", "https")
_HOST_RE = re.compile(
    r"^(?=.{1,253}$)[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$"
)


class ProxyValidationError(ValueError):
    """The proxy input is not acceptable. str(error) is a user-friendly message."""


@dataclass(frozen=True)
class ParsedProxy:
    scheme: str
    host: str
    port: int
    username: str = ""
    password: str = field(default="", repr=False)  # never printed

    @property
    def _netloc_host(self) -> str:
        return f"[{self.host}]" if ":" in self.host else self.host

    @property
    def safe_url(self) -> str:
        """URL without credentials: the only form that may be shown or logged."""
        return f"{self.scheme}://{self._netloc_host}:{self.port}"

    @property
    def has_credentials(self) -> bool:
        return bool(self.username)

    def _request_url(self) -> str:
        """URL with credentials, used ONLY to build the request. Never log this."""
        if not self.username:
            return self.safe_url
        user = quote(self.username, safe="")
        pwd = quote(self.password, safe="")
        auth = f"{user}:{pwd}" if self.password else user
        return f"{self.scheme}://{auth}@{self._netloc_host}:{self.port}"


def parse_proxy_url(text: str, username: str = "", password: str = "") -> ParsedProxy:
    """Validate `text` like 'http://host:8080' and return a ParsedProxy."""
    raw = (text or "").strip()
    if not raw:
        raise ProxyValidationError("Enter a proxy address, for example http://proxy.example.com:8080")
    if any(ch.isspace() for ch in raw):
        raise ProxyValidationError("The proxy address must not contain spaces.")
    if "@" in raw:
        raise ProxyValidationError("Do not put a username or password in the address. Use the separate fields.")

    parsed = urlparse(raw)
    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ProxyValidationError("The address must start with http:// or https://")
    if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
        raise ProxyValidationError("Use only scheme, host and port, for example http://host:8080")

    host = parsed.hostname
    if not host:
        raise ProxyValidationError("The proxy address has no host name.")
    try:
        port = parsed.port
    except ValueError:
        raise ProxyValidationError("The port is not a valid number.") from None
    if port is None:
        raise ProxyValidationError("Add a port, for example http://host:8080")
    if not 1 <= port <= 65535:
        raise ProxyValidationError("The port must be between 1 and 65535.")

    try:
        host = str(ipaddress.ip_address(host))
    except ValueError:
        if not _HOST_RE.match(host):
            raise ProxyValidationError("The host name is not valid.") from None

    if password and not username:
        raise ProxyValidationError("A password was entered without a username.")
    return ParsedProxy(scheme=scheme, host=host, port=port, username=username.strip(), password=password)


@dataclass
class ProxyTestResult:
    success: bool
    stage: str            # ok | proxy_connection | proxy_auth | timeout | tls | destination_http | invalid_response | unexpected
    message: str
    proxy: str            # credential-free URL
    elapsed_ms: float
    timestamp: str
    http_status: int | None = None
    egress_ip: str | None = None
    destination: str = SOURCE_NAME
    origin: str = "observed"

    def to_dict(self) -> dict:
        return asdict(self)


def test_proxy(proxy: ParsedProxy, session: requests.Session | None = None, url: str = IPIFY_URL) -> ProxyTestResult:
    """Run one test request through `proxy`. Never raises; always returns a result."""
    log.info("Testing proxy %s (credentials: %s)", proxy.safe_url, "yes" if proxy.has_credentials else "no")
    own_session = session is None
    http = session if session is not None else requests.Session()
    if own_session:
        http.trust_env = False  # ignore system proxy variables so only the tested proxy is used
    started = time.perf_counter()

    def result(success: bool, stage: str, message: str, **extra) -> ProxyTestResult:
        return ProxyTestResult(
            success=success,
            stage=stage,
            message=message,
            proxy=proxy.safe_url,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            **extra,
        )

    try:
        proxy_url = proxy._request_url()
        response = http.get(
            url,
            proxies={"http": proxy_url, "https": proxy_url},
            timeout=(CONNECT_TIMEOUT_S, READ_TIMEOUT_S),
            allow_redirects=False,
        )
    except requests.exceptions.ProxyError as exc:
        # str(exc) is deliberately not used: it may contain the proxy URL.
        if "407" in str(exc):
            return result(False, "proxy_auth", "The proxy asked for valid credentials (HTTP 407).")
        return result(False, "proxy_connection", "Could not connect through the proxy. Check the address, port and that the proxy is running.")
    except requests.exceptions.SSLError:
        return result(False, "tls", "A TLS (secure connection) error occurred. The proxy or the destination certificate could not be verified.")
    except requests.exceptions.ConnectTimeout:
        return result(False, "timeout", "Timed out while connecting. The proxy is probably unreachable or blocked.")
    except requests.exceptions.ReadTimeout:
        return result(False, "timeout", "The proxy connected but the response took too long.")
    except requests.exceptions.ConnectionError:
        return result(False, "proxy_connection", "A network connection error occurred before any response was received.")
    except requests.exceptions.RequestException as exc:
        log.warning("Proxy test request error: %s", type(exc).__name__)
        return result(False, "unexpected", "The test failed unexpectedly.")
    except Exception as exc:  # last-resort boundary: the caller must never see a traceback
        log.warning("Proxy test unexpected error: %s", type(exc).__name__)
        return result(False, "unexpected", "The test failed unexpectedly.")
    finally:
        if own_session:
            http.close()

    status = response.status_code
    if status == 407:
        return result(False, "proxy_auth", "The proxy asked for valid credentials (HTTP 407).", http_status=status)
    if status != 200:
        return result(
            False,
            "destination_http",
            f"The proxy connection worked, but the destination answered with HTTP {status}.",
            http_status=status,
        )
    try:
        egress_ip, _version = parse_ip(response.text)
    except IpLookupError:
        return result(False, "invalid_response", "The proxy responded, but the answer was not a valid IP address.", http_status=status)
    return result(True, "ok", "A request through the proxy succeeded.", http_status=status, egress_ip=egress_ip)
