"""End-to-end tests of everything except the GUI widgets (no real network is used)."""
import socket
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import requests

from app.controller import Controller, Mode
from reports.report_generator import build_report_data, render_html, render_text, write_report
from services.comparison_service import compare_observations
from services.ip_service import fetch_public_ip
from services.proxy_service import parse_proxy_url, test_proxy
from simulator.scenarios import load_scenarios
from storage.json_store import JsonStore

test_proxy.__test__ = False


def fake_session(text="203.0.113.7", exc=None):
    s = mock.MagicMock()
    if exc:
        s.get.side_effect = exc
    else:
        s.get.return_value = mock.MagicMock(status_code=200, text=text)
    return s


def drain(controller, expected=1, timeout=2.0):
    done, end = 0, time.time() + timeout
    while done < expected and time.time() < end:
        done += controller.tasks.poll()
        time.sleep(0.01)
    return done


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_full_workflow_lookup_compare_checklist_report_restart(self):
        c = Controller(JsonStore(self.root / "data"))
        c.set_mode(Mode.ONLINE)
        for ip in ("203.0.113.7", "198.51.100.4"):
            self.assertTrue(c.run_network_task("ip", lambda ip=ip: fetch_public_ip(fake_session(ip)), on_success=c.add_observation))
            self.assertEqual(drain(c), 1)
        self.assertEqual([o.ip for o in c.observations], ["203.0.113.7", "198.51.100.4"])
        self.assertTrue(compare_observations(*c.observations).ips_differ)

        c.set_checklist_state("vpn_active", "reviewed")
        c.run_network_task("proxy", lambda: test_proxy(parse_proxy_url("http://h.example:80", "u", "PW123"), fake_session("198.51.100.4")),
                           on_success=c.add_proxy_result)
        drain(c)

        data = build_report_data(mode=c.mode.value, observations=c.observations, proxy_results=c.proxy_results,
                                 checklist_states=c.checklist, scenarios=load_scenarios()[:1])
        out_dir = self.root / "reports"
        out_dir.mkdir()
        for fmt, render in (("txt", render_text), ("html", render_html)):
            path = write_report(out_dir / f"r.{fmt}", render(data), forbidden_dir=c.data_directory())
            body = path.read_text(encoding="utf-8")
            self.assertIn("198.51.100.4", body)
            self.assertNotIn("PW123", body)

        saved = (self.root / "data" / "data.json").read_text(encoding="utf-8")
        self.assertNotIn("PW123", saved)

        again = Controller(JsonStore(self.root / "data"))  # simulate restarting the app
        self.assertEqual(len(again.observations), 2)
        self.assertEqual(len(again.proxy_results), 1)
        self.assertEqual(again.checklist, {"vpn_active": "reviewed"})

    def test_failed_lookup_reaches_error_callback_without_saving(self):
        c = Controller(JsonStore(self.root / "data"))
        c.set_mode(Mode.ONLINE)
        errors = []
        c.run_network_task("ip", lambda: fetch_public_ip(fake_session(exc=requests.exceptions.ConnectionError())), on_error=errors.append)
        drain(c)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].kind, "connection")
        self.assertEqual(c.observations, [])

    def test_double_click_does_not_start_duplicate_lookup(self):
        import threading

        c = Controller()
        c.set_mode(Mode.ONLINE)
        gate = threading.Event()
        self.assertTrue(c.run_network_task("ip", gate.wait))
        self.assertFalse(c.run_network_task("ip", lambda: None))
        gate.set()
        drain(c)


class OfflineModeTests(unittest.TestCase):
    def test_offline_mode_refuses_network_tasks_and_never_calls_them(self):
        c = Controller()
        self.assertEqual(c.mode, Mode.OFFLINE)
        called = []
        with mock.patch("requests.sessions.Session.request", side_effect=AssertionError("request attempted")), \
                mock.patch("requests.get", side_effect=AssertionError("request attempted")):
            self.assertFalse(c.run_network_task("ip", lambda: called.append(fetch_public_ip())))
            time.sleep(0.05)
        self.assertEqual(called, [])

    def test_switching_back_to_offline_blocks_again(self):
        c = Controller()
        c.set_mode(Mode.ONLINE)
        self.assertTrue(c.run_network_task("a", lambda: 1))
        drain(c)
        c.set_mode(Mode.OFFLINE)
        self.assertFalse(c.run_network_task("b", lambda: 1))

    def test_every_offline_feature_works_with_networking_blocked(self):
        def blocked(*a, **k):
            raise AssertionError("network access attempted")

        with tempfile.TemporaryDirectory() as tmp, mock.patch("socket.socket", side_effect=blocked), \
                mock.patch("socket.create_connection", side_effect=blocked), mock.patch("socket.getaddrinfo", side_effect=blocked):
            c = Controller(JsonStore(Path(tmp) / "data"))
            self.assertEqual(len(load_scenarios()), 7)                       # simulator
            self.assertIsNone(c.set_checklist_state("dns_review", "reviewed"))  # checklist
            data = build_report_data(mode="Offline", observations=c.observations, checklist_states=c.checklist)
            out = write_report(Path(tmp) / "r.txt", render_text(data))       # reports
            self.assertTrue(out.exists())
            self.assertIsNone(c.clear_history())                             # storage


if __name__ == "__main__":
    unittest.main()
