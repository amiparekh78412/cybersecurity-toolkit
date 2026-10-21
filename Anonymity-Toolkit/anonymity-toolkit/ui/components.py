"""Small reusable widgets: Card, StatusBadge, EmptyState, Banner."""
from __future__ import annotations

import customtkinter as ctk

from app.theme import BADGE_TEXT, COLORS, FONTS, PAD, PAD_SMALL


class Card(ctk.CTkFrame):
    """A bordered panel with an optional heading."""

    def __init__(self, master, heading: str | None = None, **kwargs):
        super().__init__(
            master,
            fg_color=COLORS["card"],
            border_color=COLORS["card_border"],
            border_width=1,
            corner_radius=10,
            **kwargs,
        )
        self.columnconfigure(0, weight=1)
        if heading:
            ctk.CTkLabel(
                self, text=heading, font=FONTS["heading"], text_color=COLORS["text"], anchor="w"
            ).grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, PAD_SMALL))


class StatusBadge(ctk.CTkLabel):
    """Coloured pill showing a state such as Online / Offline / SIMULATED."""

    def __init__(self, master, text: str = "", color: str = COLORS["offline"], **kwargs):
        super().__init__(
            master,
            text=text,
            font=FONTS["small"],
            text_color=BADGE_TEXT,
            fg_color=color,
            corner_radius=12,
            padx=10,
            pady=2,
            **kwargs,
        )

    def set(self, text: str, color: str) -> None:
        self.configure(text=text, fg_color=color)


class EmptyState(ctk.CTkFrame):
    """Shown when there is no data yet, so blank areas are never ambiguous."""

    def __init__(self, master, message: str, detail: str = ""):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=message, font=FONTS["heading"], text_color=COLORS["text_muted"]).pack(pady=(PAD, 4))
        if detail:
            ctk.CTkLabel(
                self, text=detail, font=FONTS["body"], text_color=COLORS["text_muted"], wraplength=520, justify="center"
            ).pack(pady=(0, PAD))


class Banner(ctk.CTkLabel):
    """One-line message with a semantic colour: info, success, warning, error."""

    _KIND = {
        "info": COLORS["accent"],
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "error": COLORS["error"],
    }

    def __init__(self, master, text: str, kind: str = "info"):
        super().__init__(
            master,
            text=text,
            font=FONTS["body"],
            text_color=self._KIND[kind],
            anchor="w",
            justify="left",
            wraplength=700,
        )
