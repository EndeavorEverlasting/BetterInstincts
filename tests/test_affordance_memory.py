"""P82 durable token-only hover lexicon and observation-vs-utility boundaries."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts.affordance_memory import (
    AffordanceMemoryError, empty_index, ingest, known_targets,
    load_index, record_event, MAX_ENTRIES,
)
from betterinstincts.hover_learning import EVENT_SCHEMA, empty_state, observe
from betterinstincts.host_listener import activate, deactivate, observe_hover, tick
from betterinstincts.house_state import create_model, observe as observe_lot
from betterinstincts.player_presence import PresenceProbe

PATCH = "1.121.361.1020"
LOT = "hover_memory_lot"
TIME = 1800000000000


def ev(kind, i, **extra):
    return {
        "schema": EVENT_SCHEMA,
        "id": f"evt_{i:04d}", "kind": kind, "at_ms": TIME + i * 100,
        "source": "sensor_supplied", **extra,
    }


def study_lot():
    model = create_model("affordance_run", LOT)
    return observe_lot(model, entities={
        "room": {"kind": "ROOM_ZONE", "story": "FLOOR_1", "zone": "BED",
                 "enclosure": "INSIDE"},
        "bed": {"kind": "BED", "story": "FLOOR_1", "zone": "BED",
                "enclosure": "INSIDE"},
    })


class AffordanceMemoryTests(unittest.TestCase):
    def test_observed_tooltip_is_candidate_only_and_patch_lot_qualified(self):
        e = ev("tooltip_visible", 1, target_ref="object:bed", tooltip_ref="tip:sleep")
        index, receipt = ingest(empty_index(), e, session_id="session-one",
                                game_version=PATCH, lot_id=LOT)
        self.assertEqual(receipt["state"], "AFFORDANCE_EVENT_INDEXED")
        self.assertEqual(len(index["entries"]), 1)
        item = next(iter(index["entries"].values()))
        self.assertEqual(item["status"], "CANDIDATE")
        self.assertEqual(item["reviewed_helpful"], 0)
        self.assertFalse(receipt["execute_allowed"])
        self.assertEqual(known_targets(index, game_version=PATCH, lot_id=LOT),
                         {"object:bed"})
        self.assertEqual(known_targets(index, game_version=PATCH, lot_id="different_lot"), set())
        self.assertEqual(known_targets(index, game_version="1.121.999.0", lot_id=LOT), set())
        replay, again = ingest(index, e, session_id="session-one",
                               game_version=PATCH, lot_id=LOT)
        self.assertEqual(replay, index)
        self.assertEqual(again["state"], "ALREADY_INDEXED")

    def test_reviewed_utility_is_linked_to_observed_action_not_hover(self):
        h = empty_state()
        index = empty_index()
        n = 1
        first = ev("tooltip_visible", n, target_ref="object:bed", tooltip_ref="tip:sleep")
        h, _ = observe(h, first)
        index, _ = ingest(index, first, session_id="one", game_version=PATCH,
                          lot_id=LOT, hover_state=h)
        for k in range(3):
            a = ev("action", 2 + k * 2, target_ref="object:bed",
                   action_ref="action:sleep", interaction_ref=f"interaction:sleep{k}")
            h, _ = observe(h, a)
            index, _ = ingest(index, a, session_id="one", game_version=PATCH,
                              lot_id=LOT, hover_state=h)
            o = ev("outcome", 3 + k * 2,
                   interaction_ref=f"interaction:sleep{k}", outcome="helpful",
                   evidence_ref=f"capture:observed{k}", operator_reviewed=True)
            h, _ = observe(h, o)
            index, _ = ingest(index, o, session_id="one", game_version=PATCH,
                              lot_id=LOT, hover_state=h)
        row = next(iter(index["entries"].values()))
        self.assertEqual(row["reviewed_helpful"], 3)
        self.assertEqual(row["status"], "REVIEWED_ASSOCIATION_NOT_GAME_PROOF")
        self.assertEqual(row["action_refs"], ["action:sleep"])

    def test_memory_is_bounded_atomic_and_rejects_private_tooltips(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "affordance-memory.v1.json"
            for n in range(MAX_ENTRIES + 2):
                event = ev("tooltip_visible", n,
                           target_ref=f"object:fixture{n}", tooltip_ref="tip:inspect")
                record_event(path, event, session_id="one",
                             game_version=PATCH, lot_id=LOT)
            index = load_index(path)
            self.assertEqual(len(index["entries"]), MAX_ENTRIES)
            self.assertLessEqual(path.stat().st_size, 128000)
            self.assertNotIn("raw_tooltip_text", path.read_text())
            with self.assertRaises(AffordanceMemoryError):
                ingest(index, {**ev("tooltip_visible", 999,
                           target_ref="object:bed", tooltip_ref="tip:sleep"),
                           "raw_tooltip_text": "Private person name"}, session_id="one")
            self.assertEqual(load_index(path), index)
            self.assertEqual(len(list(Path(d).glob("*.tmp"))), 0)


class ListenerAffordanceMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.p1 = patch("betterinstincts.host_listener.ROOT", root)
        self.p2 = patch("betterinstincts.host_listener.OUTPUT", root / "dist" / "host-listener")
        self.p1.start()
        self.p2.start()
        activate("mem-first")
        activate("mem-second")

    def tearDown(self):
        deactivate("mem-first")
        deactivate("mem-second")
        self.p2.stop()
        self.p1.stop()
        self.temp.cleanup()

    def test_cross_session_hover_discovery_prevents_repeated_lot_scanning(self):
        m = study_lot()
        event = ev("tooltip_visible", 1, target_ref="object:bed", tooltip_ref="tip:sleep")
        first = observe_hover("mem-first", event, explicit_opt_in=True,
                              game_version=PATCH, lot_id=LOT)
        self.assertTrue(first["affordance_memory"]["recorded"])
        other = observe_hover("mem-second", ev(
            "tooltip_visible", 2, target_ref="object:bed", tooltip_ref="tip:sleep"
        ), explicit_opt_in=True, game_version=PATCH, lot_id=LOT)
        self.assertEqual(other["affordance_memory"]["entry_count"], 1)
        self.assertTrue(other["affordance_memory"]["recorded"])
        obs = {
            "schema": "betterinstincts.host-listener.observation/v1",
            "needs": dict(hunger=.9, bladder=.9, energy=.2,
                          hygiene=.8, fun=.8, social=.8),
            "queue": [], "location_kind": "home",
            "capture_ref": "capture:after-reuse", "lot_model": m,
            "game_version": PATCH, "active_lot_id": LOT,
        }
        receipt = tick("mem-second", obs, presence_probe=PresenceProbe(
            True, True, last_input_age_ms=0, probe_ok=True
        ))
        survey = receipt["opportunity_survey"]
        self.assertEqual(survey["knowledge_hits"], 1)
        self.assertEqual(survey["unknown_targets"], 0)
        self.assertEqual(survey["exploration_targets"], [])
        self.assertFalse(survey["execute_allowed"])


if __name__ == "__main__":
    unittest.main()
