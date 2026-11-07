import json
import unittest
from pathlib import Path

from betterinstincts.instincts_host import (
    InstinctsHostError,
    NeedSnapshot,
    all_green,
    is_lab_alias,
    plan,
    plan_to_dict,
    recommend_lab_save,
)

SIX = {n: 0.9 for n in ("hunger", "bladder", "energy", "hygiene", "fun", "social")}
OBJECTS = ("fridge", "toilet", "bed", "shower", "tv", "phone")


class InstinctsHostTests(unittest.TestCase):
    def test_lab_alias_hints(self):
        self.assertTrue(is_lab_alias("BI_TMP_EXPERIMENT_01"))
        self.assertTrue(is_lab_alias("BI_CONT_NEEDS_GREEN_01"))
        self.assertFalse(is_lab_alias("My Saved Game 3"))
        self.assertFalse(is_lab_alias("Richardson Family"))
        self.assertFalse(is_lab_alias("bi_tmp_lower"))

    def test_critical_hygiene_before_leisure(self):
        snap = NeedSnapshot({**SIX, "hygiene": 0.05, "energy": 0.1}, OBJECTS)
        result = plan(snap)
        self.assertEqual(result.domain, "needs")
        self.assertIn(result.next_action, {"wash", "sleep"})
        self.assertFalse(result.all_needs_green)
        self.assertEqual(result.save_recommendation["state"], "HOLD_SAVE")

    def test_missing_objects_block_impossible_remedy(self):
        snap = NeedSnapshot({**SIX, "hygiene": 0.05}, ("fridge", "toilet", "bed", "tv", "phone"))
        result = plan(snap)
        self.assertEqual(result.state, "BLOCKED_MISSING_OBJECTS")
        self.assertEqual(result.next_need, "hygiene")
        self.assertIsNone(result.next_action)

    def test_available_wash_not_blocked_by_missing_bed(self):
        snap = NeedSnapshot({**SIX, "hygiene": 0.05, "energy": 0.08}, ("toilet", "sink", "phone"))
        result = plan(snap)
        self.assertEqual(result.state, "PLAN_READY")
        self.assertEqual(result.next_action, "wash")
        energy = next(s for s in result.steps if s.need == "energy")
        self.assertFalse(energy.objects_present)

    def test_sim_absent_plans_without_queue(self):
        snap = NeedSnapshot({**SIX, "energy": 0.1}, OBJECTS, sim_absent=True)
        result = plan(snap)
        self.assertEqual(result.state, "SIM_ABSENT_PLAN_ONLY")
        self.assertIsNone(result.next_action)

    def test_player_directed_abstains(self):
        snap = NeedSnapshot({**SIX, "hunger": 0.1}, OBJECTS, player_directed=True)
        result = plan(snap)
        self.assertEqual(result.state, "ABSTAIN")
        self.assertIsNone(result.next_action)

    def test_all_green_recommends_bi_cont_save_as_only(self):
        self.assertTrue(all_green(NeedSnapshot(SIX, OBJECTS)))
        result = plan(NeedSnapshot(SIX, OBJECTS))
        self.assertTrue(result.all_needs_green)
        save = result.save_recommendation
        self.assertEqual(save["state"], "SAVE_AS_LAB_CONTINUATION_ONLY")
        self.assertEqual(save["alias"], "BI_CONT_NEEDS_GREEN_01")
        self.assertIn("DELETE", save["forbidden"])
        self.assertIn("OVERWRITE", save["forbidden"])
        self.assertIn("TOUCH_USER_NAMED_SAVE", save["forbidden"])

    def test_user_named_alias_rejected_for_continuation(self):
        with self.assertRaises(InstinctsHostError):
            recommend_lab_save(all_needs_green=True, alias="My Family Save")
        with self.assertRaises(InstinctsHostError):
            recommend_lab_save(all_needs_green=True, alias="BI_TMP_WRONG_CLASS_01")

    def test_plan_json_shape(self):
        payload = plan_to_dict(plan(NeedSnapshot({**SIX, "social": 0.2}, OBJECTS)))
        self.assertIn("steps", payload)
        self.assertEqual(len(payload["steps"]), 6)
        self.assertEqual(payload["next_action"], "socialize")

    def test_cli_script_compiles(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "instincts_plan.py"
        self.assertTrue(script.is_file())
        compile(script.read_text(encoding="utf-8"), str(script), "exec")


if __name__ == "__main__":
    unittest.main()
