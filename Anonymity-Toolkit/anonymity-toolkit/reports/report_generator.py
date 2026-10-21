"""Report generation (TXT and HTML).

Responsibility:
    Build a report from saved observations, proxy results, checklist answers and
    (optionally) learning scenarios, and write it to a file the user chose.

Information kinds are always kept apart and labelled:
    [OBSERVED]                    measured by a lookup/test request made by this tool
    [USER-REPORTED / UNVERIFIED]  privacy checklist answers (never verified here)
    [SIMULATED]                   educational scenarios, never mixed with live data

Safety:
    * Every string passes through `redact_credentials`; passwords never appear.
    * HTML escapes every dynamic value and loads nothing external.
    * Reports can be refused inside the app's own data folder (`forbidden_dir`),
      keeping reports separate from application configuration.
    * Optional IP redaction swaps each address for a stable [IP-n] token.

Limitations:
    A report is a snapshot of local data, not proof of anonymity.
"""
from __future__ import annotations

import html
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from app import APP_NAME, APP_VERSION
from services.comparison_service import ComparisonError, ComparisonResult, compare_observations, format_gap
from services.ip_service import IpObservation
from services.privacy_service import Finding, build_findings
from services.proxy_service import ProxyTestResult
from services.redaction import redact_credentials

DISCLAIMER = (
    "This report is for education. This tool cannot guarantee anonymity, verify every aspect of VPN routing or "
    "detect every privacy leak. A changed IP address does not prove anonymity."
)
LIMITATIONS = [
    "Observed values are what an external service reported at one moment, not a full picture of your network.",
    "An unchanged IP address does not prove a VPN is inactive, and a changed one does not prove it is configured correctly.",
    "DNS leaks, WebRTC leaks, IPv6 leaks, kill-switch behaviour and operating-system settings are not tested by this tool.",
    "Privacy checklist answers are what you reported. This tool did not verify them.",
    "SIMULATED content is an educational illustration, not a measurement.",
]
KIND_NOTES = [
    "[OBSERVED] = reported by a lookup service or test request made by this tool, at the time shown.",
    "[USER-REPORTED] = a checklist item you marked Reviewed. This tool did not verify it.",
    "[UNVERIFIED] = a checklist item not reviewed or marked Needs review. No evidence was checked.",
    "[SIMULATED] = educational illustration, never a measurement.",
]
ALLOWED_EXTENSIONS = {".txt", ".html", ".htm"}


class ReportError(Exception):
    """Writing the report failed. str(error) is user-friendly."""


@dataclass
class ReportData:
    mode: str
    generated_at: datetime
    observations: list[IpObservation]
    comparison: ComparisonResult | None
    proxy_results: list[ProxyTestResult]
    findings: list[Finding] | None            # None = checklist section not selected
    scenarios: list | None                    # None = simulated section not selected
    recommendations: list[str] = field(default_factory=list)
    redact_ips: bool = False


def build_report_data(
    mode: str,
    observations: Sequence[IpObservation] = (),
    proxy_results: Sequence[ProxyTestResult] = (),
    checklist_states: dict[str, str] | None = None,
    scenarios: Sequence | None = None,
    generated_at: datetime | None = None,
    redact_ips: bool = False,
) -> ReportData:
    observations = list(observations)
    comparison = None
    if len(observations) >= 2:
        try:
            comparison = compare_observations(observations[-2], observations[-1])
        except ComparisonError:
            comparison = None
    findings = build_findings(checklist_states) if checklist_states is not None else None

    recs: list[str] = []
    if comparison:
        recs.extend(comparison.follow_ups)
    if findings:
        recs.extend(f.recommendation for f in findings if f.status != "reviewed")
    recs.append("Treat saved history and reports as personal data: read a report before sharing it, or redact IP addresses.")
    recs.append("Do not rely on a changed IP address alone as evidence of anonymity.")
    seen: set[str] = set()
    recs = [r for r in recs if not (r in seen or seen.add(r))]

    return ReportData(
        mode=mode,
        generated_at=generated_at or datetime.now(timezone.utc),
        observations=observations,
        comparison=comparison,
        proxy_results=list(proxy_results),
        findings=findings,
        scenarios=list(scenarios) if scenarios is not None else None,
        recommendations=recs,
        redact_ips=redact_ips,
    )


