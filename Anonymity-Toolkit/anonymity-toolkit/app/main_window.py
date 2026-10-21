"""Main window: sidebar + one visible page at a time.

Pages are created lazily on first visit (fast startup) and then reused.
A 100 ms `after` loop drains the TaskRunner so background results are handled on
the GUI thread. The loop is cancelled when the window closes.
"""
from __future__ import annotations

import logging
import traceback
from tkinter import messagebox

import customtkinter as ctk

from app.controller import Controller
from app.navigation import DEFAULT_PAGE
from services.redaction import redact_credentials
from app.theme import COLORS, MIN_WINDOW
from storage.json_store import JsonStore
from ui.about_page import AboutPage
from ui.comparison_page import ComparisonPage
from ui.dashboard import DashboardPage
from ui.ip_page import IpPage
from ui.privacy_page import PrivacyPage
from ui.proxy_page import ProxyPage
from ui.reports_page import ReportsPage
from ui.sidebar import Sidebar
from ui.simulator_page import SimulatorPage

log = logging.getLogger(__name__)

PAGE_CLASSES = {
    "dashboard": DashboardPage,
    "ip": IpPage,
    "proxy": ProxyPage,
    "comparison": ComparisonPage,
    "privacy": PrivacyPage,
    "simulator": SimulatorPage,
    "reports": ReportsPage,
    "about": AboutPage,
}
POLL_MS = 100


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Anonymity Toolkit")
        self.geometry("1100x720")
        self.minsize(*MIN_WINDOW)
        self.configure(fg_color=COLORS["bg"])

        self.controller = Controller(JsonStore())
        ctk.set_appearance_mode(self.controller.get_preference("appearance", "dark"))
        self.controller.navigate = self.show_page
        self._pages: dict[str, ctk.CTkFrame] = {}
        self._current: str | None = None
        self._poll_job: str | None = None

        # Column 1 (content) stretches when the window is resized; sidebar stays fixed.
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.sidebar = Sidebar(self, self.controller, self.show_page)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.content = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.show_page(DEFAULT_PAGE)
        self._poll_job = self.after(POLL_MS, self._poll)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def show_page(self, key: str) -> None:
        if self._current and self._current in self._pages:
            self._pages[self._current].grid_remove()
        if key not in self._pages:
            self._pages[key] = PAGE_CLASSES[key](self.content, self.controller)
        page = self._pages[key]
        page.grid(row=0, column=0, sticky="nsew")
        page.tkraise()  # make sure this page is on top of any other
        self._current = key
        self.sidebar.highlight(key)
        page.on_show()
        self.update_idletasks()  # force a layout pass so the page draws fully

    def report_callback_exception(self, exc, val, tb) -> None:
        """Last-resort boundary: log safely and show a friendly message, never a traceback."""
        frames = traceback.extract_tb(tb)
        where = f"{frames[-1].filename.split('/')[-1].split(chr(92))[-1]}:{frames[-1].lineno}" if frames else "unknown"
        log.error("Unhandled GUI error %s at %s: %s", exc.__name__, where, redact_credentials(str(val)))
        try:
            messagebox.showerror("Unexpected error", "Something went wrong, but the app is still running.\nDetails (without secrets) were written to the log.")
        except Exception:
            pass

    def _poll(self) -> None:
        self.controller.tasks.poll()
        self._poll_job = self.after(POLL_MS, self._poll)

    def _on_close(self) -> None:
        if self._poll_job is not None:
            self.after_cancel(self._poll_job)
        self.controller.shutdown()
        self.destroy()
