"""Base class for every page: title header, scrollable body, lifecycle hook.

The page itself is a plain CTkFrame so hiding/showing it when the user switches
tabs is reliable. The scrollable area lives INSIDE it and is never hidden on its
own (hiding a CTkScrollableFrame directly can leave its canvas out of sync).
"""
from __future__ import annotations

import customtkinter as ctk

from app.controller import Controller
from app.navigation import PageSpec
from app.theme import COLORS, FONTS, PAD, PAD_SMALL


class BasePage(ctk.CTkFrame):
    """Subclasses add widgets to `self.body` and may override `on_show`."""

    SPEC: PageSpec

    def __init__(self, master, controller: Controller):
        super().__init__(master, fg_color=COLORS["bg"], corner_radius=0)
        self.controller = controller
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            scroll, text=self.SPEC.title, font=FONTS["title"], text_color=COLORS["text"], anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 0))
        ctk.CTkLabel(
            scroll, text=self.SPEC.subtitle, font=FONTS["body"], text_color=COLORS["text_muted"], anchor="w"
        ).grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, PAD_SMALL))

        self.body = ctk.CTkFrame(scroll, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew", padx=PAD, pady=PAD_SMALL)
        self.body.columnconfigure(0, weight=1)

    def on_show(self) -> None:
        """Called each time the page becomes visible. Override to refresh data."""
