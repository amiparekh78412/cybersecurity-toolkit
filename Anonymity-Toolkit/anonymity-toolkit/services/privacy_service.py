"""Rule-based privacy checklist (transparent, manual, no scoring).

Responsibility:
    Define the checklist items, their statuses, and turn the user's answers into
    findings for the UI and for reports. Pure logic: no GUI, no network.

Honesty rules built into the design:
    * Nothing here inspects the operating system, browser or VPN client. Every
      status is something the USER reports, and "Reviewed" means "I checked".
    * Default status is "Not verified" (nothing has been checked yet).
    * There is no anonymity score, percentage or grade.
"""
from __future__ import annotations

from dataclasses import dataclass

from services.comparison_service import ComparisonError, compare_observations

STATUS_LABELS = {
    "not_verified": "Not verified",
    "needs_review": "Needs review",
    "reviewed": "Reviewed",
}
DEFAULT_STATUS = "not_verified"


@dataclass(frozen=True)
class ChecklistItem:
    id: str
    title: str
    purpose: str
    evidence_required: str
    recommended_next_step: str
    limitations: str
    review_steps: tuple[str, ...]


ITEMS: tuple[ChecklistItem, ...] = (
    ChecklistItem(
        "vpn_active",
        "VPN configured or reported active",
        "Confirms you have a VPN set up and that your VPN app reports a connected tunnel.",
        "Your VPN app shows 'connected' with a named server. Before/after IP lookups in this app are optional supporting evidence.",
        "Open your VPN app, confirm it is connected, then compare two IP lookups on the Network Comparison page.",
        "This app cannot see your VPN client. 'Reviewed' means you checked; it does not prove all traffic uses the tunnel.",
        (
            "Open your VPN app and confirm its status says connected.",
            "Note the server or country it shows.",
            "Run an IP lookup before and after connecting (IP Information page).",
            "Open Network Comparison and read the explanation and limitations.",
        ),
    ),
    ChecklistItem(
        "kill_switch",
        "VPN kill-switch setting checked",
        "A kill switch blocks traffic if the VPN connection drops, so your normal address is not exposed by accident.",
        "The kill-switch (or 'network lock') option is visible as enabled in your VPN app's settings.",
        "Find the option in your VPN app and enable it if available; read what the provider says it blocks.",
        "This app cannot read VPN settings or test a dropped connection. Behaviour differs by provider and operating system.",
        (
            "Open your VPN app's settings and look for 'Kill switch', 'Network lock' or 'Block connections without VPN'.",
            "Read the provider's description: does it block all traffic, or only selected apps?",
            "Check the provider's documentation for how it behaves when the VPN reconnects.",
        ),
    ),
    ChecklistItem(
        "dns_review",
        "DNS configuration and exposure reviewed",
        "DNS lookups reveal which sites you visit to whoever runs your DNS resolver. With a VPN they should normally go through the tunnel.",
        "A DNS leak test result from a tool you chose, plus your device's or VPN app's DNS setting.",
        "Run a DNS leak test while connected and check that the listed resolvers belong to your VPN provider or a resolver you chose.",
        "This app does not run DNS leak tests or read DNS settings. Encrypted DNS changes who can read queries on the path, not whether the resolver sees them.",
        (
            "Connect to your VPN.",
            "Run a DNS leak test from a reputable tool you choose.",
            "Compare the resolvers listed with those of your VPN provider or your chosen resolver.",
            "If they belong to your ISP unexpectedly, check your VPN app's DNS settings.",
        ),
    ),
    ChecklistItem(
        "webrtc_review",
        "Browser WebRTC exposure reviewed",
        "WebRTC can let websites learn network addresses of your device from inside the browser, sometimes including addresses outside a VPN tunnel.",
        "A WebRTC test result from the browser you actually use, and the status of any related browser setting or extension.",
        "Test in your main browser while the VPN is on; if your own address appears, follow your browser's or VPN provider's guidance to restrict WebRTC.",
        "Cannot be tested from this app. Results differ by browser, version and extensions, and restricting WebRTC can break video calls.",
        (
            "Connect to your VPN.",
            "Open a WebRTC test page in the browser you normally use.",
            "Check whether it lists addresses that are not your VPN's.",
            "Repeat in any other browser you use.",
        ),
    ),
    ChecklistItem(
        "tracking_protection",
        "Browser tracking protections considered",
        "Websites can track you with cookies, fingerprinting and third-party scripts regardless of your IP address.",
        "Your browser's tracking-protection and third-party-cookie settings, and any content blockers you use.",
        "Review your browser's privacy settings, consider blocking third-party cookies, and keep the browser updated.",
        "No setting fully stops fingerprinting, and stricter settings can break some sites. This app cannot read browser settings.",
        (
            "Open your browser's privacy or security settings.",
            "Note how third-party cookies and tracking protection are set.",
            "Decide whether you want a stricter setting, accepting that some sites may break.",
        ),
    ),
    ChecklistItem(
        "account_cookies",
        "Account-based identification and cookies understood",
        "Signed in services recognise you by account whatever IP address you use, and cookies can link browsing sessions together.",
        "You can explain which accounts you are signed into while testing and how cookies and sessions persist across a VPN change.",
        "Sign out of accounts when privacy matters, use separate browser profiles, and clear cookies when appropriate.",
        "Self-assessed only: this app cannot see your accounts, cookies or sessions.",
        (
            "List the accounts you are signed into in your browser.",
            "Ask: would this service still know who I am after I change my IP address?",
            "Consider a separate browser profile for activity you want kept apart.",
        ),
    ),
    ChecklistItem(
        "report_hygiene",
        "Sensitive information excluded from saved reports",
        "Saved history and reports contain IP addresses and timestamps, which are personal data and should not be shared carelessly.",
        "You have looked at what is stored (the Dashboard shows the file location) and read a report before sharing it.",
        "Open a report before sending it, and clear saved history you no longer need from the Dashboard.",
        "The app avoids saving passwords and credentials, but it cannot judge what else you consider sensitive.",
        (
            "Open the Dashboard and note where local data is stored.",
            "Read any generated report in full before sharing it.",
            "Clear saved history you no longer need.",
        ),
    ),
)

