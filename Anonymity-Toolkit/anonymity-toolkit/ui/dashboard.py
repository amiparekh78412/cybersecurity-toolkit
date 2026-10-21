"""Dashboard: honest overview built only from real, saved data."""
from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from app.navigation import PAGES
from app.theme import COLORS, FONTS, PAD, PAD_SMALL
from services.comparison_service import format_gap, seconds_since
from ui.base_page import BasePage
from ui.components import Banner, Card

SPEC = next(p for p in PAGES if p.key == "dashboard")
STALE_AFTER_S = 3600


class DashboardPage(BasePage):
    SPEC = SPEC

    def __init__(self, master, controller):
        super().__init__(master, controller)

        status = Card(self.body, "Status")
        status.grid(row=0, column=0, sticky="ew", pady=(0, PAD))
        self.status_text = ctk.CTkLabel(status, text="", font=FONTS["mono"], text_color=COLORS["text"], anchor="w", justify="left", wraplength=760)
        self.status_text.grid(row=1, column=0, sticky="w", padx=PAD, pady=(0, PAD))

        actions = Card(self.body, "Quick actions")
        actions.grid(row=1, column=0, sticky="ew", pady=(0, PAD))
        row = ctk.CTkFrame(actions, fg_color="transparent")
        row.grid(row=1, column=0, sticky="w", padx=PAD, pady=(0, PAD))
        for text, key in [("IP lookup", "ip"), ("Test a proxy", "proxy"), ("Compare observations", "comparison"), ("Privacy checklist", "privacy")]:
            ctk.CTkButton(row, text=text, command=lambda k=key: self.controller.go_to(k)).pack(side="left", padx=(0, PAD_SMALL))

        data = Card(self.body, "Local data")
        data.grid(row=2, column=0, sticky="ew", pady=(0, PAD))
        self.data_text = ctk.CTkLabel(data, text="", font=FONTS["body"], text_color=COLORS["text"], anchor="w", justify="left", wraplength=760)
        self.data_text.grid(row=1, column=0, sticky="w", padx=PAD, pady=(0, PAD_SMALL))
        self.warning_text = ctk.CTkLabel(data, text="", font=FONTS["body"], text_color=COLORS["warning"], anchor="w", justify="left", wraplength=760)
        self.warning_text.grid(row=2, column=0, sticky="w", padx=PAD)
        ctk.CTkButton(data, text="Clear saved history", fg_color=COLORS["error"], hover_color=COLORS["error"], command=self._clear).grid(
            row=3, column=0, sticky="w", padx=PAD, pady=PAD
        )

        Banner(
            self.body,
            "Educational tool. It reports what a lookup service observed and cannot guarantee anonymity, verify "
            "every VPN setting or detect every privacy leak.",
            "warning",
        ).grid(row=3, column=0, sticky="ew")

        controller.on_mode_change(lambda _m: self.refresh())
        self.refresh()

    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        c = self.controller
        last = c.last_observation()
        if last is None:
            last_text = "none yet (run an IP lookup in Online mode)"
        else:
            age = seconds_since(last.timestamp)
            stale = "  [STALE: older than 1 hour]" if (age is not None and age > STALE_AFTER_S) else ""
            ago = f", {format_gap(age)} ago" if age is not None else ""
            last_text = f"{last.ip} (IPv{last.version}) from {last.source}{ago}{stale}"
        stamp = c.last_diagnostic_timestamp() or "none yet"
        self.status_text.configure(
            text=(
                f"Mode                  : {c.mode.value}\n"
                f"Latest IP observation : {last_text}\n"
                f"Last diagnostic       : {stamp}\n"
                f"Saved observations    : {len(c.observations)}\n"
                f"Saved proxy tests     : {len(c.proxy_results)}"
            )
        )
        self.data_text.configure(
            text=f"Saved only on this computer, never sent anywhere:\n{c.data_location()}\nIt contains IP addresses and timestamps (no proxy credentials)."
        )
        self.warning_text.configure(text="\n".join(c.load_warnings))

    def _clear(self) -> None:
        if not messagebox.askyesno("Clear saved history", "Delete all saved IP observations and proxy test results?"):
            return
        error = self.controller.clear_history()
        self.controller.load_warnings = []
        self.refresh()
        if error:
            messagebox.showwarning("Clear saved history", error)
