"""Safe background work: worker thread + queue, results delivered on the main thread.

Responsibility:
    Run slow functions (network calls) off the GUI thread without freezing the
    window, and hand results back so callbacks run ONLY when `poll()` is called.
    The GUI calls `poll()` from `widget.after(...)`, so every callback executes
    on the main thread. Worker threads never touch widgets.

Also prevents duplicate runs: submitting a task name that is still running is
rejected, which protects against repeated button clicks.

This module has no GUI imports so it can be unit-tested directly.
"""
from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from typing import Any, Callable

log = logging.getLogger(__name__)


@dataclass
class _Result:
    name: str
    value: Any = None
    error: BaseException | None = None
    on_success: Callable[[Any], None] | None = None
    on_error: Callable[[BaseException], None] | None = None


class TaskRunner:
    def __init__(self) -> None:
        self._results: "queue.Queue[_Result]" = queue.Queue()
        self._running: set[str] = set()
        self._lock = threading.Lock()
        self._closed = False

    def is_busy(self, name: str) -> bool:
        with self._lock:
            return name in self._running

    def submit(
        self,
        name: str,
        func: Callable[[], Any],
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> bool:
        """Start `func` in a worker thread. Returns False if `name` is already running."""
        with self._lock:
            if self._closed or name in self._running:
                return False
            self._running.add(name)

        def worker() -> None:
            result = _Result(name=name, on_success=on_success, on_error=on_error)
            try:
                result.value = func()
            except BaseException as exc:  # boundary: never let a thread die silently
                log.warning("Task %s failed: %s", name, type(exc).__name__)
                result.error = exc
            self._results.put(result)

        threading.Thread(target=worker, name=f"task-{name}", daemon=True).start()
        return True

    def poll(self) -> int:
        """Run callbacks for finished tasks. Call from the GUI thread. Returns count handled."""
        handled = 0
        while True:
            try:
                result = self._results.get_nowait()
            except queue.Empty:
                break
            with self._lock:
                self._running.discard(result.name)
            handled += 1
            if self._closed:
                continue  # window is closing; drop results
            try:
                if result.error is not None:
                    if result.on_error:
                        result.on_error(result.error)
                elif result.on_success:
                    result.on_success(result.value)
            except Exception:
                log.exception("Callback for task %s raised", result.name)
        return handled

    def close(self) -> None:
        """Stop accepting work and drop pending results (called on window close)."""
        with self._lock:
            self._closed = True