ITEM_IDS = tuple(item.id for item in ITEMS)


@dataclass(frozen=True)
class Finding:
    item_id: str
    title: str
    status: str
    status_label: str
    evidence_kind: str      # "user-reported" or "unverified"; never "observed"
    recommendation: str
    limitations: str


def clean_states(raw) -> dict[str, str]:
    """Keep only known item ids with valid statuses."""
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if k in ITEM_IDS and v in STATUS_LABELS}


def status_for(states: dict[str, str], item_id: str) -> str:
    value = states.get(item_id, DEFAULT_STATUS)
    return value if value in STATUS_LABELS else DEFAULT_STATUS


def build_finding(item: ChecklistItem, status: str) -> Finding:
    status = status if status in STATUS_LABELS else DEFAULT_STATUS
    if status == "reviewed":
        evidence_kind = "user-reported"
        recommendation = "You marked this as reviewed. Re-check it after changing your VPN, browser or network."
    else:
        evidence_kind = "unverified"
        recommendation = item.recommended_next_step
    return Finding(item.id, item.title, status, STATUS_LABELS[status], evidence_kind, recommendation, item.limitations)


def build_findings(states: dict[str, str]) -> list[Finding]:
    return [build_finding(item, status_for(states, item.id)) for item in ITEMS]


def summary_counts(states: dict[str, str]) -> dict[str, int]:
    counts = {key: 0 for key in STATUS_LABELS}
    for item in ITEMS:
        counts[status_for(states, item.id)] += 1
    return counts


def observation_hint(observations: list) -> str:
    """Supporting context for the VPN item, taken from saved lookups. Never proof."""
    if len(observations) < 2:
        return "Saved lookups: fewer than two, so there is nothing to compare yet (see Network Comparison)."
    try:
        res = compare_observations(observations[-2], observations[-1])
    except ComparisonError:
        return "Saved lookups could not be compared."
    if res.ips_differ:
        return ("Your two latest saved lookups show different addresses (OBSERVED). This is supporting context only, "
                "not proof that the VPN is configured correctly.")
    return ("Your two latest saved lookups show the same address (OBSERVED). This alone does not establish "
            "whether a VPN is active.")
