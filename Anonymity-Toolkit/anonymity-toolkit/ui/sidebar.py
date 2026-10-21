"""Sidebar: page navigation, mode selector and Online/Offline indicator."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.controller import Controller, Mode
from app.navigation import PAGES
from app.theme import COLORS, FONTS, PAD, PAD_SMALL, SIDEBAR_WIDTH
from ui.components import StatusBadge


LIGHT_LABEL = "☀ Light"
DARK_LABEL = "☾ Dark"


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, controller: Controller, on_navigate: Callable[[str], None]):
        super().__init__(master, width=SIDEBAR_WIDTH, fg_color=COLORS["sidebar"], corner_radius=0)
        self.grid_propagate(False)
        self.controller = controller
        self._on_navigate = on_navigate
        self._buttons: dict[str, ctk.CTkButton] = {}

        ctk.CTkLabel(
            self, text="Anonymity\nToolkit", font=FONTS["heading"], text_color=COLORS["text"], justify="left"
        ).grid(row=0, column=0, padx=PAD, pady=(PAD, PAD), sticky="w")

        for row, spec in enumerate(PAGES, start=1):
            btn = ctk.CTkButton(
                self,
                text=spec.title,
                anchor="w",
                font=FONTS["body"],
                fg_color="transparent",
                hover_color=COLORS["card"],
                text_color=COLORS["text"],
                command=lambda key=spec.key: self._on_navigate(key),
            )
            btn.grid(row=row, column=0, padx=PAD_SMALL, pady=2, sticky="ew")
            self._buttons[spec.key] = btn

        spacer_row = len(PAGES) + 1
        self.rowconfigure(spacer_row, weight=1)  # pushes mode controls to the bottom
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Mode", font=FONTS["small"], text_color=COLORS["text_muted"]).grid(
            row=spacer_row + 1, column=0, padx=PAD, sticky="w"
        )
        self.mode_selector = ctk.CTkSegmentedButton(
            self,
            values=[Mode.OFFLINE.value, Mode.ONLINE.value],
            command=self._mode_chosen,
            font=FONTS["small"],
        )
        self.mode_selector.set(controller.mode.value)
        self.mode_selector.grid(row=spacer_row + 2, column=0, padx=PAD_SMALL, pady=PAD_SMALL, sticky="ew")

        self.badge = StatusBadge(self)
        self.badge.grid(row=spacer_row + 3, column=0, padx=PAD, pady=(0, PAD), sticky="w")
        self.badge.grid_configure(pady=(0, PAD_SMALL))
        self.refresh_badge()
        controller.on_mode_change(lambda _mode: self.refresh_badge())

        ctk.CTkLabel(self, text="Appearance", font=FONTS["small"], text_color=COLORS["text_muted"]).grid(
            row=spacer_row + 4, column=0, padx=PAD, sticky="w"
        )
        self.theme_selector = ctk.CTkSegmentedButton(
            self,
            values=[LIGHT_LABEL, DARK_LABEL],
            command=self._theme_chosen,
            font=FONTS["small"],
        )
        saved = controller.get_preference("appearance", "dark")
        self.theme_selector.set(LIGHT_LABEL if saved == "light" else DARK_LABEL)
        self.theme_selector.grid(row=spacer_row + 5, column=0, padx=PAD_SMALL, pady=(PAD_SMALL, PAD), sticky="ew")

    def _mode_chosen(self, value: str) -> None:
        self.controller.set_mode(Mode(value))

    def _theme_chosen(self, value: str) -> None:
        choice = "light" if value == LIGHT_LABEL else "dark"
        ctk.set_appearance_mode(choice)
        self.controller.set_preference("appearance", choice)

    def refresh_badge(self) -> None:
        if self.controller.network_allowed():
            self.badge.set("● ONLINE", COLORS["online"])
        else:
            self.badge.set("● OFFLINE", COLORS["offline"])
        self.mode_selector.set(self.controller.mode.value)

    def highlight(self, key: str) -> None:
        for k, btn in self._buttons.items():
            btn.configure(fg_color=COLORS["card"] if k == key else "transparent")
