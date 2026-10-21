"""IP Information page: run a lookup and show the result.

Every successful lookup is recorded automatically (this session only), so there
is no label to type and no save button to forget.
"""
from __future__ import annotations

import customtkinter as ctk

from app.navigation import PAGES
from app.theme import COLORS, FONTS, PAD, PAD_SMALL
from services.ip_service import IpLookupError, IpObservation, fetch_public_ip
from ui.base_page import BasePage
from ui.components import Banner, Card, EmptyState

SPEC = next(p for p in PAGES if p.key == "ip")
TASK_NAME = "ip_lookup"


class IpPage(BasePage):
    SPEC = SPEC

    def __init__(self, master, controller):
        super().__init__(master, controller)

        lookup = Card(self.body, "Public IP lookup")
        lookup.grid(row=0, column=0, sticky="ew", pady=(0, PAD))
        self.lookup_button = ctk.CTkButton(lookup, text="Look up my public IP", font=FONTS["body"], command=self._start_lookup)
        self.lookup_button.grid(row=1, column=0, sticky="w", padx=PAD, pady=PAD_SMALL)
        self.status = ctk.CTkLabel(lookup, text="", font=FONTS["body"], anchor="w", justify="left", wraplength=700)
        self.status.grid(row=2, column=0, sticky="ew", padx=PAD, pady=(0, PAD))

        self.result_card = Card(self.body, "Result (OBSERVED)")
        self.result_card.grid(row=1, column=0, sticky="ew", pady=(0, PAD))
        self.result_empty = EmptyState(self.result_card, "No lookup yet", "Press the button above in Online mode.")
        self.result_empty.grid(row=1, column=0)
        self.result_text = ctk.CTkLabel(
            self.result_card, text="", font=FONTS["mono"], text_color=COLORS["text"], anchor="w", justify="left"
        )
        self.record_note = ctk.CTkLabel(self.result_card, text="", font=FONTS["small"], text_color=COLORS["text_muted"], anchor="w")

        Banner(
            self.body,
            "Note: a lookup shows what one server saw at one moment. A changed address does not prove "
            "you are anonymous, and an unchanged one does not prove a VPN is off.",
            "warning",
        ).grid(row=2, column=0, sticky="ew")

        controller.on_mode_change(lambda _m: self._refresh_controls())
        self._refresh_controls()

    def on_show(self) -> None:
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        busy = self.controller.tasks.is_busy(TASK_NAME)
        online = self.controller.network_allowed()
        self.lookup_button.configure(state="normal" if (online and not busy) else "disabled")
        if not online:
            self._set_status("Offline mode: no network requests are made. Switch to Online to run a lookup.", "warning")
        elif not busy and self.status.cget("text").startswith("Offline mode"):
            self._set_status("", "info")

    def _set_status(self, text: str, kind: str) -> None:
        colour = {"info": COLORS["text_muted"], "success": COLORS["success"], "warning": COLORS["warning"], "error": COLORS["error"]}[kind]
        self.status.configure(text=text, text_color=colour)

    def _start_lookup(self) -> None:
        if not self.controller.network_allowed():
            self._refresh_controls()
            return
        if self.controller.run_network_task(TASK_NAME, fetch_public_ip, self._on_success, self._on_error):
            self.lookup_button.configure(state="disabled", text="Looking up…")
            self._set_status("Contacting the lookup service…", "info")

    def _finish(self) -> None:
        self.lookup_button.configure(text="Look up my public IP")
        self._refresh_controls()

    def _on_success(self, obs: IpObservation) -> None:
        error = self.controller.add_observation(obs)
        self._finish()
        self._set_status("Lookup succeeded.", "success")
        self.result_empty.grid_remove()
        self.result_text.configure(
            text=(
                f"IP address : {obs.ip}\nIP version : IPv{obs.version}\nTimestamp  : {obs.timestamp}\n"
                f"Source     : {obs.source}\nElapsed    : {obs.elapsed_ms} ms"
            )
        )
        self.result_text.grid(row=2, column=0, sticky="w", padx=PAD, pady=PAD_SMALL)
        number = len(self.controller.observations)
        if error:
            self.record_note.configure(text=f"Observation #{number} is kept for this session only. {error}", text_color=COLORS["warning"])
        else:
            self.record_note.configure(
                text=f"Saved as observation #{number} in {self.controller.data_location()}", text_color=COLORS["text_muted"]
            )
        self.record_note.grid(row=3, column=0, sticky="w", padx=PAD, pady=(0, PAD))

    def _on_error(self, exc: BaseException) -> None:
        self._finish()
        if isinstance(exc, IpLookupError):
            self._set_status(f"Lookup failed: {exc}", "error")
        else:
            self._set_status("Lookup failed unexpectedly. Please try again.", "error")
