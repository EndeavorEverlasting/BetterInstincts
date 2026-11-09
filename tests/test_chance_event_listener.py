"""Cross-stack sidecar proof: popup advice survives the player-presence gate."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from betterinstincts.chance_event_research import (
    empty_memo, remember, save_memo,
)
from betterinstincts.host_listener import (
    HostListenerError, activate, tick,
)
from betterinstincts.player_presence import PresenceProbe

GREEN = dict(hunger=.9, bladder=.9, energy=.9, hygiene=.9, fun=.9, social=.9)


def event():
    return {
        "schema": "betterinstincts.chance-event/v1",
        "capture_ref": "capture:popup",
        "modal_visible": True,
        "scene_cues": ["dialog_bounds", "choice_controls"],
        "title": "A Mystery Offer",
        "body": "A strange choice interrupts the day.",
        "options": [{"id": "yes", "label": "Take it"},
                    {"id": "no", "label": "Refuse"}],
        "context": {"game_version": "1.121.361.1020", "locale": "en-US",
                    "packs": ["EP17"], "mods_digest": "NONE"},
    }


def observation(**extra):
    return {
        "schema": "betterinstincts.host-listener.observation/v1",
        "needs": GREEN, "queue": [], "location_kind": "home",
        "capture_ref": "capture:popup",
        "objects_on_current_lot": True,
        "viewport": {"state": "VIEWPORT_OK"},
        "chance_event": event(),
        **extra,
    }


class ChanceEventListenerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.root_patch = patch("betterinstincts.host_listener.ROOT", self.root)
        self.output_patch = patch("betterinstincts.host_listener.OUTPUT",
                                  self.root / "dist" / "host-listener")
        self.root_patch.start()
        self.output_patch.start()
        activate("chance-sidecar")

    def tearDown(self):
        self.output_patch.stop()
        self.root_patch.stop()
        self.tmp.cleanup()

    def test_player_active_receives_advisory_without_host_control(self):
        result = tick("chance-sidecar", observation(),
                      presence_probe=PresenceProbe(True, True, last_input_age_ms=0))
        self.assertEqual(result["listener_action"], "YIELD_TO_PLAYER")
        self.assertEqual(result["chance_event"]["state"], "RESEARCH_REQUIRED")
        self.assertEqual(result["chance_event"]["ui"]["game_choice_control"], "PLAYER_ONLY")
        self.assertFalse(result["execute_clicks"])
        self.assertIsNone(result["chance_event"]["control_permit"])

    def test_idle_receipt_reuses_same_advisory_without_host_click(self):
        result = tick("chance-sidecar", observation(),
                      presence_probe=PresenceProbe(False, False,
                                                   last_input_age_ms=21000, probe_ok=True))
        self.assertIn("chance_event", result)
        self.assertEqual(result["chance_event"]["state"], "RESEARCH_REQUIRED")
        self.assertFalse(result["execute_clicks"])

    def test_opt_in_adds_frontier_job_but_not_network_side_effect(self):
        result = tick("chance-sidecar", observation(
            chance_event_external_research_opt_in=True),
            presence_probe=PresenceProbe(True, True, last_input_age_ms=0))
        self.assertEqual([x["lane"] for x in result["chance_event"]["research_dispatch"]],
                         ["LOCAL_MECHANICS", "FRONTIER_CROSSCHECK"])
        self.assertIsNone(result["chance_event"]["control_permit"])

    def test_mismatched_capture_ref_is_rejected(self):
        bad = event()
        bad["capture_ref"] = "capture:old"
        with self.assertRaisesRegex(HostListenerError, "CHANCE_EVENT_CAPTURE_MISMATCH"):
            tick("chance-sidecar", observation(chance_event=bad),
                 presence_probe=PresenceProbe(True, True, last_input_age_ms=0))

    def test_invalid_external_opt_in_rejected(self):
        with self.assertRaisesRegex(HostListenerError, "CHANCE_EVENT_EXTERNAL_OPT_IN_INVALID"):
            tick("chance-sidecar", observation(chance_event_external_research_opt_in="yes"),
                 presence_probe=PresenceProbe(True, True, last_input_age_ms=0))

    def test_reviewed_memo_reused_while_player_controls_game(self):
        now = datetime.now(timezone.utc)
        complete = {
            "reviewed": True, "recommended_option_id": "no",
            "sources": [{"kind": "LOCAL_TUNING", "ref": "local:source",
                         "observed_at": now.isoformat()}],
            "implications": [
                {"option_id": "yes", "permanence": "IRREVERSIBLE",
                 "benefits": [], "risks": ["Permanent change"],
                 "unknowns": [], "confidence": "HIGH"},
                {"option_id": "no", "permanence": "REVERSIBLE",
                 "benefits": ["Keep current state"], "risks": [],
                 "unknowns": [], "confidence": "HIGH"},
            ],
        }
        memo = remember(empty_memo(), event(), complete, now=now)
        local = self.root / "dist" / "chance-event-research"
        local.mkdir(parents=True)
        save_memo(local / "memo.json", memo)
        result = tick("chance-sidecar", observation(),
                      presence_probe=PresenceProbe(True, True, last_input_age_ms=0))
        self.assertTrue(result["chance_event"]["memo_hit"])
        self.assertEqual(result["chance_event"]["state"], "READY_FOR_PLAYER")
        self.assertEqual(result["chance_event"]["recommended_option_id"], "no")
        self.assertEqual(result["listener_action"], "YIELD_TO_PLAYER")
        self.assertFalse(result["chance_event"]["execute_clicks"])


if __name__ == "__main__":
    unittest.main()
