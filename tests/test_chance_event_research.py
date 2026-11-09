import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from betterinstincts.chance_event_research import (
    ChanceEventError, assess, empty_memo, identify, load_memo, remember, save_memo,
)

NOW = datetime(2026, 11, 9, 19, 20, tzinfo=timezone.utc)


def event(*, version="1.121.361.1020", mods="NONE", cues=None):
    return {
        "schema": "betterinstincts.chance-event/v1",
        "capture_ref": "capture:chance-1",
        "modal_visible": True,
        "scene_cues": cues if cues is not None else ["dialog_bounds", "choice_controls"],
        "title": "A Strange Offer",
        "body": "A passerby offers your Sim a mysterious charm.",
        "options": [{"id": "take", "label": "Accept the Charm"},
                    {"id": "decline", "label": "Politely Decline"}],
        "context": {"game_version": version, "locale": "en-US",
                    "mods_digest": mods, "packs": ["EP17"]},
    }


def research(*, risk="IRREVERSIBLE", local=True, disputed=False):
    sources = [{"kind": "LOCAL_TUNING" if local else "EXTERNAL_REFERENCE",
                "ref": "file:local-tuning" if local else "https://example.org/guide",
                "observed_at": NOW.isoformat()}]
    return {
        "reviewed": True,
        "recommended_option_id": "decline",
        "sources": sources,
        "implications": [
            {"option_id": "take", "permanence": risk, "benefits": ["Potential boost"],
             "risks": ["Changes life state"], "unknowns": [],
             "confidence": "HIGH", "disputed": disputed},
            {"option_id": "decline", "permanence": "REVERSIBLE",
             "benefits": ["Preserves current path"], "risks": [],
             "unknowns": [], "confidence": "HIGH"},
        ],
    }


class ChanceEventResearchTests(unittest.TestCase):
    def test_confirmed_popup_dispatches_local_first_no_click(self):
        report = assess(event(), now=NOW)
        self.assertEqual(report["state"], "RESEARCH_REQUIRED")
        self.assertEqual([x["lane"] for x in report["research_dispatch"]],
                         ["LOCAL_MECHANICS"])
        self.assertFalse(report["execute_clicks"])
        self.assertIsNone(report["control_permit"])
        self.assertFalse(report["ui"]["non_modal"] is False)
        self.assertEqual(report["ui"]["game_choice_control"], "PLAYER_ONLY")

    def test_external_search_requires_opt_in_and_stays_sanitized(self):
        report = assess(event(), external_research_opt_in=True, now=NOW)
        self.assertEqual(len(report["research_dispatch"]), 2)
        self.assertTrue(report["research_dispatch"][1]["network"])
        self.assertNotIn("mysterious charm",
                         json.dumps(report["research_dispatch"]).lower())
        self.assertEqual(report["ui"]["focus"], "GAME_RETAINS_KEYBOARD_AND_POINTER")

    def test_two_distinct_cues_required(self):
        report = assess(event(cues=["dialog_bounds", "dialog_bounds"]), now=NOW)
        self.assertEqual(report["state"], "OBSERVATION_REQUIRED")
        self.assertEqual(report["research_dispatch"], [])

    def test_running_only_when_real_host_reports_running(self):
        self.assertEqual(assess(event(), now=NOW)["state"], "RESEARCH_REQUIRED")
        self.assertEqual(assess(event(), now=NOW, host_research_state="RUNNING")["state"],
                         "RESEARCHING")
        self.assertEqual(assess(event(), now=NOW, host_research_state="FAILED")["state"],
                         "RESEARCH_FAILED")

    def test_reviewed_memo_is_reused_without_research_or_action(self):
        memo = remember(empty_memo(), event(), research(), now=NOW)
        result = assess(event(), memo, now=NOW + timedelta(days=1))
        self.assertEqual(result["state"], "READY_FOR_PLAYER")
        self.assertEqual(result["recommended_option_id"], "decline")
        self.assertTrue(result["memo_hit"])
        self.assertEqual(result["research_dispatch"], [])
        self.assertEqual(len(result["ui"]["choices"]), 2)
        self.assertFalse(result["execute_clicks"])

    def test_patch_and_mod_changes_invalidate_cache(self):
        memo = remember(empty_memo(), event(), research(), now=NOW)
        for changed in [event(version="1.121.361.1021"),
                        event(mods="MOD-NEW")]:
            result = assess(changed, memo, now=NOW)
            self.assertFalse(result["memo_hit"])
            self.assertEqual(result["state"], "RESEARCH_REQUIRED")
        self.assertNotEqual(identify(event())["key"], identify(event(mods="x"))["key"])

    def test_cache_ttl_does_not_survive_staleness(self):
        memo = remember(empty_memo(), event(), research(), now=NOW, ttl_days=1)
        self.assertEqual(assess(event(), memo, now=NOW + timedelta(days=2))["state"],
                         "RESEARCH_REQUIRED")

    def test_permanent_frontier_only_does_not_recommend(self):
        memo = remember(empty_memo(), event(), research(local=False), now=NOW)
        result = assess(event(), memo, now=NOW)
        self.assertEqual(result["state"], "REVIEW_REQUIRED")
        self.assertIsNone(result["recommended_option_id"])

    def test_disputed_or_unknown_outcome_fails_closed(self):
        for material in [research(disputed=True), research(risk="UNKNOWN")]:
            memo = remember(empty_memo(), event(), material, now=NOW)
            result = assess(event(), memo, now=NOW)
            self.assertEqual(result["state"], "REVIEW_REQUIRED")

    def test_unreviewed_or_misaligned_research_cannot_memoize(self):
        bad = research()
        bad["reviewed"] = False
        with self.assertRaises(ChanceEventError):
            remember(empty_memo(), event(), bad, now=NOW)
        bad = research()
        bad["implications"][0]["option_id"] = "third_choice"
        with self.assertRaises(ChanceEventError):
            remember(empty_memo(), event(), bad, now=NOW)

    def test_unknown_version_and_duplicate_options_rejected(self):
        bad = event()
        bad["context"]["game_version"] = ""
        with self.assertRaises(ChanceEventError):
            assess(bad, now=NOW)
        bad = event()
        bad["options"][1]["id"] = "take"
        with self.assertRaises(ChanceEventError):
            assess(bad, now=NOW)

    def test_local_memo_atomic_roundtrip(self):
        memo = remember(empty_memo(), event(), research(), now=NOW)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "memo.json"
            save_memo(path, memo)
            self.assertEqual(load_memo(path), memo)
            self.assertEqual(assess(event(), load_memo(path), now=NOW)["state"],
                             "READY_FOR_PLAYER")
            (Path(tmp) / "bad.json").write_text('{"records": {}}', encoding="utf-8")
            with self.assertRaises(ChanceEventError):
                load_memo(Path(tmp) / "bad.json")

    def test_no_recognition_from_gameplay_control_data_only(self):
        bad = event()
        bad["modal_visible"] = False
        report = assess(bad, now=NOW)
        self.assertEqual(report["state"], "OBSERVATION_REQUIRED")
        self.assertIsNone(report["control_permit"])


if __name__ == "__main__":
    unittest.main()
