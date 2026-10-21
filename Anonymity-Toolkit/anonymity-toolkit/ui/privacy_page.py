"""Privacy Checklist page: guided manual review. Works fully offline.

The app cannot inspect your VPN, DNS or browser, so every status here is what YOU
report. Nothing is scored.
"""
from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from app.navigation import PAGES
from app.theme import COLORS, FONTS, PAD, PAD_SMALL
from services.privacy_service import ITEMS, STATUS_LABELS, build_finding, observation_hint, status_for, summary_counts
from ui.base_page import BasePage
from ui.components import Banner, Card, StatusBadge

SPEC = next(p for p in PAGES if p.key == "privacy")
LABEL_TO_STATUS = {label: key for key, label in STATUS_LABELS.items()}
ORDER = ["Not verified", "Needs review", "Reviewed"]
BADGE_COLOURS = {"reviewed": COLORS["success"], "needs_review": COLORS["warning"], "not_verified": COLORS["offline"]}


class PrivacyPage(BasePage):
    SPEC = SPEC

    def __init__(self, master, controller):
        super().__init__(master, controller)
        self._rows: dict[str, dict] = {}

        Banner(
            self.body,
            "This checklist records what YOU report. The app does not inspect your VPN, DNS or browser, "
            "and it gives no anonymity score. 'Reviewed' means you checked it yourself.",
            "info",
        ).grid(row=0, column=0, sticky="ew", pady=(0, PAD))

        howto = Card(self.body, "How to use this page (30 seconds)")
        howto.grid(row=1, column=0, sticky="ew", pady=(0, PAD))
        ctk.CTkLabel(
            howto, font=FONTS["body"], text_color=COLORS["text"], anchor="w", justify="left", wraplength=760,
            text=(
                "1. Read an item's title and its one-line 'Why it matters'.\n"
                "2. Do the check yourself outside this app (press 'Show details' to see how).\n"
                "3. Come back and set the status:\n"
                "     Reviewed = I checked it.   Needs review = I found a problem or I'm unsure.   Not verified = I haven't checked yet.\n\n"
                "You may leave items as 'Not verified'. This is your personal to-do list, not a test the app grades."
            ),
        ).grid(row=1, column=0, sticky="w", padx=PAD, pady=(0, PAD))

        top = Card(self.body, "Summary")
        top.grid(row=2, column=0, sticky="ew", pady=(0, PAD))
        self.summary = ctk.CTkLabel(top, text="", font=FONTS["body"], text_color=COLORS["text"], anchor="w")
        self.summary.grid(row=1, column=0, sticky="w", padx=PAD, pady=(0, PAD_SMALL))
        self.save_note = ctk.CTkLabel(top, text="", font=FONTS["small"], text_color=COLORS["warning"], anchor="w", justify="left", wraplength=760)
        self.save_note.grid(row=2, column=0, sticky="w", padx=PAD)
        ctk.CTkButton(top, text="Reset checklist", fg_color=COLORS["offline"], command=self._reset).grid(
            row=3, column=0, sticky="w", padx=PAD, pady=PAD
        )

        for index, item in enumerate(ITEMS, start=3):
            self._build_item(index, item)
        self.refresh()

    def on_show(self) -> None:
        self.refresh()

    def _build_item(self, row: int, item) -> None:
        card = Card(self.body, item.title)
        card.grid(row=row, column=0, sticky="ew", pady=(0, PAD))

        control = ctk.CTkFrame(card, fg_color="transparent")
        control.grid(row=1, column=0, sticky="w", padx=PAD, pady=(0, PAD_SMALL))
        badge = StatusBadge(control)
        badge.pack(side="left", padx=(0, PAD))
        selector = ctk.CTkSegmentedButton(control, values=ORDER, command=lambda v, i=item.id: self._chosen(i, v), font=FONTS["small"])
        selector.pack(side="left")

        ctk.CTkLabel(
            card, font=FONTS["body"], text_color=COLORS["text"], anchor="w", justify="left", wraplength=760,
            text=f"Why it matters: {item.purpose}",
        ).grid(row=2, column=0, sticky="w", padx=PAD, pady=PAD_SMALL)

        dynamic = ctk.CTkLabel(card, font=FONTS["body"], text_color=COLORS["accent"], anchor="w", justify="left", wraplength=760)
        dynamic.grid(row=3, column=0, sticky="w", padx=PAD, pady=PAD_SMALL)

        hint = None
        if item.id == "vpn_active":
            hint = ctk.CTkLabel(card, font=FONTS["small"], text_color=COLORS["text_muted"], anchor="w", justify="left", wraplength=760)
            hint.grid(row=4, column=0, sticky="w", padx=PAD)

        details = ctk.CTkLabel(
            card, font=FONTS["body"], text_color=COLORS["text"], anchor="w", justify="left", wraplength=760,
            text=(
                f"Evidence required: {item.evidence_required}\n\nLimitations: {item.limitations}\n\nGuided review:\n"
                + "\n".join(f"{n}. {step}" for n, step in enumerate(item.review_steps, start=1))
            ),
        )
        toggle = ctk.CTkButton(card, text="Show details", width=150)
        toggle.configure(command=lambda d=details, t=toggle: self._toggle_details(d, t))
        toggle.grid(row=5, column=0, sticky="w", padx=PAD, pady=PAD)
        details.grid(row=6, column=0, sticky="w", padx=PAD, pady=(0, PAD))
        details.grid_remove()

        self._rows[item.id] = {"item": item, "badge": badge, "selector": selector, "dynamic": dynamic, "hint": hint}

    @staticmethod
    def _toggle_details(details, button) -> None:
        if details.winfo_ismapped():
            details.grid_remove()
            button.configure(text="Show details")
        else:
            details.grid()
            button.configure(text="Hide details")

    def _chosen(self, item_id: str, label: str) -> None:
        error = self.controller.set_checklist_state(item_id, LABEL_TO_STATUS[label])
        self.save_note.configure(text=f"Your answer is kept for this session only. {error}" if error else "")
        self.refresh()

    def _reset(self) -> None:
        if messagebox.askyesno("Reset checklist", "Set every item back to 'Not verified'?"):
            error = self.controller.reset_checklist()
            self.save_note.configure(text=error or "")
            self.refresh()

    def refresh(self) -> None:
        states = self.controller.checklist
        for item_id, row in self._rows.items():
            status = status_for(states, item_id)
            finding = build_finding(row["item"], status)
            row["badge"].set(finding.status_label, BADGE_COLOURS[status])
            row["selector"].set(finding.status_label)
            row["dynamic"].configure(
                text=f"Evidence type: {finding.evidence_kind.capitalize()}\nRecommended next step: {finding.recommendation}"
            )
            if row["hint"] is not None:
                row["hint"].configure(text=observation_hint(self.controller.observations))
        counts = summary_counts(states)
        self.summary.configure(
            text=f"Reviewed: {counts['reviewed']}   ·   Needs review: {counts['needs_review']}   ·   Not verified: {counts['not_verified']}"
        )
