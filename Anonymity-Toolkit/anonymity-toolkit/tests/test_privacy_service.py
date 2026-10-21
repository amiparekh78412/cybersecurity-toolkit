import tempfile
import unittest
from pathlib import Path

from app.controller import Controller
from services.ip_service import IpObservation
from services.privacy_service import (
    ITEM_IDS, ITEMS, STATUS_LABELS, build_findings, clean_states, observation_hint, summary_counts,
)
from storage.json_store import JsonStore


def obs(ip, ts):
    return IpObservation(ip=ip, version=4, timestamp=ts, source="api.ipify.org", elapsed_ms=5.0)


class ChecklistContentTests(unittest.TestCase):
    def test_required_topics_present_and_complete(self):
        self.assertEqual(
            set(ITEM_IDS),
            {"vpn_active", "kill_switch", "dns_review", "webrtc_review", "tracking_protection", "account_cookies", "report_hygiene"},
        )
        self.assertEqual(len(set(ITEM_IDS)), len(ITEMS))
        for item in ITEMS:
            for text in (item.title, item.purpose, item.evidence_required, item.recommended_next_step, item.limitations):
                self.assertTrue(text.strip())
            self.assertGreaterEqual(len(item.review_steps), 3)

    def test_no_overclaiming_language(self):
        blob = " ".join(
            " ".join([i.title, i.purpose, i.evidence_required, i.recommended_next_step, i.limitations, *i.review_steps]) for i in ITEMS
        ).lower()
        for phrase in ("guarantee", "completely anonymous", "you are anonymous", "100%", "score"):
            self.assertNotIn(phrase, blob)


class FindingTests(unittest.TestCase):
    def test_default_is_not_verified_and_unverified_evidence(self):
        findings = build_findings({})
        self.assertEqual({f.status_label for f in findings}, {"Not verified"})
        self.assertEqual({f.evidence_kind for f in findings}, {"unverified"})

    def test_statuses_map_to_labels_and_evidence_kind(self):
        findings = {f.item_id: f for f in build_findings({"vpn_active": "reviewed", "kill_switch": "needs_review"})}
        self.assertEqual(findings["vpn_active"].status_label, "Reviewed")
        self.assertEqual(findings["vpn_active"].evidence_kind, "user-reported")
        self.assertEqual(findings["kill_switch"].status_label, "Needs review")
        self.assertEqual(findings["kill_switch"].evidence_kind, "unverified")
        self.assertIn("Re-check", findings["vpn_active"].recommendation)

    def test_no_finding_is_ever_marked_observed(self):
        all_reviewed = {i: "reviewed" for i in ITEM_IDS}
        self.assertNotIn("observed", {f.evidence_kind for f in build_findings(all_reviewed)})

    def test_summary_counts_only_statuses_and_total_matches(self):
        counts = summary_counts({"vpn_active": "reviewed", "dns_review": "needs_review"})
        self.assertEqual(set(counts), set(STATUS_LABELS))
        self.assertEqual(counts, {"not_verified": 5, "needs_review": 1, "reviewed": 1})

    def test_clean_states_drops_unknown_ids_and_bad_statuses(self):
        self.assertEqual(clean_states({"vpn_active": "reviewed", "nope": "reviewed", "dns_review": "great"}), {"vpn_active": "reviewed"})
        for junk in (None, [], "x", 5):
            self.assertEqual(clean_states(junk), {})


class ObservationHintTests(unittest.TestCase):
    def test_hint_cases(self):
        a, b = obs("203.0.113.7", "2026-10-03T10:00:00+00:00"), obs("198.51.100.4", "2026-10-03T10:05:00+00:00")
        self.assertIn("fewer than two", observation_hint([]))
        self.assertIn("fewer than two", observation_hint([a]))
        differ = observation_hint([a, b])
        self.assertIn("different", differ)
        self.assertIn("not proof", differ)
        same = observation_hint([a, obs("203.0.113.7", "2026-10-03T10:09:00+00:00")])
        self.assertIn("does not establish", same)


class ControllerChecklistTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_answers_persist_and_reset(self):
        c = Controller(JsonStore(self.dir))
        self.assertIsNone(c.set_checklist_state("dns_review", "reviewed"))
        self.assertEqual(Controller(JsonStore(self.dir)).checklist, {"dns_review": "reviewed"})
        self.assertIsNone(c.reset_checklist())
        self.assertEqual(Controller(JsonStore(self.dir)).checklist, {})

    def test_invalid_item_or_status_rejected(self):
        c = Controller(JsonStore(self.dir))
        self.assertIsInstance(c.set_checklist_state("made_up", "reviewed"), str)
        self.assertIsInstance(c.set_checklist_state("vpn_active", "perfect"), str)
        self.assertEqual(c.checklist, {})

    def test_clearing_history_keeps_checklist(self):
        c = Controller(JsonStore(self.dir))
        c.set_checklist_state("vpn_active", "reviewed")
        c.clear_history()
        self.assertEqual(Controller(JsonStore(self.dir)).checklist, {"vpn_active": "reviewed"})


if __name__ == "__main__":
    unittest.main()
