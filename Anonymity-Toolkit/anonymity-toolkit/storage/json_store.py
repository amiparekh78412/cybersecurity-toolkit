"""Local JSON storage.

Responsibility:
    Keep a small, validated JSON file with preferences, saved IP observations,
    proxy test results and checklist states. Nothing else is stored, and nothing
    is ever sent anywhere.

Safety features:
    * Missing file  -> start with defaults.
    * Corrupted / wrong-shape file -> renamed to data.corrupt-<time>.json
      (so nothing is silently destroyed) and defaults are used, with a warning.
    * Every entry is validated on load AND on save; invalid entries are dropped
      and only known fields are kept (an unexpected "password" field is stripped).
    * Proxy entries whose address contains credentials ("@") are rejected.
    * Writes are atomic (temp file + fsync + os.replace) so a crash cannot leave
      a half-written file.
    * History is capped at MAX_ENTRIES per list.

Limitations:
    Plain JSON, not encrypted. Anyone with access to your user account can read
    it. It holds IP addresses and timestamps, so treat it as personal data.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

FORMAT_VERSION = 1
MAX_ENTRIES = 200
MAX_FILE_BYTES = 5_000_000
FILE_NAME = "data.json"
ENV_VAR = "ANONYMITY_TOOLKIT_HOME"
ALLOWED_ORIGINS = {"observed", "simulated"}
ALLOWED_PREFERENCES = {"appearance": {"light", "dark"}}


class StorageError(Exception):
    """A save failed. str(error) is safe to show to the user."""


def default_directory() -> Path:
    override = os.environ.get(ENV_VAR)
    return Path(override) if override else Path.home() / ".anonymity_toolkit"


# ---------- validation helpers ----------
def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_text(value: Any, limit: int = 300) -> bool:
    return isinstance(value, str) and len(value) <= limit


def _is_iso(value: Any) -> bool:
    if not _is_text(value, 64):
        return False
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def _valid_ip(value: Any) -> ipaddress._BaseAddress | None:
    try:
        return ipaddress.ip_address(value) if _is_text(value, 64) else None
    except ValueError:
        return None


def clean_observation(raw: Any) -> dict | None:
    """Return a sanitised copy of an IP observation, or None if invalid."""
    if not isinstance(raw, dict):
        return None
    addr = _valid_ip(raw.get("ip"))
    if addr is None or raw.get("version") != addr.version or isinstance(raw.get("version"), bool):
        return None
    if not (_is_iso(raw.get("timestamp")) and _is_text(raw.get("source")) and _is_number(raw.get("elapsed_ms"))):
        return None
    origin = raw.get("origin", "observed")
    if origin not in ALLOWED_ORIGINS:
        return None
    return {
        "ip": str(addr),
        "version": addr.version,
        "timestamp": raw["timestamp"],
        "source": raw["source"],
        "elapsed_ms": raw["elapsed_ms"],
        "origin": origin,
    }


def clean_proxy_result(raw: Any) -> dict | None:
    """Return a sanitised copy of a proxy test result, or None if invalid."""
    if not isinstance(raw, dict):
        return None
    if not isinstance(raw.get("success"), bool):
        return None
    if not all(_is_text(raw.get(k)) for k in ("stage", "message", "proxy")):
        return None
    if "@" in raw["proxy"] or "@" in raw["message"]:  # credentials must never reach the file
        return None
    if not (_is_number(raw.get("elapsed_ms")) and _is_iso(raw.get("timestamp"))):
        return None
    status = raw.get("http_status")
    if status is not None and (not isinstance(status, int) or isinstance(status, bool)):
        return None
    egress = raw.get("egress_ip")
    if egress is not None and _valid_ip(egress) is None:
        return None
    destination = raw.get("destination", "")
    origin = raw.get("origin", "observed")
    if not _is_text(destination) or origin not in ALLOWED_ORIGINS:
        return None
    return {
        "success": raw["success"],
        "stage": raw["stage"],
        "message": raw["message"],
        "proxy": raw["proxy"],
        "elapsed_ms": raw["elapsed_ms"],
        "timestamp": raw["timestamp"],
        "http_status": status,
        "egress_ip": egress,
        "destination": destination,
        "origin": origin,
    }


def _clean_list(raw: Any, cleaner) -> tuple[list[dict], int]:
    if not isinstance(raw, list):
        return [], 0
    kept = [c for c in (cleaner(item) for item in raw) if c is not None]
    return kept[-MAX_ENTRIES:], len(raw) - len(kept)


def _clean_checklist(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if _is_text(k, 64) and _is_text(v, 40)}


def _clean_preferences(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if k in ALLOWED_PREFERENCES and v in ALLOWED_PREFERENCES[k]}


class JsonStore:
    def __init__(self, directory: Path | str | None = None) -> None:
        self.directory = Path(directory) if directory is not None else default_directory()
        self.path = self.directory / FILE_NAME
        self.load_warnings: list[str] = []
        self._data = self._empty()
        self._load()

    @staticmethod
    def _empty() -> dict:
        return {"version": FORMAT_VERSION, "preferences": {}, "observations": [], "proxy_results": [], "checklist": {}}

    # ----- loading -----
    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            if self.path.stat().st_size > MAX_FILE_BYTES:
                raise ValueError("file too large")
            parsed = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("unexpected structure")
        except (ValueError, UnicodeDecodeError):  # JSONDecodeError is a ValueError
            self._quarantine()
            return
        except OSError as exc:
            log.warning("Could not read %s: %s", self.path, type(exc).__name__)
            self.load_warnings.append("The saved data file could not be read, so the app started with empty history.")
            return

        observations, dropped_a = _clean_list(parsed.get("observations"), clean_observation)
        proxies, dropped_b = _clean_list(parsed.get("proxy_results"), clean_proxy_result)
        self._data.update(
            observations=observations,
            proxy_results=proxies,
            checklist=_clean_checklist(parsed.get("checklist")),
            preferences=_clean_preferences(parsed.get("preferences")),
        )
        if dropped_a + dropped_b:
            self.load_warnings.append(f"{dropped_a + dropped_b} invalid saved entr{'y was' if dropped_a + dropped_b == 1 else 'ies were'} ignored.")

    def _quarantine(self) -> None:
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup = self.path.with_name(f"data.corrupt-{stamp}.json")
        try:
            os.replace(self.path, backup)
            self.load_warnings.append(f"The saved data file was damaged. It was kept as {backup.name} and the app started with empty history.")
        except OSError:
            self.load_warnings.append("The saved data file was damaged and could not be moved aside. The app started with empty history.")

    # ----- saving -----
    def _write(self) -> None:
        tmp_name = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(dir=self.directory, prefix="data-", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._data, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
        except OSError as exc:
            if tmp_name:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
            log.warning("Saving failed: %s", type(exc).__name__)
            raise StorageError("The data file could not be written. Check that the folder exists and is writable.") from None

    # ----- public API -----
    def observations(self) -> list[dict]:
        return [dict(o) for o in self._data["observations"]]

    def proxy_results(self) -> list[dict]:
        return [dict(p) for p in self._data["proxy_results"]]

    def checklist(self) -> dict[str, str]:
        return dict(self._data["checklist"])

    def get_preference(self, key: str, default: str) -> str:
        return self._data["preferences"].get(key, default)

    def add_observation(self, raw: dict) -> None:
        cleaned = clean_observation(raw)
        if cleaned is None:
            raise StorageError("The observation was not valid and was not saved.")
        self._data["observations"] = (self._data["observations"] + [cleaned])[-MAX_ENTRIES:]
        self._write()

    def add_proxy_result(self, raw: dict) -> None:
        cleaned = clean_proxy_result(raw)
        if cleaned is None:
            raise StorageError("The proxy result was not valid and was not saved.")
        self._data["proxy_results"] = (self._data["proxy_results"] + [cleaned])[-MAX_ENTRIES:]
        self._write()

    def set_preference(self, key: str, value: str) -> None:
        if key not in ALLOWED_PREFERENCES or value not in ALLOWED_PREFERENCES[key]:
            raise StorageError("Unknown preference.")
        self._data["preferences"][key] = value
        self._write()

    def set_checklist(self, states: dict[str, str]) -> None:
        self._data["checklist"] = _clean_checklist(states)
        self._write()

    def clear_history(self) -> None:
        """Remove saved observations and proxy results (preferences and checklist stay)."""
        self._data["observations"] = []
        self._data["proxy_results"] = []
        self._write()
