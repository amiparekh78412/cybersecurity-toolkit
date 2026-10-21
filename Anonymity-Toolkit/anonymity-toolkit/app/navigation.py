"""Navigation definitions (GUI-free) so the page list is easy to test and edit."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PageSpec:
    key: str
    title: str
    subtitle: str


PAGES: tuple[PageSpec, ...] = (
    PageSpec("dashboard", "Dashboard", "Overview of your latest observations"),
    PageSpec("ip", "IP Information", "Observe the public IP address a lookup service sees"),
    PageSpec("proxy", "Proxy Tester", "Test an HTTP/HTTPS proxy you own or are authorised to test"),
    PageSpec("comparison", "Network Comparison", "Compare observations before and after a VPN or proxy"),
    PageSpec("privacy", "Privacy Checklist", "Guided, transparent review of privacy settings"),
    PageSpec("simulator", "Learning Simulator", "Offline, clearly labelled SIMULATED scenarios"),
    PageSpec("reports", "Reports", "Export a local report of your findings"),
    PageSpec("about", "About / Help", "What this tool can and cannot tell you"),
)

DEFAULT_PAGE = "dashboard"
