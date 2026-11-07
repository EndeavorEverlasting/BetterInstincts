"""P04 reentry: guard real-game boundaries even when source and CI are merged."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SceneHandoffTests(unittest.TestCase):
    def test_post_merge_proof_and_future_live_gate_stay_separate(self):
        manifest = json.loads((ROOT / "plans/active/BI-SCENE-MAP.dispatch.v1.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "betterinstincts.scene-map.dispatch/v1")
        self.assertEqual(manifest["implementation"]["pr"], 15)
        self.assertEqual(manifest["implementation"]["post_merge_ci_conclusion"], "success")
        self.assertEqual(manifest["implementation"]["offline_tests_passed"], 139)
        self.assertEqual(manifest["parent"]["id"], "BI-002")
        self.assertEqual(manifest["parent"]["state"], "ACTIVE")
        self.assertFalse(manifest["parent"]["live_mode_observed"])
        self.assertEqual(manifest["parent"]["baseline_trials"], 0)
        self.assertEqual(manifest["parent"]["modified_trials"], 0)
        self.assertEqual(manifest["safety"]["unknown_save"], "UNKNOWN_PROTECTED")
        self.assertFalse(manifest["safety"]["save_name_is_authority"])

    def test_only_local_agent_can_certify_live_experience(self):
        manifest = json.loads((ROOT / "plans/active/BI-SCENE-MAP.dispatch.v1.json").read_text(encoding="utf-8"))
        lanes = {l["id"]: l for l in manifest["lanes"]}
        self.assertEqual(lanes["SCENE_CAPTURE"]["host"], "LOCAL_AGENT_RUNTIME")
        self.assertEqual(lanes["HUNGER_LIVE"]["host"], "LOCAL_AGENT_RUNTIME")
        self.assertNotEqual(lanes["HUNGER_LIVE"]["state"], "SUCCESS")
        self.assertEqual(lanes["SAVE_OWNERSHIP"]["host"], "OPERATOR_OR_PHYSICAL_RUNTIME")
        text = (ROOT / "plans/active/BI-SCENE-MAP.HANDOFF.md").read_text(encoding="utf-8")
        for needle in ("P00", "P01", "P95", "P08", "P82", "P07", "P04",
                       "USER_PROTECTED", "UNKNOWN_PROTECTED", "CAS", "Live Mode"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
