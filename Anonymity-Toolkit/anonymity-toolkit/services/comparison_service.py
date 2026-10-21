"""Compare two IP observations and explain the result carefully.

Responsibility:
    Decide whether two observed addresses differ and produce a plain-language
    explanation, limitations and follow-up checks. Pure logic: no GUI, no network.

The wording never claims anonymity or proves VPN correctness; see tests.
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from datetime import datetime, timezone

from services.ip_service import IpObservation

LONG_GAP_SECONDS = 24 * 3600

LIMITATIONS = [
    "Each lookup shows only what one external server saw at one moment.",
    "A VPN or proxy can be active without changing this address (for example split tunnelling), and an address "
    "can change for unrelated reasons (your ISP reassigning it, or you switching networks).",
    "This comparison cannot see DNS requests, WebRTC, IPv6 routes, or traffic from other applications.",
]
FOLLOW_UPS = [
    "Confirm in your VPN app that the tunnel is connected and note which server is selected.",
    "Repeat the lookup a few minutes later to check the result is stable.",
    "Review DNS and WebRTC exposure using the Privacy Checklist page.",
    "Check that the kill-switch setting is enabled in your VPN app.",
]


class ComparisonError(ValueError):
    """The comparison cannot be made. str(error) is user-friendly."""


@dataclass
class ComparisonResult:
    earlier: IpObservation
    later: IpObservation
    ips_differ: bool
    versions_differ: bool
    sources_differ: bool
    gap_seconds: float | None
    headline: str
    explanation: str
    notes: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)


def parse_timestamp(text: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def seconds_since(text: str) -> float | None:
    parsed = parse_timestamp(text)
    return None if parsed is None else (datetime.now(timezone.utc) - parsed).total_seconds()


def format_gap(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    seconds = int(abs(seconds))
    if seconds < 60:
        return f"{seconds} s"
    if seconds < 3600:
        return f"{seconds // 60} min {seconds % 60} s"
    return f"{seconds // 3600} h {(seconds % 3600) // 60} min"


def compare_observations(a: IpObservation | None, b: IpObservation | None) -> ComparisonResult:
    if a is None or b is None:
        raise ComparisonError("Two observations are needed. Run at least two IP lookups first.")
    if a is b:
        raise ComparisonError("Choose two different observations.")

    ta, tb = parse_timestamp(a.timestamp), parse_timestamp(b.timestamp)
    earlier, later = (b, a) if (ta and tb and tb < ta) else (a, b)
    t1, t2 = parse_timestamp(earlier.timestamp), parse_timestamp(later.timestamp)
    gap = (t2 - t1).total_seconds() if (t1 and t2) else None

    differ = ipaddress.ip_address(earlier.ip) != ipaddress.ip_address(later.ip)
    versions_differ = earlier.version != later.version
    sources_differ = earlier.source != later.source

    if differ:
        headline = "OBSERVED ADDRESS CHANGED"
        explanation = (
            f"The observed egress address changed from {earlier.ip} to {later.ip}. That is consistent with traffic "
            "leaving through a different network (for example a VPN or proxy), but it does not prove the VPN is "
            "configured correctly, that all of your traffic uses it, or that you are anonymous."
        )
    else:
        headline = "OBSERVED ADDRESS IDENTICAL"
        explanation = (
            f"Both observations show {later.ip}. This result alone does not establish whether a VPN or proxy was "
            "active or inactive: it may have been inactive, or active but not carrying this lookup."
        )

    notes: list[str] = []
    follow_ups = list(FOLLOW_UPS)
    if versions_differ:
        notes.append("The observations use different IP versions (IPv4 vs IPv6), so they are not a like-for-like comparison.")
        follow_ups.append("Test IPv4 and IPv6 separately; a VPN may handle only one of them.")
    if sources_differ:
        notes.append("The observations came from different lookup sources.")
    if "simulated" in (earlier.origin, later.origin):
        notes.append("At least one observation is marked SIMULATED and is not a real measurement.")
    if gap is not None and gap > LONG_GAP_SECONDS:
        notes.append("The observations are more than 24 hours apart; conditions may have changed for unrelated reasons.")

    return ComparisonResult(
        earlier=earlier, later=later, ips_differ=differ, versions_differ=versions_differ,
        sources_differ=sources_differ, gap_seconds=gap, headline=headline, explanation=explanation,
        notes=notes, limitations=list(LIMITATIONS), follow_ups=follow_ups,
    )