# ---------- shared content ----------
Block = tuple[str, str, list[str]]  # (heading, kind label, lines)


def _timestamp(data: ReportData) -> str:
    return data.generated_at.astimezone(timezone.utc).isoformat()


def _blocks(data: ReportData) -> list[Block]:
    blocks: list[Block] = []
    details = [
        f"Application: {APP_NAME} {APP_VERSION}",
        f"Report generated: {_timestamp(data)}",
        f"Operating mode when generated: {data.mode}",
    ]
    if data.redact_ips:
        details.append("IP addresses are redacted; the same [IP-n] token always means the same address.")
    if data.mode.lower() == "offline":
        details.append("Offline mode: built only from data saved on this computer; no network requests were made.")
    blocks.append(("Report details", "", details))
    blocks.append(("How to read this report", "", list(KIND_NOTES)))

    obs_lines = []
    for i, o in enumerate(data.observations, start=1):
        tag = "[SIMULATED]" if o.origin == "simulated" else "[OBSERVED]"
        obs_lines.append(f"{tag} {o.ip} (IPv{o.version}) | {o.timestamp} | source: {o.source} | lookup time: {o.elapsed_ms} ms | #{i}")
    blocks.append(("IP observations", "OBSERVED", obs_lines or ["No observations were selected."]))

    cmp_lines = ["Not available: at least two observations are needed."]
    if data.comparison:
        c = data.comparison
        cmp_lines = [
            c.headline,
            f"Earlier: {c.earlier.ip} at {c.earlier.timestamp} (source: {c.earlier.source})",
            f"Later: {c.later.ip} at {c.later.timestamp} (source: {c.later.source})",
            f"Time between: {format_gap(c.gap_seconds)}",
            c.explanation,
            *[f"Note: {n}" for n in c.notes],
            *[f"Limitation: {t}" for t in c.limitations],
        ]
    blocks.append(("IP comparison", "OBSERVED", cmp_lines))

    proxy_lines = []
    for p in data.proxy_results:
        status = p.http_status if p.http_status is not None else "n/a"
        outcome = "SUCCESS" if p.success else "FAILED"
        proxy_lines.append(
            f"[OBSERVED] {p.proxy} | {outcome} ({p.stage}) | HTTP status: {status} | elapsed: {p.elapsed_ms} ms | "
            f"egress IP: {p.egress_ip or 'n/a'} | {p.timestamp} | {p.message}"
        )
    blocks.append(("Proxy tests (credentials are never recorded)", "OBSERVED", proxy_lines or ["No proxy test results were included."]))

    if data.findings is not None:
        lines = []
        for f in data.findings:
            if f.status == "reviewed":
                lines.append(f"[USER-REPORTED] {f.title}: marked Reviewed by you (not verified by this tool)")
            else:
                lines.append(f"[UNVERIFIED] {f.title}: {f.status_label}. Next step: {f.recommendation}")
        blocks.append(("Privacy checklist", "USER-REPORTED / UNVERIFIED", lines))

    if data.scenarios is not None:
        blocks.append((
            "Learning scenarios (educational, not measurements)", "SIMULATED",
            [f"[SIMULATED] {s.title}: {s.summary}" for s in data.scenarios] or ["No scenarios were selected."],
        ))

    blocks.append(("Recommendations", "", list(data.recommendations)))
    blocks.append(("Limitations and disclaimer", "", [*LIMITATIONS, DISCLAIMER]))
    return blocks


