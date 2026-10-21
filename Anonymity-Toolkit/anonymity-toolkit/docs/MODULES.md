# Module guide

Each entry: responsibility · connections · key functions · how to test · limitations.

**app/tasks.py** — runs slow functions in worker threads; callbacks run only in `poll()` on the GUI thread; rejects
duplicate task names. Used by the controller. Key: `TaskRunner.submit`, `poll`. Test: `tests/test_tasks.py`.
Limit: no cancellation of a running request (timeouts bound it).

**app/controller.py** — mode, network gate, saved data, checklist answers, preferences, navigation. Pages call it;
services never do. Key: `network_allowed`, `run_network_task` (never calls the function when Offline), `add_observation`.
Test: `test_tasks.py`, `test_storage.py`, `test_integration.py`. Limit: single user, single window.

**services/ip_service.py** — one lookup, validation with `ipaddress`, friendly `IpLookupError`. Key: `fetch_public_ip`,
`parse_ip`. Test: `test_ip_service.py`. Limit: trusts one external service's answer.

**services/proxy_service.py** — validates a proxy endpoint and runs one test request; credentials only in memory and
never in results or logs. Key: `parse_proxy_url`, `test_proxy`. Test: `test_proxy_service.py`. Limit: http/https only.

**services/comparison_service.py** — compares two observations and writes qualified explanations. Key:
`compare_observations`. Test: `test_comparison.py`. Limit: cannot see DNS/WebRTC/IPv6 behaviour.

**services/privacy_service.py** — checklist definitions, statuses and findings (no score). Key: `ITEMS`,
`build_findings`, `summary_counts`. Test: `test_privacy_service.py`. Limit: nothing is verified automatically.

**services/redaction.py** — removes credentials from text. Used by logging and reports. Test: `test_redaction.py`.
Limit: pattern based.

**storage/json_store.py** — validated, atomic JSON file; quarantines corrupt files; caps history. Key: `JsonStore`.
Test: `test_storage.py`. Limit: not encrypted.

**simulator/scenarios.py + data/scenarios.json** — loads/validates 7 offline scenarios. Test: `test_simulator.py`.
Limit: simplified models.

**reports/report_generator.py** — builds TXT/HTML reports with separated evidence kinds, redaction, safe writing.
Key: `build_report_data`, `render_text`, `render_html`, `write_report`. Test: `test_reports.py`.
Limit: a snapshot, not proof.

**app/logging_setup.py** — log filter that redacts secrets in messages and tracebacks. Test: `test_redaction.py`.

**ui/** — pages and widgets. No network logic. Test manually with `docs/MANUAL_TESTING.md`; `test_gui_smoke.py` opens
each page when a display is available.
