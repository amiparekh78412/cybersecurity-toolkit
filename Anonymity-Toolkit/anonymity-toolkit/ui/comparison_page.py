"""Network Comparison page: pick two saved observations and compare them.

Works in Offline mode too, because it only uses data already saved locally.
"""
from __future__ import annotations

import customtkinter as ctk

from app.navigation import PAGES
from app.theme import COLORS, FONTS, PAD, PAD_SMALL
from services.comparison_service import ComparisonError, compare_observations, format_gap
from ui.base_page import BasePage
from ui.components import Card

SPEC = next(p for p in PAGES if p.key == "comparison")
NONE_TEXT = "(no observations yet)"


class ComparisonPage(BasePage):
    SPEC = SPEC

    def __init__(self, master, controller):
        super().__init__(master, controller)
        self._by_label: dict = {}

        how = Card(self.body, "How to compare")
        how.grid(row=0, column=0, sticky="ew", pady=(0, PAD))
        ctk.CTkLabel(
            how, font=FONTS["body"], text_color=COLORS["text"], anchor="w", justify="left", wraplength=760,
            text=(
                "1. On IP Information, run a lookup (it is saved automatically).\n"
                "2. Connect or disconnect your VPN/proxy outside this app.\n"
                "3. Run another lookup.\n"
                "4. Come back here, choose two observations and press Compare."
            ),
        ).grid(row=1, column=0, sticky="w", padx=PAD, pady=(0, PAD))

        pick = Card(self.body, "Choose two observations (saved data, SAVED/OBSERVED)")
        pick.grid(row=1, column=0, sticky="ew", pady=(0, PAD))
        pick.columnconfigure(1, weight=1)
        ctk.CTkLabel(pick, text="First", font=FONTS["body"], text_color=COLORS["text"]).grid(row=1, column=0, padx=PAD, pady=PAD_SMALL, sticky="w")
        self.first_menu = ctk.CTkOptionMenu(pick, values=[NONE_TEXT], dynamic_resizing=False)
        self.first_menu.grid(row=1, column=1, padx=(0, PAD), pady=PAD_SMALL, sticky="ew")
        ctk.CTkLabel(pick, text="Second", font=FONTS["body"], text_color=COLORS["text"]).grid(row=2, column=0, padx=PAD, pady=PAD_SMALL, sticky="w")
        self.second_menu = ctk.CTkOptionMenu(pick, values=[NONE_TEXT], dynamic_resizing=False)
        self.second_menu.grid(row=2, column=1, padx=(0, PAD), pady=PAD_SMALL, sticky="ew")
        self.compare_button = ctk.CTkButton(pick, text="Compare", command=self._compare)
        self.compare_button.grid(row=3, column=0, columnspan=2, padx=PAD, pady=PAD_SMALL, sticky="w")
        self.message = ctk.CTkLabel(pick, text="", font=FONTS["body"], anchor="w", justify="left", wraplength=760)
        self.message.grid(row=4, column=0, columnspan=2, padx=PAD, pady=(0, PAD), sticky="ew")

        self.result_card = Card(self.body, "Comparison result")
        self.result_card.grid(row=2, column=0, sticky="ew")
        self.headline = ctk.CTkLabel(self.result_card, text="", font=FONTS["heading"], text_color=COLORS["accent"], anchor="w")
        self.details = ctk.CTkLabel(self.result_card, text="", font=FONTS["mono"], text_color=COLORS["text"], anchor="w", justify="left")
        self.explanation = ctk.CTkLabel(self.result_card, text="", font=FONTS["body"], text_color=COLORS["text"], anchor="w", justify="left", wraplength=760)
        self.extra = ctk.CTkLabel(self.result_card, text="", font=FONTS["body"], text_color=COLORS["text_muted"], anchor="w", justify="left", wraplength=760)
        self._hide_result()

    # ----- helpers -----
    def on_show(self) -> None:
        self._refresh_options()

    def _refresh_options(self) -> None:
        observations = self.controller.observations
        self._by_label = {
            f"#{i} · {o.ip} · {o.timestamp} · {o.source}" + (" · SIMULATED" if o.origin == "simulated" else ""): o
            for i, o in enumerate(observations, start=1)
        }
        labels = list(self._by_label) or [NONE_TEXT]
        old_first, old_second = self.first_menu.get(), self.second_menu.get()
        for menu in (self.first_menu, self.second_menu):
            menu.configure(values=labels)
        if len(labels) >= 2 and self._by_label:
            self.first_menu.set(old_first if old_first in self._by_label else labels[-2])
            self.second_menu.set(old_second if old_second in self._by_label else labels[-1])
            self.compare_button.configure(state="normal")
            self._say("", "info")
        else:
            self.first_menu.set(labels[0])
            self.second_menu.set(labels[0])
            self.compare_button.configure(state="disabled")
            self._hide_result()
            count = len(self._by_label)
            self._say(f"{count} saved observation(s). At least two are needed. Run IP lookups first (Online mode).", "warning")

    def _say(self, text: str, kind: str) -> None:
        colour = {"info": COLORS["text_muted"], "warning": COLORS["warning"], "error": COLORS["error"]}[kind]
        self.message.configure(text=text, text_color=colour)

    def _hide_result(self) -> None:
        for w in (self.headline, self.details, self.explanation, self.extra):
            w.grid_remove()

    def _compare(self) -> None:
        first = self._by_label.get(self.first_menu.get())
        second = self._by_label.get(self.second_menu.get())
        try:
            res = compare_observations(first, second)
        except ComparisonError as exc:
            self._hide_result()
            self._say(str(exc), "error")
            return
        self._say("", "info")

        def describe(name, o):
            sim = "  (SIMULATED)" if o.origin == "simulated" else ""
            return f"{name}: {o.ip} (IPv{o.version})\n         {o.timestamp} · {o.source}{sim}"

        self.headline.configure(text=res.headline)
        self.details.configure(
            text=describe("Earlier", res.earlier) + "\n" + describe("Later  ", res.later) + f"\nTime between: {format_gap(res.gap_seconds)}"
        )
        sections = [res.explanation]
        if res.notes:
            sections.append("Notes:\n" + "\n".join(f"• {n}" for n in res.notes))
        self.explanation.configure(text="\n\n".join(sections))
        self.extra.configure(
            text="Limitations:\n" + "\n".join(f"• {t}" for t in res.limitations)
            + "\n\nRecommended follow-up checks:\n" + "\n".join(f"• {t}" for t in res.follow_ups)
        )
        self.headline.grid(row=1, column=0, sticky="w", padx=PAD, pady=(0, PAD_SMALL))
        self.details.grid(row=2, column=0, sticky="w", padx=PAD, pady=PAD_SMALL)
        self.explanation.grid(row=3, column=0, sticky="w", padx=PAD, pady=PAD_SMALL)
        self.extra.grid(row=4, column=0, sticky="w", padx=PAD, pady=(PAD_SMALL, PAD))
