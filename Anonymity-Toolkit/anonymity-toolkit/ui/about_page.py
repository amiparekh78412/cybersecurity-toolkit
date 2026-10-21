"""About / Help page: what the tool does, what it cannot do, privacy and ethical use."""
from __future__ import annotations

import customtkinter as ctk

from app import APP_NAME, APP_VERSION
from app.navigation import PAGES
from app.theme import COLORS, FONTS, PAD, PAD_SMALL
from ui.base_page import BasePage
from ui.components import Card

SPEC = next(p for p in PAGES if p.key == "about")

SECTIONS = [
    ("What this tool does", [
        "Shows the public IP address an external lookup service sees (Online mode).",
        "Tests one HTTP/HTTPS proxy you own or are authorised to test (Online mode).",
        "Compares your saved IP observations, for example before and after you connect a VPN yourself.",
        "Gives a guided privacy checklist and an offline simulator with 7 SIMULATED scenarios.",
        "Exports a local TXT or HTML report.",
    ]),
    ("What it cannot do", [
        "It cannot guarantee anonymity or prove that a VPN is configured correctly.",
        "It does not test for DNS, WebRTC or IPv6 leaks, kill-switch behaviour or operating-system settings.",
        "A changed IP address is not proof of anonymity. An unchanged one does not prove a VPN is off.",
        "Proxy support covers http:// and https:// proxies only (no SOCKS).",
    ]),
    ("Quick start", [
        "1. Switch to Online mode (bottom of the sidebar) and run an IP lookup. It is saved automatically.",
        "2. Connect or disconnect your VPN or proxy outside this app, then run another lookup.",
        "3. Open Network Comparison, choose two observations and read the explanation and limitations.",
        "4. Work through the Privacy Checklist at your own pace and use the Learning Simulator to understand the concepts.",
        "5. Create a report on the Reports page. Offline mode works for everything except new lookups and proxy tests.",
    ]),
    ("Privacy and ethical use", [
        "Only test proxies, networks and accounts you own or are authorised to use.",
        "The tool never scans networks, finds proxies or tries credentials.",
        "No analytics. Nothing is sent anywhere except the lookup and proxy-test requests you start in Online mode.",
        "Proxy passwords stay in memory for one test and are never saved, logged or put in reports.",
    ]),
]


class AboutPage(BasePage):
    SPEC = SPEC

    def __init__(self, master, controller):
        super().__init__(master, controller)
        row = 0
        head = Card(self.body, f"{APP_NAME} {APP_VERSION}")
        head.grid(row=row, column=0, sticky="ew", pady=(0, PAD)); row += 1
        ctk.CTkLabel(
            head, font=FONTS["body"], text_color=COLORS["text"], anchor="w", justify="left", wraplength=760,
            text="A cybersecurity student project about network privacy, VPNs, proxies and diagnostics. Educational use only.",
        ).grid(row=1, column=0, sticky="w", padx=PAD, pady=(0, PAD))

        for title, lines in SECTIONS:
            card = Card(self.body, title)
            card.grid(row=row, column=0, sticky="ew", pady=(0, PAD)); row += 1
            text = "\n".join(line if line[:2].strip().rstrip(".").isdigit() else f"• {line}" for line in lines)
            ctk.CTkLabel(card, text=text, font=FONTS["body"], text_color=COLORS["text"], anchor="w", justify="left", wraplength=760).grid(
                row=1, column=0, sticky="w", padx=PAD, pady=(0, PAD))

        self.data_card = Card(self.body, "Where your data is stored")
        self.data_card.grid(row=row, column=0, sticky="ew")
        self.data_label = ctk.CTkLabel(self.data_card, text="", font=FONTS["body"], text_color=COLORS["text"], anchor="w", justify="left", wraplength=760)
        self.data_label.grid(row=1, column=0, sticky="w", padx=PAD, pady=(0, PAD))

    def on_show(self) -> None:
        self.data_label.configure(
            text=f"{self.controller.data_location()}\nIt holds preferences, saved observations, proxy results (no credentials) and checklist answers. "
                 "Reports are saved wherever you choose, separate from this file. Use 'Clear saved history' on the Dashboard to delete observations."
        )
