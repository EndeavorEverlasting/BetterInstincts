"""Offline lot cardinal semantics + library search clear + workstation identity."""
from __future__ import annotations

import unittest

from betterinstincts.lot_cardinal_semantics import (
    assess_library_search_admission,
    assess_workstation_candidate,
    authority_stack,
    describe_landmark,
    is_ninety_deg_from,
    load_contract,
)


class LotCardinalSemanticsTests(unittest.TestCase):
    def test_authority_prefers_ea_parser(self):
        stack = authority_stack()
        self.assertEqual(stack[0], "EA_SAVE_OR_TRAY_PARSER_WHEN_AUTHORIZED")
        self.assertIn("CARDINAL_SEMANTIC_MODEL", stack)
        self.assertLess(
            stack.index("CARDINAL_SEMANTIC_MODEL"),
            stack.index("CAMERA_ROAM_LAST_RESORT"),
        )

    def test_ninety_deg_and_landmarks(self):
        self.assertTrue(is_ninety_deg_from(front_cardinal="N", target_cardinal="E"))
        self.assertTrue(is_ninety_deg_from(front_cardinal="E", target_cardinal="S"))
        self.assertFalse(is_ninety_deg_from(front_cardinal="N", target_cardinal="S"))
        fridge = describe_landmark("fridge")
        self.assertTrue(fridge["found"])
        kinds = {r["kind"] for r in fridge["relations"]}
        self.assertIn("OPPOSITE_SIDE_AS", kinds)
        self.assertIn("NEAR", kinds)
        tub = describe_landmark("bathtub")
        self.assertIn("SAME_SIDE_AS", {r["kind"] for r in tub["relations"]})
        ws = describe_landmark("robotics_workstation")
        self.assertIn("NINETY_DEG_FROM", {r["kind"] for r in ws["relations"]})

    def test_workstation_gray_vs_blue_generator(self):
        ok = assess_workstation_candidate(
            body_color="GRAY",
            gardener_bot_needs_fix=True,
            servo_activate_affordance=False,
        )
        self.assertTrue(ok["admit"])
        self.assertIn("ACTIVATE_SERVO", ok["forbidden"])
        deny = assess_workstation_candidate(
            body_color="BLUE",
            dominant_blue_glow_cylinder=True,
            pie_tokens=["ADD_FUEL", "START_WATER_GENERATOR"],
        )
        self.assertFalse(deny["admit"])
        self.assertEqual(deny["gate"], "ROBOTICS_WORKSTATION_IDENTITY_MISMATCH")
        act = assess_workstation_candidate(
            body_color="GRAY",
            servo_activate_affordance=True,
        )
        self.assertFalse(act["admit"])

    def test_library_search_clear_required(self):
        denied = assess_library_search_admission(
            current_search_text="Smog",
            intended_query="Hydroponic",
            search_cleared=False,
        )
        self.assertFalse(denied["admit"])
        self.assertEqual(denied["gate"], "CLEAR_SEARCH_BEFORE_QUERY")
        self.assertIn("CTRL_A", denied["chord_until_measured"])
        ok = assess_library_search_admission(
            current_search_text="Smog",
            intended_query="Hydroponic",
            search_cleared=True,
        )
        self.assertTrue(ok["admit"])
        empty = assess_library_search_admission(
            current_search_text="",
            intended_query="Hydroponic",
        )
        self.assertTrue(empty["admit"])

    def test_contract_workstation_gray(self):
        cfg = load_contract()
        self.assertEqual(
            cfg["robotics_workstation_identity"]["visual"]["body_color"], "GRAY"
        )


if __name__ == "__main__":
    unittest.main()
