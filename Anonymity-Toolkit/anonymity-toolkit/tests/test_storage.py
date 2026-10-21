import json
import tempfile
import unittest
from pathlib import Path

from app.controller import Controller
from services.ip_service import IpObservation
from services.proxy_service import ProxyTestResult
from storage.json_store import MAX_ENTRIES, JsonStore, StorageError

OBS = {"ip": "203.0.113.7", "version": 4, "timestamp": "2026-10-03T10:00:00+00:00", "source": "api.ipify.org", "elapsed_ms": 12.5, "origin": "observed"}
PROXY = {"success": True, "stage": "ok", "message": "fine", "proxy": "http://host:8080", "elapsed_ms": 30.0,
         "timestamp": "2026-10-03T10:01:00+00:00", "http_status": 200, "egress_ip": "198.51.100.4", "destination": "api.ipify.org", "origin": "observed"}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write_raw(self, text):
        (self.dir / "data.json").write_text(text, encoding="utf-8")

    def test_missing_file_gives_defaults_without_warning(self):
        store = JsonStore(self.dir)
        self.assertEqual((store.observations(), store.proxy_results(), store.load_warnings), ([], [], []))
        self.assertEqual(store.get_preference("appearance", "dark"), "dark")

    def test_round_trip_and_preferences(self):
        store = JsonStore(self.dir)
        store.add_observation(OBS)
        store.add_proxy_result(PROXY)
        store.set_preference("appearance", "light")
        store.set_checklist({"vpn": "reviewed"})
        again = JsonStore(self.dir)
        self.assertEqual(again.observations(), [OBS])
        self.assertEqual(again.proxy_results(), [PROXY])
        self.assertEqual(again.get_preference("appearance", "dark"), "light")
        self.assertEqual(again.checklist(), {"vpn": "reviewed"})
        self.assertEqual(list(self.dir.glob("*.tmp")), [])  # atomic write leaves no temp files

    def test_corrupted_json_is_quarantined(self):
        for bad in ["{not json", "[]", '"text"', "\x00\x01", ""]:
            with self.subTest(bad=bad[:10]):
                self.write_raw(bad)
                store = JsonStore(self.dir)
                self.assertEqual(store.observations(), [])
                self.assertTrue(store.load_warnings)
                self.assertTrue(list(self.dir.glob("data.corrupt-*.json")))
                self.assertFalse((self.dir / "data.json").exists())
                for f in self.dir.glob("data.corrupt-*.json"):
                    f.unlink()
        store.add_observation(OBS)  # still usable after recovery
        self.assertEqual(len(JsonStore(self.dir).observations()), 1)

    def test_invalid_entries_dropped_and_reported(self):
        bad_obs = [
            {**OBS, "ip": "999.1.1.1"}, {**OBS, "version": 6}, {**OBS, "timestamp": "nope"},
            {**OBS, "origin": "weird"}, {**OBS, "elapsed_ms": "fast"}, "string", None, {"ip": "1.1.1.1"},
        ]
        self.write_raw(json.dumps({"observations": [OBS] + bad_obs, "proxy_results": [PROXY, {"junk": 1}]}))
        store = JsonStore(self.dir)
        self.assertEqual(len(store.observations()), 1)
        self.assertEqual(len(store.proxy_results()), 1)
        self.assertIn("ignored", store.load_warnings[0])

    def test_secrets_are_stripped_or_rejected(self):
        with_pw = {**PROXY, "password": "hunter2", "extra": "x"}
        leaked = {**PROXY, "proxy": "http://user:hunter2@host:8080"}
        self.write_raw(json.dumps({"proxy_results": [with_pw, leaked]}))
        store = JsonStore(self.dir)
        self.assertEqual(len(store.proxy_results()), 1)
        self.assertNotIn("password", store.proxy_results()[0])
        self.assertNotIn("hunter2", json.dumps(store.proxy_results()))
        with self.assertRaises(StorageError):
            store.add_proxy_result(leaked)

    def test_invalid_add_and_preference_rejected(self):
        store = JsonStore(self.dir)
        with self.assertRaises(StorageError):
            store.add_observation({**OBS, "ip": "bad"})
        with self.assertRaises(StorageError):
            store.set_preference("appearance", "neon")
        with self.assertRaises(StorageError):
            store.set_preference("secret", "x")

    def test_history_is_capped_keeping_newest(self):
        store = JsonStore(self.dir)
        for i in range(MAX_ENTRIES + 3):
            store.add_observation({**OBS, "elapsed_ms": float(i)})
        saved = JsonStore(self.dir).observations()
        self.assertEqual(len(saved), MAX_ENTRIES)
        self.assertEqual(saved[-1]["elapsed_ms"], float(MAX_ENTRIES + 2))

    def test_clear_history_keeps_preferences(self):
        store = JsonStore(self.dir)
        store.add_observation(OBS)
        store.set_preference("appearance", "light")
        store.clear_history()
        again = JsonStore(self.dir)
        self.assertEqual(again.observations(), [])
        self.assertEqual(again.get_preference("appearance", "dark"), "light")

    def test_unwritable_location_raises_storage_error(self):
        blocker = self.dir / "iamafile"
        blocker.write_text("x")
        store = JsonStore(blocker / "sub")  # parent is a file, so the folder cannot be created
        with self.assertRaises(StorageError):
            store.add_observation(OBS)


class ControllerPersistenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_observations_survive_restart_and_clear(self):
        c = Controller(JsonStore(self.dir))
        o = IpObservation(**OBS)
        self.assertIsNone(c.add_observation(o))
        self.assertIsNone(c.add_proxy_result(ProxyTestResult(**PROXY)))
        c2 = Controller(JsonStore(self.dir))
        self.assertEqual(c2.observations, [o])
        self.assertEqual(c2.last_diagnostic_timestamp(), PROXY["timestamp"])
        self.assertIsNone(c2.clear_history())
        self.assertEqual(Controller(JsonStore(self.dir)).observations, [])

    def test_save_failure_is_reported_but_session_keeps_data(self):
        blocker = self.dir / "iamafile"
        blocker.write_text("x")
        c = Controller(JsonStore(blocker / "sub"))
        error = c.add_observation(IpObservation(**OBS))
        self.assertIsInstance(error, str)
        self.assertEqual(len(c.observations), 1)

    def test_no_store_means_memory_only(self):
        c = Controller()
        self.assertIsNone(c.add_observation(IpObservation(**OBS)))
        self.assertEqual(c.last_diagnostic_timestamp(), OBS["timestamp"])
        self.assertIn("memory only", c.data_location())
        self.assertEqual(c.get_preference("appearance", "dark"), "dark")
        c.set_preference("appearance", "light")
        self.assertEqual(c.get_preference("appearance", "dark"), "light")


if __name__ == "__main__":
    unittest.main()
