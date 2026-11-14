"""Regression checks for the user's Super Fertilizer hover screenshot semantics.

The fixture contains only visibly supported tooltip text and a synthetic
placeholder object ref; it is NOT an installed-game observation or input permit.
"""
import json
import unittest
from pathlib import Path

from betterinstincts.fertilizer_hover_recognition import (
    FertilizerHoverError, recognize_super_fertilizer_hover,
)

FIXTURE = (Path(__file__).resolve().parents[1] / "contracts" / "fixtures" /
           "BI-SUPER-FERTILIZER-HOVER-20261114.v1.json")


class SuperFertilizerHoverRecognitionTests(unittest.TestCase):
    def fixture(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def sample(self, **overrides):
        obs = dict(self.fixture()["synthetic_recognition_example"])
        obs.update(overrides)
        return obs

    def recognize(self, obs):
        return recognize_super_fertilizer_hover(
            obs, capture_ref="capture:fixture", item_ref="item:illustrative",
        )

    def test_uploaded_screenshot_has_genuine_specific_identity(self):
        fixture = self.fixture()
        self.assertEqual(fixture["screenshot_extract"]["tooltip_title"],
                         "SUPER FERTILIZER")
        self.assertIn("Jasmine", fixture["screenshot_extract"]["tooltip_description"])
        self.assertIn("Growfruit Challenge",
                      fixture["screenshot_extract"]["tooltip_description"])
        self.assertTrue(fixture["screenshot_extract"]["pointer_points_to_visible_ground_item"])
        self.assertTrue(fixture["screenshot_extract"]["visible_ground_item_highlighted"])
        out = self.recognize(self.sample())
        self.assertTrue(out["recognized"])
        self.assertEqual(out["item_kind"], "SUPER_FERTILIZER")
        self.assertEqual(out["displayed_value"], "§80")
        self.assertFalse(out["displayed_value_is_purchase_price"])
        self.assertTrue(out["identity_candidate_only"])
        self.assertTrue(out["host_reobservation_required"])
        self.assertFalse(out["dispatch_authorized"])

    def test_current_host_hover_keeps_actuation_separate(self):
        out = self.recognize(self.sample(source="HOST_VERIFIED_HOVER"))
        self.assertTrue(out["recognized"])
        self.assertFalse(out["host_reobservation_required"])
        self.assertFalse(out["dispatch_authorized"])
        self.assertEqual(out["proof_ceiling"],
                         "HOVER_OBJECT_IDENTITY_NOT_ELIGIBILITY_OR_GAME_EFFECT")

    def test_never_match_generic_fertilizer_decor_or_other_tooltip(self):
        for title, desc in (
            ("FERTILIZER BAG", "Special fertilizer received from Jasmine"),
            ("SUPER FERTILIZER KIT", "Special fertilizer received from Jasmine"),
            ("SUPER FERTILIZER", "A decorative landscaping sign"),
            ("GROWFRUIT", "Special fertilizer received from Jasmine"),
        ):
            with self.subTest(title=title, desc=desc):
                out = self.recognize(self.sample(title=title, description=desc))
                self.assertFalse(out["recognized"])
                self.assertIsNone(out["item_kind"])

    def test_tooltip_must_be_anchored_to_same_highlighted_world_target(self):
        for delta in (
            {"pointer_target_ref": "item:other"},
            {"highlighted_target_ref": "item:other"},
            {"tooltip_attached_to_target": False},
            {"capture_ref": "capture:unrelated"},
            {"source": "UNKNOWN_SENSOR"},
            {"source": "SCREEN_LABEL_ONLY"},
        ):
            with self.subTest(delta=delta), self.assertRaises(FertilizerHoverError):
                self.recognize(self.sample(**delta))

    def test_invalid_text_never_becomes_an_identified_object(self):
        for delta in (
            {"title": None},
            {"title": "\x00SUPER FERTILIZER"},
            {"title": "A" * 101},
            {"description": ""},
            {"displayed_value": "9" * 33},
        ):
            with self.subTest(delta=str(delta)[:50]), self.assertRaises(FertilizerHoverError):
                self.recognize(self.sample(**delta))

    def test_image_bounding_box_does_not_prove_world_position(self):
        fixture = self.fixture()
        self.assertFalse(fixture["screenshot_extract"]["bbox_is_gameplay_calibration"])
        self.assertFalse(fixture["source_image_in_public_repository"])
        self.assertIn("EA in-game object ID", fixture["unproven"])
        self.assertIn("regression-test placeholder", fixture["synthetic_ref_warning"])


if __name__ == "__main__":
    unittest.main()
