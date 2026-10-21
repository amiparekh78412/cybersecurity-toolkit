import json
import socket
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from reports.report_generator import (
    DISCLAIMER, ReportError, build_report_data, default_filename, render_html, render_report, render_text, write_report,
)
from services.ip_service import IpObservation
from services.proxy_service import ProxyTestResult
from simulator.scenarios import load_scenarios

NOW = datetime(2026, 10, 3, 12, 0, 0, tzinfo=timezone.utc)


def obs(ip, ts, source="api.ipify.org", origin="observed", version=4):
    return IpObservation(ip=ip, version=version, timestamp=ts, source=source, elapsed_ms=12.0, origin=origin)


def proxy(**kw):
    base = dict(success=True, stage="ok", message="A request through the proxy succeeded.", proxy="http://host:8080",
                elapsed_ms=30.0, timestamp="2026-10-03T10:02:00+00:00", http_status=200, egress_ip="198.51.100.4")
    base.update(kw)
    return ProxyTestResult(**base)


A, B = obs("203.0.113.7", "2026-10-03T10:00:00+00:00"), obs("198.51.100.4", "2026-10-03T10:05:00+00:00")


def full_data(**kw):
    args = dict(mode="Online", observations=[A, B], proxy_results=[proxy()], checklist_states={"vpn_active": "reviewed"},
                scenarios=load_scenarios()[:2], generated_at=NOW)
    args.update(kw)
    return build_report_data(**args)


class ContentTests(unittest.TestCase):
    def test_text_report_has_required_parts(self):
        text = render_text(full_data())
        for needle in ["ANONYMITY TOOLKIT REPORT", "2026-10-03T12:00:00+00:00", "Operating mode when generated: Online",
                       "203.0.113.7", "198.51.100.4", "OBSERVED ADDRESS CHANGED", "http://host:8080", "Privacy checklist".upper(),
                       "RECOMMENDATIONS", "LIMITATIONS", DISCLAIMER]:
            self.assertIn(needle, text)

    def test_all_four_evidence_labels_and_separate_simulated_section(self):
        text = render_text(full_data())
        for label in ("[OBSERVED]", "[USER-REPORTED / UNVERIFIED]", "[SIMULATED]"):
            self.assertIn(label, text)
        self.assertIn("USER-REPORTED]", text)   # reviewed item
        self.assertIn("UNVERIFIED]", text)      # un-reviewed items
        sim_start = text.index("LEARNING SCENARIOS")
        self.assertNotIn("203.0.113.7", text[sim_start:text.index("RECOMMENDATIONS")])  # no live data inside simulated section

    def test_simulated_observation_is_labelled(self):
        text = render_text(build_report_data(mode="Offline", observations=[obs("192.0.2.1", "2026-10-03T09:00:00+00:00", origin="simulated")], generated_at=NOW))
        self.assertIn("[SIMULATED] 192.0.2.1", text)

    def test_empty_data_is_handled_honestly(self):
        text = render_text(build_report_data(mode="Offline", generated_at=NOW))
        self.assertIn("No observations were selected.", text)
        self.assertIn("Not available: at least two observations", text)
        self.assertIn("No proxy test results were included.", text)
        self.assertNotIn("PRIVACY CHECKLIST", text)  # section omitted when not selected

    def test_comparison_needs_two_observations(self):
        self.assertIsNone(full_data(observations=[A]).comparison)
        self.assertIsNotNone(full_data().comparison)

    def test_no_overclaiming(self):
        text = render_text(full_data()).lower()
        for phrase in ("completely anonymous", "guarantees anonymity", "untraceable", "you are now anonymous"):
            self.assertNotIn(phrase, text)
        self.assertIn("cannot guarantee anonymity", text)
        self.assertIn("does not prove", text)


class SecurityTests(unittest.TestCase):
    def test_credentials_never_reach_report(self):
        leaky = proxy(message="failed for http://alice:S3cr3t@host:8080", proxy="http://host:8080")
        for fmt in ("txt", "html"):
            out = render_report(full_data(proxy_results=[leaky]), fmt)
            self.assertNotIn("S3cr3t", out)
            self.assertNotIn("alice", out)

    def test_html_is_escaped(self):
        evil = obs("203.0.113.9", "2026-10-03T10:00:00+00:00", source="<script>alert(1)</script>")
        out = render_html(full_data(observations=[evil, B]))
        self.assertNotIn("<script>alert(1)</script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_html_is_self_contained(self):
        out = render_html(full_data())
        self.assertNotIn("http://", out.replace("http://host:8080", ""))  # no external resources
        self.assertNotIn("<script", out.lower())
        self.assertNotIn("src=", out.lower())


class WriteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_writes_utf8_file_and_leaves_no_temp_files(self):
        target = write_report(self.dir / "r.txt", "héllo ✓\n")
        self.assertEqual(target.read_text(encoding="utf-8"), "héllo ✓\n")
        self.assertEqual([p.name for p in self.dir.iterdir()], ["r.txt"])

    def test_overwrite_replaces_content(self):
        write_report(self.dir / "r.html", "one")
        write_report(self.dir / "r.html", "two")
        self.assertEqual((self.dir / "r.html").read_text(), "two")

    def test_invalid_paths_rejected_with_friendly_errors(self):
        (self.dir / "folder.txt").mkdir()
        cases = ["", "   ", str(self.dir / "r.exe"), str(self.dir / "missing" / "r.txt"), str(self.dir / "folder.txt"), "bad\x00name.txt"]
        for bad in cases:
            with self.subTest(bad=bad[:20]):
                with self.assertRaises(ReportError) as ctx:
                    write_report(bad, "x")
                self.assertNotIn("Traceback", str(ctx.exception))

    def test_cannot_write_into_app_data_folder(self):
        data_dir = self.dir / "appdata"
        data_dir.mkdir()
        with self.assertRaises(ReportError):
            write_report(data_dir / "r.txt", "x", forbidden_dir=data_dir)
        with self.assertRaises(ReportError):
            (data_dir / "sub").mkdir()
            write_report(data_dir / "sub" / "r.txt", "x", forbidden_dir=data_dir)

    def test_permission_error_is_friendly(self):
        with mock.patch("os.replace", side_effect=PermissionError("denied")):
            with self.assertRaises(ReportError) as ctx:
                write_report(self.dir / "r.txt", "x")
        self.assertIn("permission", str(ctx.exception))
        self.assertEqual(list(self.dir.iterdir()), [])  # temp file cleaned up

    def test_default_filename(self):
        self.assertEqual(default_filename("html", datetime(2026, 10, 3, 9, 8, 7)), "anonymity-toolkit-report-20261003-090807.html")
        self.assertTrue(default_filename("txt").endswith(".txt"))


class OfflineTests(unittest.TestCase):
    def test_report_generation_needs_no_network(self):
        def blocked(*a, **k):
            raise AssertionError("network access attempted")

        with mock.patch("socket.socket", side_effect=blocked), mock.patch("socket.create_connection", side_effect=blocked), \
                mock.patch("socket.getaddrinfo", side_effect=blocked):
            self.assertIn("Operating mode when generated: Offline", render_text(full_data(mode="Offline")))
            self.assertIn("<h1>", render_html(full_data(mode="Offline")))


if __name__ == "__main__":
    unittest.main()
