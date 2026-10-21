import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import simulator.scenarios as scenarios_module
from simulator.scenarios import PROTECTION_LABELS, SIMULATED_LABEL, SIMULATION_NOTICE, ScenarioDataError, load_scenarios

EXPECTED_IDS = {
    "direct_connection", "http_https_proxy", "vpn_tunnel", "public_wifi_https",
    "vpn_failure_kill_switch", "dns_privacy", "tracking_cookies_fingerprinting",
}


def valid_scenario(**overrides):
    base = {
        "id": "x", "title": "X", "summary": "s", "assumptions": ["a"],
        "flows": [{"title": "f", "nodes": ["A", "B"], "links": [{"label": "l", "protection": "encrypted"}]}],
        "parties": [{"name": "p", "can_see": ["c"], "cannot_see": []}],
        "protects": ["p"], "does_not_protect": ["d"], "recommendations": ["r"],
    }
    base.update(overrides)
    return base


class ShippedScenarioTests(unittest.TestCase):
    def setUp(self):
        self.scenarios = load_scenarios()

    def test_all_seven_required_scenarios_present(self):
        self.assertEqual({s.id for s in self.scenarios}, EXPECTED_IDS)
        self.assertEqual(len(self.scenarios), 7)

    def test_every_scenario_is_complete_and_marked_simulated(self):
        for s in self.scenarios:
            with self.subTest(s.id):
                self.assertTrue(s.simulated)
                self.assertTrue(s.assumptions and s.protects and s.does_not_protect)
                self.assertGreaterEqual(len(s.recommendations), 2)
                self.assertTrue(s.parties and all(p.can_see for p in s.parties))
                for flow in s.flows:
                    self.assertEqual(len(flow.nodes), len(flow.links) + 1)
                    self.assertTrue(all(link.protection in PROTECTION_LABELS for link in flow.links))

    def test_kill_switch_scenario_shows_both_outcomes(self):
        s = next(x for x in self.scenarios if x.id == "vpn_failure_kill_switch")
        self.assertEqual(len(s.flows), 2)
        for flow in s.flows:
            self.assertIn("failed", {link.protection for link in flow.links})

    def test_no_overclaiming_language(self):
        blob = json.dumps(Path(scenarios_module.default_path()).read_text(encoding="utf-8")).lower()
        for phrase in ("guarantee", "completely anonymous", "untraceable", "100%", "fully anonymous"):
            self.assertNotIn(phrase, blob)

    def test_labels_make_simulation_explicit(self):
        self.assertEqual(SIMULATED_LABEL, "SIMULATED")
        self.assertIn("not live data", SIMULATION_NOTICE)


class OfflineTests(unittest.TestCase):
    def test_loading_works_with_all_networking_blocked(self):
        def blocked(*args, **kwargs):
            raise AssertionError("network access attempted")

        with mock.patch("socket.socket", side_effect=blocked), mock.patch("socket.create_connection", side_effect=blocked), \
                mock.patch("socket.getaddrinfo", side_effect=blocked):
            self.assertEqual(len(load_scenarios()), 7)

    def test_module_source_has_no_network_code(self):
        source = Path(scenarios_module.__file__).read_text(encoding="utf-8")
        for word in ("import requests", "import socket", "urllib", "http.client", "subprocess"):
            self.assertNotIn(word, source)


class InvalidDataTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "s.json"

    def write(self, payload):
        self.path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")

    def test_valid_minimal_file_loads(self):
        self.write({"scenarios": [valid_scenario()]})
        self.assertEqual(load_scenarios(self.path)[0].id, "x")

    def test_bad_files_raise_scenario_data_error(self):
        flows_bad_count = [{"title": "f", "nodes": ["A", "B", "C"], "links": [{"label": "l", "protection": "encrypted"}]}]
        flows_bad_protection = [{"title": "f", "nodes": ["A", "B"], "links": [{"label": "l", "protection": "magic"}]}]
        cases = {
            "not json": "{oops",
            "wrong top level": [],
            "no scenarios": {"scenarios": []},
            "missing key": {"scenarios": [{k: v for k, v in valid_scenario().items() if k != "summary"}]},
            "node/link mismatch": {"scenarios": [valid_scenario(flows=flows_bad_count)]},
            "unknown protection": {"scenarios": [valid_scenario(flows=flows_bad_protection)]},
            "duplicate ids": {"scenarios": [valid_scenario(), valid_scenario()]},
            "empty text": {"scenarios": [valid_scenario(title="  ")]},
        }
        for name, payload in cases.items():
            with self.subTest(name):
                self.write(payload)
                with self.assertRaises(ScenarioDataError):
                    load_scenarios(self.path)

    def test_missing_file(self):
        with self.assertRaises(ScenarioDataError):
            load_scenarios(Path(self._tmp.name) / "nope.json")


if __name__ == "__main__":
    unittest.main()
