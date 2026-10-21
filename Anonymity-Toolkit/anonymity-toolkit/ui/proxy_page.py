"""Proxy Tester page: validate input, run one test in the background, show the result."""
from __future__ import annotations

import customtkinter as ctk

from app.navigation import PAGES
from app.theme import COLORS, FONTS, PAD, PAD_SMALL
from services.proxy_service import ProxyTestResult, ProxyValidationError, parse_proxy_url, test_proxy
from ui.base_page import BasePage
from ui.components import Banner, Card, EmptyState

SPEC = next(p for p in PAGES if p.key == "proxy")
TASK_NAME = "proxy_test"

STAGE_TITLES = {
    "ok": "SUCCESS",
    "proxy_connection": "FAILED: proxy connection",
    "proxy_auth": "FAILED: proxy authentication",
    "timeout": "FAILED: timeout",
    "tls": "FAILED: TLS error",
    "destination_http": "FAILED: destination returned an HTTP error (proxy itself worked)",
    "invalid_response": "FAILED: unexpected response",
    "unexpected": "FAILED: unexpected error",
}


class ProxyPage(BasePage):
    SPEC = SPEC

    def __init__(self, master, controller):
        super().__init__(master, controller)

        form = Card(self.body, "Proxy endpoint")
        form.grid(row=0, column=0, sticky="ew", pady=(0, PAD))
        form.columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Proxy URL", font=FONTS["body"], text_color=COLORS["text"]).grid(row=1, column=0, padx=PAD, pady=PAD_SMALL, sticky="w")
        self.url_entry = ctk.CTkEntry(form, placeholder_text="http://proxy.example.com:8080")
        self.url_entry.grid(row=1, column=1, padx=(0, PAD), pady=PAD_SMALL, sticky="ew")

        ctk.CTkLabel(form, text="Username (optional)", font=FONTS["body"], text_color=COLORS["text"]).grid(row=2, column=0, padx=PAD, pady=PAD_SMALL, sticky="w")
        self.user_entry = ctk.CTkEntry(form)
        self.user_entry.grid(row=2, column=1, padx=(0, PAD), pady=PAD_SMALL, sticky="ew")

        ctk.CTkLabel(form, text="Password (optional)", font=FONTS["body"], text_color=COLORS["text"]).grid(row=3, column=0, padx=PAD, pady=PAD_SMALL, sticky="w")
        self.pass_entry = ctk.CTkEntry(form, show="•")
        self.pass_entry.grid(row=3, column=1, padx=(0, PAD), pady=PAD_SMALL, sticky="ew")

        ctk.CTkLabel(
            form,
            text="Credentials stay in memory for this test only. They are never saved, logged or put in reports.",
            font=FONTS["small"], text_color=COLORS["text_muted"], anchor="w",
        ).grid(row=4, column=0, columnspan=2, padx=PAD, sticky="w")

        self.auth_var = ctk.BooleanVar(value=False)
        self.auth_check = ctk.CTkCheckBox(
            form, text="I own this proxy or am authorised to test it", variable=self.auth_var, command=self._refresh_controls
        )
        self.auth_check.grid(row=5, column=0, columnspan=2, padx=PAD, pady=PAD_SMALL, sticky="w")

        self.test_button = ctk.CTkButton(form, text="Test proxy", font=FONTS["body"], command=self._start_test)
        self.test_button.grid(row=6, column=0, columnspan=2, padx=PAD, pady=PAD_SMALL, sticky="w")
        self.status = ctk.CTkLabel(form, text="", font=FONTS["body"], anchor="w", justify="left", wraplength=700)
        self.status.grid(row=7, column=0, columnspan=2, padx=PAD, pady=(0, PAD), sticky="ew")

        self.result_card = Card(self.body, "Result (OBSERVED)")
        self.result_card.grid(row=1, column=0, sticky="ew", pady=(0, PAD))
        self.result_empty = EmptyState(self.result_card, "No test yet", "Enter a proxy you are authorised to test and press Test proxy.")
        self.result_empty.grid(row=1, column=0)
        self.result_title = ctk.CTkLabel(self.result_card, text="", font=FONTS["heading"], anchor="w")
        self.result_text = ctk.CTkLabel(self.result_card, text="", font=FONTS["mono"], text_color=COLORS["text"], anchor="w", justify="left")

        Banner(
            self.body,
            "Note: a successful test shows that one request used the proxy. It does not prove every application "
            "uses it, and it says nothing about DNS or other traffic.",
            "warning",
        ).grid(row=2, column=0, sticky="ew")

        controller.on_mode_change(lambda _m: self._refresh_controls())
        self._refresh_controls()

    def on_show(self) -> None:
        self._refresh_controls()

    def _refresh_controls(self) -> None:
        busy = self.controller.tasks.is_busy(TASK_NAME)
        online = self.controller.network_allowed()
        ready = online and not busy and self.auth_var.get()
        self.test_button.configure(state="normal" if ready else "disabled")
        if not online:
            self._set_status("Offline mode: no network requests are made. Switch to Online to test a proxy.", "warning")
        elif self.status.cget("text").startswith("Offline mode"):
            self._set_status("", "info")

    def _set_status(self, text: str, kind: str) -> None:
        colour = {"info": COLORS["text_muted"], "success": COLORS["success"], "warning": COLORS["warning"], "error": COLORS["error"]}[kind]
        self.status.configure(text=text, text_color=colour)

    def _start_test(self) -> None:
        if not self.controller.network_allowed() or not self.auth_var.get():
            self._refresh_controls()
            return
        try:
            proxy = parse_proxy_url(self.url_entry.get(), self.user_entry.get(), self.pass_entry.get())
        except ProxyValidationError as exc:
            self._set_status(str(exc), "error")
            return
        started = self.controller.run_network_task(TASK_NAME, lambda: test_proxy(proxy), self._on_done, self._on_error)
        if started:
            self.test_button.configure(state="disabled", text="Testing…")
            self._set_status(f"Testing {proxy.safe_url} …", "info")

    def _finish(self) -> None:
        self.pass_entry.delete(0, "end")  # credentials live only for the test
        self.test_button.configure(text="Test proxy")
        self._refresh_controls()

    def _on_done(self, res: ProxyTestResult) -> None:
        save_error = self.controller.add_proxy_result(res)
        self._finish()
        if save_error:
            self._set_status(f"Test finished, but the result could not be saved. {save_error}", "warning")
        else:
            self._set_status("Test finished.", "success" if res.success else "error")
        self.result_empty.grid_remove()
        self.result_title.configure(
            text=STAGE_TITLES.get(res.stage, "RESULT"),
            text_color=COLORS["success"] if res.success else COLORS["error"],
        )
        self.result_title.grid(row=1, column=0, sticky="w", padx=PAD, pady=(0, PAD_SMALL))
        status = res.http_status if res.http_status is not None else "n/a"
        egress = res.egress_ip or "n/a"
        self.result_text.configure(
            text=(
                f"Proxy      : {res.proxy}\nHTTP status: {status}\nElapsed    : {res.elapsed_ms} ms\n"
                f"Egress IP  : {egress}\nDestination: {res.destination}\nTimestamp  : {res.timestamp}\n\n{res.message}"
            )
        )
        self.result_text.grid(row=2, column=0, sticky="w", padx=PAD, pady=(0, PAD))

    def _on_error(self, exc: BaseException) -> None:
        self._finish()
        self._set_status("The test failed unexpectedly. Please try again.", "error")
