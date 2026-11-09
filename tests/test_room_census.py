"""P82 measured offline tests: room evidence, mixed use, style plurality, no invented floor."""
from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from betterinstincts.build_floor_activity import evaluate_floor_activity
from betterinstincts.house_state import create_model, observe, HouseStateError
from betterinstincts.host_listener import activate, deactivate, tick
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.room_census import RoomCensusError, scan_lot_model, load_contract


def sample_model():
    model = create_model("room_lab_run", "Household Lab")
    return observe(model, entities={
        "living-zone": {"kind": "ROOM_ZONE", "story": "FLOOR_3", "zone": "LOFT", "enclosure": "INSIDE"},
        "sofa": {"kind": "SOFA", "story": "FLOOR_3", "zone": "LOFT", "enclosure": "INSIDE",
                 "style_tags": ["modern", "industrial"], "function_tags": ["office"]},
        "table": {"kind": "DINING_TABLE", "story": "FLOOR_3", "zone": "LOFT", "enclosure": "INSIDE",
                  "style_tags": ["industrial"]},
        "yard-zone": {"kind": "ROOM_ZONE", "story": "FLOOR_1", "zone": "GARDEN", "enclosure": "OUTSIDE"},
        "planter": {"kind": "PLANTER", "story": "FLOOR_1", "zone": "GARDEN", "enclosure": "OUTSIDE",
                    "style_tags": ["cottagecore"]},
        "basement-zone": {"kind": "ROOM_ZONE", "story": "BASEMENT_1", "zone": "UTILITY", "enclosure": "INSIDE"},
        "basement-item": {"kind": "CABINET", "story": "BASEMENT_1", "zone": "UTILITY", "enclosure": "INSIDE",
                          "category": "storage"},
        "lost-bed": {"kind": "BED", "story": "FLOOR_2", "enclosure": "INSIDE"},
    })