def _finalise(data: ReportData, text: str) -> str:
    """Scrub credentials, then (optionally) replace IP addresses with stable tokens."""
    text = redact_credentials(text)
    if data.redact_ips:
        ordered: list[str] = []
        for ip in [o.ip for o in data.observations] + [p.egress_ip for p in data.proxy_results if p.egress_ip]:
            if ip not in ordered:
                ordered.append(ip)
        for number, ip in enumerate(ordered, start=1):
            pattern = r"(?<![0-9A-Za-z:.])" + re.escape(ip) + r"(?![0-9A-Za-z:]|\.[0-9])"
            text = re.sub(pattern, f"[IP-{number}]", text)
    return text


def render_text(data: ReportData) -> str:
    out = [f"{APP_NAME.upper()} REPORT", "=" * (len(APP_NAME) + 7), ""]
    for heading, kind, lines in _blocks(data):
        title = heading.upper() + (f"  [{kind}]" if kind else "")
        out += [title, "-" * len(title)]
        out += [line if line.startswith("[") else f"- {line}" for line in lines]
        out.append("")
    return _finalise(data, "\n".join(out))


_CSS = """
:root{color-scheme:light dark;--bg:#fff;--fg:#1f2328;--card:#f6f8fa;--bd:#d0d7de}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--card:#161b22;--bd:#30363d}}
body{background:var(--bg);color:var(--fg);font-family:system-ui,Segoe UI,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.5}
section{background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:1rem 1.25rem;margin:1rem 0}
h2{font-size:1.1rem;margin:.2rem 0 .6rem}
.badge{font-size:.7rem;font-weight:700;padding:2px 8px;border-radius:10px;margin-left:.5rem;color:#fff;vertical-align:middle;background:#59636e}
.OBSERVED{background:#1a7f37}.SIMULATED{background:#8250df}.UR{background:#9a6700}
ul{padding-left:1.2rem;margin:0} li{margin:.25rem 0;overflow-wrap:anywhere}
"""


def render_html(data: ReportData) -> str:
    esc = html.escape
    parts = [
        "<!DOCTYPE html>", '<html lang="en"><head><meta charset="utf-8">',
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">",
        f"<title>{esc(APP_NAME)} report</title><style>{_CSS}</style></head><body>",
        f"<h1>{esc(APP_NAME)} report</h1>",
    ]
    for heading, kind, lines in _blocks(data):
        css = "UR" if "/" in kind else kind
        badge = f'<span class="badge {css}">{esc(kind)}</span>' if kind else ""
        parts.append(f"<section><h2>{esc(heading)}{badge}</h2><ul>")
        parts += [f"<li>{esc(line)}</li>" for line in lines]
        parts.append("</ul></section>")
    parts.append("</body></html>")
    return _finalise(data, "\n".join(parts))


def render_report(data: ReportData, fmt: str) -> str:
    if fmt == "txt":
        return render_text(data)
    if fmt == "html":
        return render_html(data)
    raise ValueError(f"Unknown report format: {fmt}")


# ---------- writing ----------
def default_filename(fmt: str, now: datetime | None = None) -> str:
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"anonymity-toolkit-report-{stamp}.{fmt}"


def _inside(path: Path, folder: Path) -> bool:
    try:
        path.resolve().relative_to(folder.resolve())
        return True
    except ValueError:
        return False


def write_report(path: str | Path, content: str, forbidden_dir: str | Path | None = None) -> Path:
    """Write the report safely (temp file, then replace). Raises ReportError with a clear message."""
    if not str(path).strip():
        raise ReportError("No file location was chosen.")
    tmp = None
    try:
        target = Path(path)
        if target.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ReportError("Use a .txt or .html file name.")
        if target.is_dir():
            raise ReportError("That location is a folder. Choose a file name.")
        if not target.parent.is_dir():
            raise ReportError("The folder does not exist.")
        if forbidden_dir is not None and _inside(target.parent, Path(forbidden_dir)):
            raise ReportError("Reports cannot be saved inside the app's data folder. Choose another folder.")
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".report-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp, target)
        tmp = None
        return target
    except ReportError:
        raise
    except PermissionError:
        raise ReportError("You do not have permission to write to that location.") from None
    except (OSError, ValueError):
        raise ReportError("The report could not be written to that location.") from None
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass
