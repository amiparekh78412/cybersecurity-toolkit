"""Application controller: shared state, persistence and the task runner.

Responsibility:
    * Current mode (Online/Offline) and the network gate `network_allowed()`.
    * Holds saved observations / proxy results and writes them through JsonStore.
    * Runs background tasks (see app/tasks.py).

Connections:
    ui/* pages receive the controller. services/* never import it. With
    store=None (used by tests) nothing is persisted.
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Callable

from services.comparison_service import parse_timestamp
from services.ip_service import IpObservation
from services.privacy_service import STATUS_LABELS, ITEM_IDS, clean_states
from services.proxy_service import ProxyTestResult
from app.tasks import TaskRunner
from storage.json_store import MAX_ENTRIES, JsonStore, StorageError

log = logging.getLogger(__name__)


class Mode(str, Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"


class Controller:
    def __init__(self, store: JsonStore | None = None) -> None:
        self._mode = Mode.OFFLINE  # safe default: no network until the user opts in
        self._mode_listeners: list[Callable[[Mode], None]] = []
        self.tasks = TaskRunner()
        self.store = store
        self.navigate: Callable[[str], None] | None = None  # set by the main window
        self._prefs: dict[str, str] = {}
        self.observations: list[IpObservation] = []
        self.proxy_results: list[ProxyTestResult] = []
        self.load_warnings: list[str] = []
        self.checklist: dict[str, str] = {}
        if store is not None:
            self.observations = [IpObservation(**d) for d in store.observations()]
            self.proxy_results = [ProxyTestResult(**d) for d in store.proxy_results()]
            self.load_warnings = list(store.load_warnings)
            self.checklist = clean_states(store.checklist())

    # ----- mode -----
    @property
    def mode(self) -> Mode:
        return self._mode

    def set_mode(self, mode: Mode) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        for listener in list(self._mode_listeners):
            listener(mode)

    def on_mode_change(self, listener: Callable[[Mode], None]) -> None:
        self._mode_listeners.append(listener)

    def network_allowed(self) -> bool:
        """True only in Online mode. Every network-using feature must check this."""
        return self._mode is Mode.ONLINE

    # ----- persistence helper -----
    @staticmethod
    def _persist(action: Callable[[], None]) -> str | None:
        """Run a store action. Returns a user-friendly error text, or None on success."""
        try:
            action()
            return None
        except StorageError as exc:
            return str(exc)

    def data_location(self) -> str:
        return str(self.store.path) if self.store else "Nothing is saved to disk (memory only)."

    # ----- observations -----
    def add_observation(self, obs: IpObservation) -> str | None:
        self.observations = (self.observations + [obs])[-MAX_ENTRIES:]
        if self.store is None:
            return None
        return self._persist(lambda: self.store.add_observation(obs.to_dict()))

    def add_proxy_result(self, result: ProxyTestResult) -> str | None:
        self.proxy_results = (self.proxy_results + [result])[-MAX_ENTRIES:]
        if self.store is None:
            return None
        return self._persist(lambda: self.store.add_proxy_result(result.to_dict()))

    def last_observation(self) -> IpObservation | None:
        return self.observations[-1] if self.observations else None

    def last_diagnostic_timestamp(self) -> str | None:
        """Newest timestamp among saved observations and proxy tests, or None."""
        stamps = [o.timestamp for o in self.observations] + [p.timestamp for p in self.proxy_results]
        dated = [(parse_timestamp(s), s) for s in stamps]
        dated = [(d, s) for d, s in dated if d is not None]
        return max(dated)[1] if dated else None

    def clear_history(self) -> str | None:
        self.observations = []
        self.proxy_results = []
        if self.store is None:
            return None
        return self._persist(self.store.clear_history)

    # ----- privacy checklist -----
    def set_checklist_state(self, item_id: str, status: str) -> str | None:
        """Record the user's answer for one item. Returns an error text, or None."""
        if item_id not in ITEM_IDS or status not in STATUS_LABELS:
            return "Unknown checklist item or status."
        self.checklist[item_id] = status
        if self.store is None:
            return None
        return self._persist(lambda: self.store.set_checklist(self.checklist))

    def reset_checklist(self) -> str | None:
        self.checklist = {}
        if self.store is None:
            return None
        return self._persist(lambda: self.store.set_checklist({}))

    # ----- preferences -----
    def get_preference(self, key: str, default: str) -> str:
        return self.store.get_preference(key, default) if self.store else self._prefs.get(key, default)

    def set_preference(self, key: str, value: str) -> str | None:
        if self.store is None:
            self._prefs[key] = value
            return None
        return self._persist(lambda: self.store.set_preference(key, value))

    # ----- navigation -----
    def go_to(self, page_key: str) -> None:
        if self.navigate:
            self.navigate(page_key)

    # ----- background work -----
    def run_task(
        self,
        name: str,
        func: Callable[[], Any],
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> bool:
        return self.tasks.submit(name, func, on_success, on_error)

    def run_network_task(self, name, func, on_success=None, on_error=None) -> bool:
        """Like run_task, but REFUSES to start (and never calls func) unless Online mode is on."""
        if not self.network_allowed():
            return False
        return self.run_task(name, func, on_success, on_error)

    def data_directory(self):
        return self.store.directory if self.store else None

    def shutdown(self) -> None:
        self.tasks.close()