class RoomCensusTests(unittest.TestCase):
    def test_all_attested_floors_and_indoor_outdoor_zones(self):
        receipt = scan_lot_model(sample_model())
        self.assertEqual(list(receipt["floors"]), ["BASEMENT_1", "FLOOR_1", "FLOOR_2", "FLOOR_3"])
        self.assertEqual(receipt["rooms"]["FLOOR_1:GARDEN"]["enclosure"], "OUTSIDE")
        self.assertEqual(receipt["rooms"]["FLOOR_3:LOFT"]["enclosure"], "INSIDE")
        self.assertEqual(receipt["rooms"]["FLOOR_3:LOFT"]["room_evidence"], "STRUCTURE_ATTESTED")
        self.assertEqual(receipt["observed_story_count"], 4)
        self.assertIn("NOT_COMPLETE", receipt["coverage"])
        self.assertFalse(receipt["execute_allowed"])

    def test_multi_function_and_aesthetic_styles_not_exclusive(self):
        room = scan_lot_model(sample_model())["rooms"]["FLOOR_3:LOFT"]
        self.assertEqual(set(room["function_labels"]), {"living", "dining", "office"})
        self.assertEqual(set(room["style_labels"]), {"modern", "industrial"})
        self.assertEqual(next(x for x in room["styles"] if x["label"] == "industrial")["item_count"], 2)
        self.assertEqual(room["item_count"], 2)
        self.assertEqual(room["classification"], "MULTI_LABEL_NOT_EXCLUSIVE")

    def test_unassigned_and_zone_candidate(self):
        receipt = scan_lot_model(sample_model())
        self.assertEqual(receipt["unassigned_items"], [{"item_id": "lost-bed", "reason": "UNKNOWN_ZONE"}])
        m = create_model("room_lab_run", "Candidate Lot")
        m = observe(m, entities={"bed": {"kind": "BED", "story": "FLOOR_1", "zone": "CORNER", "enclosure": "INSIDE"}})
        self.assertEqual(scan_lot_model(m)["rooms"]["FLOOR_1:CORNER"]["room_evidence"], "ZONE_CANDIDATE")

    def test_conflicting_enclosure_abstains(self):
        m = create_model("room_lab_run", "Conflict Lot")
        m = observe(m, entities={
            "room": {"kind": "ROOM_ZONE", "story": "FLOOR_1", "zone": "MIX", "enclosure": "INSIDE"},
            "plant": {"kind": "PLANTER", "story": "FLOOR_1", "zone": "MIX", "enclosure": "OUTSIDE"},
        })
        zone = scan_lot_model(m)["rooms"]["FLOOR_1:MIX"]
        self.assertEqual(zone["enclosure"], "UNKNOWN_ENCLOSURE")
        self.assertTrue(zone["enclosure_conflict"])

    def test_style_persists_across_observation_update(self):
        m = sample_model()
        updated = observe(m, entities={"sofa": {"kind": "SOFA", "story": "FLOOR_3", "zone": "LOFT",
                                                "enclosure": "INSIDE", "label": "Sofa examined"}})
        self.assertEqual(updated["entities"]["sofa"]["style_tags"], ["modern", "industrial"])
        self.assertIn("industrial", scan_lot_model(updated)["rooms"]["FLOOR_3:LOFT"]["style_labels"])
        self.assertGreater(updated["revision"], m["revision"])

    def test_invalid_tags_and_model_fail_closed(self):
        with self.assertRaises(HouseStateError):
            observe(create_model("room_lab_run", "Unsafe Lot"), entities={
                "bed": {"kind": "BED", "style_tags": "modern"}
            })
        with self.assertRaises(RoomCensusError):
            scan_lot_model({"schema": "wrong", "entities": {}, "revision": 1})

    def test_listener_peer_is_compact_and_skips_live(self):
        model = sample_model()
        result = evaluate_floor_activity(build_or_buy_mode=True, active_story="FLOOR_1", lot_model=model)
        self.assertEqual(result["room_census"]["room_count_total"], 3)
        self.assertNotIn("items", result["room_census"]["rooms"][0])
        skipped = evaluate_floor_activity(build_or_buy_mode=False, lot_model=model)
        self.assertNotIn("room_census", skipped)
        yield_result = evaluate_floor_activity(build_or_buy_mode=True, player_directed=True, lot_model=model)
        self.assertNotIn("room_census", yield_result)

    def test_host_listener_tick_keeps_read_only_room_summary(self):
        import betterinstincts.host_listener as hl
        sid = "room-census-lab-unit"
        path = hl.OUTPUT / sid
        if path.exists():
            shutil.rmtree(path)
        try:
            activate(sid)
            probe = PresenceProbe(foreground_is_sims=True, cursor_in_client=False,
                                  last_input_age_ms=60000, operator_declared_playing=False,
                                  player_directed_queue=False, probe_ok=True)
            receipt = tick(sid, {
                "schema": "betterinstincts.host-listener.observation/v1",
                "needs": {k: 0.8 for k in ("hunger", "bladder", "energy", "hygiene", "fun", "social")},
                "queue": [], "location_kind": "home", "capture_ref": "capture:room-lab",
                "build_or_buy_mode": True, "active_story": "FLOOR_1",
                "lot_model": sample_model(),
            }, presence_probe=probe, idle_ms=1000)
            self.assertEqual(receipt["build_floor_activity"]["room_census"]["room_count_total"], 3)
            self.assertFalse(receipt["execute_clicks"])
            deactivate(sid)
        finally:
            if path.exists():
                shutil.rmtree(path)

    def test_p78_glossary_and_documentation_single_authority(self):
        root = Path(__file__).resolve().parents[1]
        contract = load_contract()
        self.assertEqual(contract["authority"], "betterinstincts/room_census.py")
        glossary_contract = json.loads((root / "contracts/glossary.v1.json").read_text(encoding="utf-8"))
        doc = (root / "docs/GLOSSARY.md").read_text(encoding="utf-8")
        # P78 keeps human-facing glossary rows inside the existing table.
        self.assertEqual(doc.count("| **ROOM_CENSUS** / **ROOM_CENSUS_COVERAGE** |"), 1)
        self.assertLess(doc.index("| **ROOM_CENSUS** /"), doc.index("Related matrices:"))
        for term in (
            "ROOM_CENSUS", "ROOM_CENSUS_COVERAGE", "ROOM_ZONE_ATTESTED",
            "ROOM_ZONE_CANDIDATE", "MULTI_LABEL_ROOM_FUNCTION", "ROOM_STYLE_EVIDENCE",
        ):
            self.assertIn(term, glossary_contract["terms"])
            self.assertIn("**" + term + "**", doc)
            for owner in glossary_contract["terms"][term]["owners"]:
                self.assertTrue((root / owner).is_file(), owner)
        runbook = (root / "docs/ROOM_CENSUS.md").read_text(encoding="utf-8")
        provenance = (root / "docs/PROMPT_INVOCATIONS.md").read_text(encoding="utf-8")
        self.assertIn("python -m scripts.room_census evaluate", runbook)
        self.assertIn("P08 live-game gate", runbook)
        self.assertIn("P78 — Repository Glossary & Documentation Diet", provenance)
        self.assertNotIn("P95/P124/P178/Trifecta", provenance)
        self.assertLess(len(runbook), 2000)

    def test_contract_and_cli(self):
        cfg = load_contract()
        self.assertIn("minimalist", cfg["style_labels"])
        root = Path(__file__).resolve().parents[1]
        script = root / "scripts" / "room_census.py"
        compile(script.read_text(encoding="utf-8"), str(script), "exec")


if __name__ == "__main__":
    unittest.main()
