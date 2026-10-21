import unittest

from services.comparison_service import ComparisonError, compare_observations, format_gap
from services.ip_service import IpObservation


def obs(ip="203.0.113.7", ts="2026-10-03T10:00:00+00:00", version=4, source="api.ipify.org", origin="observed"):
    return IpObservation(ip=ip, version=version, timestamp=ts, source=source, elapsed_ms=10.0, origin=origin)


class CompareTests(unittest.TestCase):
    def test_different_addresses_wording_is_qualified(self):
        res = compare_observations(obs("203.0.113.7"), obs("198.51.100.4", "2026-10-03T10:05:00+00:00"))
        self.assertTrue(res.ips_differ)
        self.assertEqual(res.headline, "OBSERVED ADDRESS CHANGED")
        self.assertIn("does not prove", res.explanation)
        self.assertNotIn("guarantee", res.explanation.lower())
        self.assertEqual(res.gap_seconds, 300)

    def test_identical_addresses_are_inconclusive(self):
        res = compare_observations(obs(), obs(ts="2026-10-03T10:01:00+00:00"))
        self.assertFalse(res.ips_differ)
        self.assertIn("does not establish", res.explanation)

    def test_selection_order_does_not_matter(self):
        a, b = obs("203.0.113.7", "2026-10-03T10:00:00+00:00"), obs("198.51.100.4", "2026-10-03T11:00:00+00:00")
        res = compare_observations(b, a)
        self.assertIs(res.earlier, a)
        self.assertIs(res.later, b)

    def test_ipv6_text_forms_compare_equal(self):
        res = compare_observations(obs("2001:db8::1", version=6), obs("2001:0db8:0:0:0:0:0:1", "2026-10-03T10:01:00+00:00", version=6))
        self.assertFalse(res.ips_differ)

    def test_notes_for_version_source_simulated_and_long_gap(self):
        res = compare_observations(
            obs(), obs("2001:db8::1", "2026-10-05T10:00:00+00:00", version=6, source="other", origin="simulated")
        )
        text = " ".join(res.notes)
        for word in ("IPv4 vs IPv6", "different lookup sources", "SIMULATED", "24 hours"):
            self.assertIn(word, text)

    def test_limitations_and_followups_always_present(self):
        res = compare_observations(obs(), obs("198.51.100.4", "2026-10-03T10:05:00+00:00"))
        self.assertTrue(res.limitations and res.follow_ups)

    def test_missing_or_same_observation_rejected(self):
        a = obs()
        for args in [(None, a), (a, None), (None, None), (a, a)]:
            with self.assertRaises(ComparisonError):
                compare_observations(*args)

    def test_unparseable_timestamps_do_not_crash(self):
        res = compare_observations(obs(ts="garbage"), obs("198.51.100.4", ts="also bad"))
        self.assertIsNone(res.gap_seconds)

    def test_format_gap(self):
        self.assertEqual(format_gap(None), "unknown")
        self.assertEqual(format_gap(42), "42 s")
        self.assertEqual(format_gap(125), "2 min 5 s")
        self.assertEqual(format_gap(7500), "2 h 5 min")


if __name__ == "__main__":
    unittest.main()
