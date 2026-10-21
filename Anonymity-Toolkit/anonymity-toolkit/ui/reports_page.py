"""Reports page: choose what to include, preview, and save a TXT or HTML report.

Works offline: it only uses data already saved on this computer.
"""
from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from app.navigation import PAGES
from app.theme import COLORS, FONTS, PAD, PAD_SMALL
from reports.report_generator import ReportError, build_report_data, default_filename, render_report, write_report
from services.privacy_service import summary_counts
from simulator.scenarios import ScenarioDataError, load_scenarios
from ui.base_page import BasePage
from ui.components import Banner, Card

SPEC = next(p for p in PAGES if p.key == "reports")
FORMAT_LABELS = {"Text (.txt)": "txt", "Web page (.html)": "html"}
SCOPE_LABELS = {"All saved observations": None, "Latest 10": 10, "Latest 2": 2}


class ReportsPage(BasePage):
    SPEC = SPEC

    def __init__(self, master, controller):
        super().__init__(master, controller)

        Banner(
            self.body,
            "Reports contain IP addresses and timestamps, which are personal data. Read a report before sharing it, "
            "or tick 'Redact IP addresses'. Passwords and credentials are never included.",
            "warning",
        ).grid(row=0, column=0, sticky="ew", pady=(0, PAD))

        card = Card(self.body, "Report options")
        card.grid(row=1, column=0, sticky="ew", pady=(0, PAD))
        card.columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Format", font=FONTS["body"], text_color=COLORS["text"]).grid(row=1, column=0, padx=PAD, pady=PAD_SMALL, sticky="w")
        self.format_menu = ctk.CTkSegmentedButton(card, values=list(FORMAT_LABELS))
        self.format_menu.set("Text (.txt)")
        self.format_menu.grid(row=1, column=1, padx=(0, PAD), pady=PAD_SMALL, sticky="w")
        ctk.CTkLabel(card, text="Observations", font=FONTS["body"], text_color=COLORS["text"]).grid(row=2, column=0, padx=PAD, pady=PAD_SMALL, sticky="w")
        self.scope_menu = ctk.CTkOptionMenu(card, values=list(SCOPE_LABELS), command=lambda _v: self._refresh_summary())
        self.scope_menu.grid(row=2, column=1, padx=(0, PAD), pady=PAD_SMALL, sticky="w")

        self.proxy_var = ctk.BooleanVar(value=True)
        self.checklist_var = ctk.BooleanVar(value=True)
        self.sim_var = ctk.BooleanVar(value=False)
        self.redact_var = ctk.BooleanVar(value=False)
        for row, (text, var) in enumerate([
            ("Include proxy test results", self.proxy_var),
            ("Include privacy checklist (user-reported / unverified)", self.checklist_var),
            ("Include learning scenario summaries (clearly labelled SIMULATED)", self.sim_var),
            ("Redact IP addresses (replace with [IP-1], [IP-2]…)", self.redact_var),
        ], start=3):
            ctk.CTkCheckBox(card, text=text, variable=var).grid(row=row, column=0, columnspan=2, padx=PAD, pady=PAD_SMALL, sticky="w")

        self.summary = ctk.CTkLabel(card, text="", font=FONTS["small"], text_color=COLORS["text_muted"], anchor="w", justify="left", wraplength=760)
        self.summary.grid(row=7, column=0, columnspan=2, padx=PAD, pady=PAD_SMALL, sticky="w")
        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.grid(row=8, column=0, columnspan=2, padx=PAD, pady=(0, PAD), sticky="w")
        ctk.CTkButton(buttons, text="Preview", command=self._preview).pack(side="left", padx=(0, PAD_SMALL))
        ctk.CTkButton(buttons, text="Save report…", command=self._save).pack(side="left")
        self.status = ctk.CTkLabel(card, text="", font=FONTS["body"], anchor="w", justify="left", wraplength=760)
        self.status.grid(row=9, column=0, columnspan=2, padx=PAD, pady=(0, PAD), sticky="w")

        preview = Card(self.body, "Preview (text version)")
        preview.grid(row=2, column=0, sticky="ew")
        self.preview_box = ctk.CTkTextbox(preview, height=320, font=FONTS["mono"], wrap="word")
        self.preview_box.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, PAD))
        self.preview_box.configure(state="disabled")
        self._refresh_summary()

    def on_show(self) -> None:
        self._refresh_summary()

    def _selected_observations(self) -> list:
        limit = SCOPE_LABELS[self.scope_menu.get()]
        items = list(self.controller.observations)
        return items[-limit:] if limit else items

    def _say(self, text: str, kind: str) -> None:
        colour = {"info": COLORS["text_muted"], "success": COLORS["success"], "error": COLORS["error"]}[kind]
        self.status.configure(text=text, text_color=colour)

    def _refresh_summary(self) -> None:
        c = self.controller
        reviewed = summary_counts(c.checklist)["reviewed"]
        note = "built from saved local data" + ("" if c.network_allowed() else ", no network needed")
        self.summary.configure(
            text=f"Saved: {len(c.observations)} observation(s), {len(c.proxy_results)} proxy test(s), {reviewed} checklist item(s) "
                 f"marked Reviewed. Mode: {c.mode.value} ({note}). Reports are saved where you choose, never inside the app's data folder."
        )

    def _build(self, fmt: str) -> str | None:
        scenarios = None
        if self.sim_var.get():
            try:
                scenarios = load_scenarios()
            except ScenarioDataError as exc:
                self._say(f"Scenarios could not be loaded: {exc}", "error")
                return None
        c = self.controller
        data = build_report_data(
            mode=c.mode.value,
            observations=self._selected_observations(),
            proxy_results=c.proxy_results if self.proxy_var.get() else (),
            checklist_states=c.checklist if self.checklist_var.get() else None,
            scenarios=scenarios,
            redact_ips=self.redact_var.get(),
        )
        return render_report(data, fmt)

    def _preview(self) -> None:
        text = self._build("txt")
        if text is None:
            return
        self.preview_box.configure(state="normal")
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", text)
        self.preview_box.configure(state="disabled")
        self._say("Preview updated.", "info")

    def _save(self) -> None:
        fmt = FORMAT_LABELS[self.format_menu.get()]
        text = self._build(fmt)
        if text is None:
            return
        chosen = filedialog.asksaveasfilename(
            title="Save report",
            defaultextension=f".{fmt}",
            initialfile=default_filename(fmt),
            initialdir=str(Path.home()),
            filetypes=[("Report", f"*.{fmt}")],
        )
        if not chosen:
            return  # user cancelled
        try:
            saved = write_report(chosen, text, forbidden_dir=self.controller.data_directory())
        except ReportError as exc:
            self._say(f"Report not saved: {exc}", "error")
            return
        self._say(f"Report saved to {saved}", "success")
