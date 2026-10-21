"""Offline learning scenarios.

Responsibility:
    Load and validate the educational scenarios in data/scenarios.json and expose
    them as typed objects for the Learning Simulator page.

Offline guarantee:
    This module only reads a local file. It never opens a network connection,
    never changes system settings and never reads live diagnostic data. Every
    scenario is SIMULATED; keep it visually separate from real observations.

Limitations:
    The scenarios are simplified models. Real products differ in details.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

SIMULATED_LABEL = "SIMULATED"
SIMULATION_NOTICE = (
    "Educational illustration only. This is not live data. Nothing is sent over the network "
    "and no settings on your computer are changed."
)
PROTECTION_LABELS = {
    "encrypted": "Encrypted",
    "tunnel": "VPN tunnel / encrypted DNS",
    "partial": "Partly visible",
    "plain": "Readable on the path",
    "failed": "Tunnel down / blocked",
    "info": "Information",
}
EXPECTED_COUNT = 7


class ScenarioDataError(Exception):
    """The scenario file is missing or invalid."""


@dataclass(frozen=True)
class Link:
    label: str
    protection: str


@dataclass(frozen=True)
class Flow:
    title: str
    nodes: tuple[str, ...]
    links: tuple[Link, ...]


@dataclass(frozen=True)
class Party:
    name: str
    can_see: tuple[str, ...]
    cannot_see: tuple[str, ...]


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    summary: str
    assumptions: tuple[str, ...]
    flows: tuple[Flow, ...]
    parties: tuple[Party, ...]
    protects: tuple[str, ...]
    does_not_protect: tuple[str, ...]
    recommendations: tuple[str, ...]
    simulated: bool = True  # always: scenarios are never live data


def default_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "scenarios.json"


def _text(obj: dict, key: str, where: str) -> str:
    value = obj.get(key) if isinstance(obj, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ScenarioDataError(f"{where}: '{key}' must be non-empty text.")
    return value


def _texts(obj: dict, key: str, where: str, allow_empty: bool = False) -> tuple[str, ...]:
    value = obj.get(key) if isinstance(obj, dict) else None
    if not isinstance(value, list) or (not value and not allow_empty) or not all(isinstance(v, str) and v.strip() for v in value):
        raise ScenarioDataError(f"{where}: '{key}' must be a non-empty list of text.")
    return tuple(value)


def _list(obj: dict, key: str, where: str) -> list:
    value = obj.get(key) if isinstance(obj, dict) else None
    if not isinstance(value, list) or not value:
        raise ScenarioDataError(f"{where}: '{key}' must be a non-empty list.")
    return value


def _parse_flow(raw: dict, where: str) -> Flow:
    nodes = _texts(raw, "nodes", where)
    links = []
    for item in _list(raw, "links", where):
        protection = item.get("protection") if isinstance(item, dict) else None
        if protection not in PROTECTION_LABELS:
            raise ScenarioDataError(f"{where}: unknown protection '{protection}'.")
        links.append(Link(_text(item, "label", where), protection))
    if len(nodes) != len(links) + 1:
        raise ScenarioDataError(f"{where}: a flow needs exactly one more node than links.")
    return Flow(_text(raw, "title", where), nodes, tuple(links))


def _parse_scenario(raw: dict) -> Scenario:
    where = f"scenario '{raw.get('id', '?')}'" if isinstance(raw, dict) else "scenario"
    flows = tuple(_parse_flow(f, f"{where} flow") for f in _list(raw, "flows", where))
    parties = tuple(
        Party(_text(p, "name", where), _texts(p, "can_see", where), _texts(p, "cannot_see", where, allow_empty=True))
        for p in _list(raw, "parties", where)
    )
    return Scenario(
        id=_text(raw, "id", where),
        title=_text(raw, "title", where),
        summary=_text(raw, "summary", where),
        assumptions=_texts(raw, "assumptions", where),
        flows=flows,
        parties=parties,
        protects=_texts(raw, "protects", where),
        does_not_protect=_texts(raw, "does_not_protect", where),
        recommendations=_texts(raw, "recommendations", where),
    )


def load_scenarios(path: Path | str | None = None) -> list[Scenario]:
    """Read and validate the scenario file. Raises ScenarioDataError on any problem."""
    file = Path(path) if path is not None else default_path()
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ScenarioDataError(f"Scenario file not found: {file.name}") from None
    except (OSError, ValueError):
        raise ScenarioDataError(f"Scenario file could not be read: {file.name}") from None
    raw_list = data.get("scenarios") if isinstance(data, dict) else None
    if not isinstance(raw_list, list) or not raw_list:
        raise ScenarioDataError("Scenario file has no scenarios.")
    scenarios = [_parse_scenario(item) for item in raw_list]
    ids = [s.id for s in scenarios]
    if len(set(ids)) != len(ids):
        raise ScenarioDataError("Scenario ids must be unique.")
    return scenarios
