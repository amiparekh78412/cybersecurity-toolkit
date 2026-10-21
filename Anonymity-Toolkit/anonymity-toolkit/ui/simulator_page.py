"""Learning Simulator page. Fully offline; everything shown is SIMULATED.

The traffic flow is drawn with ordinary frames and labels (no canvas) so it follows
the light/dark theme and resizes with the window. Each link states its protection
in WORDS as well as colour.
"""
from __future__ import annotations

import customtkinter as ctk

from app.navigation import PAGES
from app.theme import COLORS, FONTS, PAD, PAD_SMALL
from simulator.scenarios import PROTECTION_LABELS, SIMULATED_LABEL, SIMULATION_NOTICE, Scenario, ScenarioDataError, load_scenarios
from ui.base_page import BasePage
from ui.components import Banner, Card, StatusBadge

SPEC = next(p for p in PAGES if p.key == "simulator")
LINK_COLOURS = {
    "encrypted": COLORS["success"],
    "tunnel": COLORS["success"],
    "partial": COLORS["warning"],
    "plain": COLORS["error"],
    "failed": COLORS["error"],
    "info": COLORS["text_muted"],
}
WRAP = 740


class SimulatorPage(BasePage):
    SPEC = SPEC

    def __init__(self, master, controller):
        super().__init__(master, controller)
        try:
            self.scenarios = load_scenarios()
        except ScenarioDataError as exc:
            Banner(self.body, f"The scenarios could not be loaded: {exc}", "error").grid(row=0, column=0, sticky="ew")
            return
        self._by_title = {s.title: s for s in self.scenarios}

        notice = Card(self.body)
        notice.grid(row=0, column=0, sticky="ew", pady=(0, PAD))
        StatusBadge(notice, text=f"● {SIMULATED_LABEL}", color=COLORS["simulated"]).grid(row=0, column=0, sticky="w", padx=PAD, pady=(PAD, PAD_SMALL))
        ctk.CTkLabel(notice, text=SIMULATION_NOTICE, font=FONTS["body"], text_color=COLORS["text"], anchor="w", justify="left", wraplength=WRAP).grid(
            row=1, column=0, sticky="w", padx=PAD, pady=(0, PAD)
        )

        chooser = Card(self.body, "Choose a scenario")
        chooser.grid(row=1, column=0, sticky="ew", pady=(0, PAD))
        chooser.columnconfigure(0, weight=1)
        self.menu = ctk.CTkOptionMenu(chooser, values=list(self._by_title), command=self._show_by_title, dynamic_resizing=False)
        self.menu.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, PAD))

        self.content = ctk.CTkFrame(self.body, fg_color="transparent")
        self.content.grid(row=2, column=0, sticky="ew")
        self.content.columnconfigure(0, weight=1)
        self._show(self.scenarios[0])

    # ----- building blocks -----
    @staticmethod
    def _bullets(items) -> str:
        return "\n".join(f"• {item}" for item in items)

    def _label(self, parent, text: str, row: int, muted: bool = False) -> None:
        ctk.CTkLabel(
            parent, text=text, font=FONTS["body"], text_color=COLORS["text_muted"] if muted else COLORS["text"],
            anchor="w", justify="left", wraplength=WRAP,
        ).grid(row=row, column=0, sticky="w", padx=PAD, pady=(0, PAD_SMALL))

    def _draw_flow(self, card: Card, flow) -> None:
        box = ctk.CTkFrame(card, fg_color="transparent")
        box.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, PAD))
        box.columnconfigure(0, weight=1)
        row = 0
        for index, node in enumerate(flow.nodes):
            frame = ctk.CTkFrame(box, fg_color=COLORS["bg"], border_color=COLORS["simulated"], border_width=2, corner_radius=8)
            frame.grid(row=row, column=0, pady=2)
            ctk.CTkLabel(frame, text=node, font=FONTS["body"], text_color=COLORS["text"]).pack(padx=PAD, pady=6)
            row += 1
            if index < len(flow.links):
                link = flow.links[index]
                tag = PROTECTION_LABELS[link.protection].upper()
                ctk.CTkLabel(
                    box, text=f"▼  [{tag}]  {link.label}", font=FONTS["small"], text_color=LINK_COLOURS[link.protection],
                    wraplength=WRAP - 40, justify="center",
                ).grid(row=row, column=0, pady=4)
                row += 1

    # ----- page content -----
    def _show_by_title(self, title: str) -> None:
        self._show(self._by_title[title])

    def _show(self, scenario: Scenario) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        row = 0

        card = Card(self.content, f"{SIMULATED_LABEL} · Summary and assumptions")
        card.grid(row=row, column=0, sticky="ew", pady=(0, PAD)); row += 1
        self._label(card, scenario.summary, 1)
        self._label(card, "Assumptions this scenario makes:\n" + self._bullets(scenario.assumptions), 2, muted=True)

        for flow in scenario.flows:
            card = Card(self.content, f"{SIMULATED_LABEL} · Traffic flow: {flow.title}")
            card.grid(row=row, column=0, sticky="ew", pady=(0, PAD)); row += 1
            self._draw_flow(card, flow)

        card = Card(self.content, f"{SIMULATED_LABEL} · What each party may observe")
        card.grid(row=row, column=0, sticky="ew", pady=(0, PAD)); row += 1
        for i, party in enumerate(scenario.parties, start=1):
            text = f"{party.name}\n  Can see:\n" + "\n".join(f"    • {x}" for x in party.can_see)
            if party.cannot_see:
                text += "\n  Cannot see:\n" + "\n".join(f"    • {x}" for x in party.cannot_see)
            self._label(card, text, i)

        card = Card(self.content, f"{SIMULATED_LABEL} · What encryption and protection do and do not cover")
        card.grid(row=row, column=0, sticky="ew", pady=(0, PAD)); row += 1
        self._label(card, "Protects:\n" + self._bullets(scenario.protects), 1)
        self._label(card, "Does NOT protect:\n" + self._bullets(scenario.does_not_protect), 2)

        card = Card(self.content, "Practical defensive recommendations")
        card.grid(row=row, column=0, sticky="ew", pady=(0, PAD)); row += 1
        self._label(card, self._bullets(scenario.recommendations), 1)
