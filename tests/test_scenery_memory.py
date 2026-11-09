"""A wrong camera scene becomes reusable metadata, never blind navigation."""
from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from betterinstincts.scenery_memory import (
    record_scenery, review_scenery, propose_revisit, SceneryMemoryError,
    validate_registry,
)
from betterinstincts.scenes import load_catalog
from scripts import scenery_memory as cli

CAP="capture:wrong-street-1"
REG={"schema":"betterinstincts.scenery-discoveries/v1","records":[]}

def view(**changes):
    d={"source":"HOST_CAPTURE","capture_ref":CAP,
       "game_version":load_catalog()["game_version"],"scene_id":"live_mode",
       "world_ref":"world:willow","lot_ref":"lot:demo",
       "view_kind":"TOP_DOWN_STREET","view_sector":"north_block",
       "camera_revision":"camera:52","landmark_tokens":["road_crosswalk","lamp_post"],
       "scene_cues":[{"source":"visual","token":"street_layout"},
                     {"source":"operator","token":"not_goal_location"}],
       "intended_goal_id":"goal:find-bloomer","intended_target_id":"item:aok",
       "on_intended_target":False}
    d.update(changes);return d

class SceneryMemoryTests(unittest.TestCase):
    def test_wrong_street_becomes_independent_reviewable_scene_not_game_mode(self):
        out=record_scenery(REG,capture_ref=CAP,observation=view())
        self.assertEqual(out["state"],"SCENERY_CANDIDATE_RECORDED")
        self.assertEqual(out["record"]["view_kind"],"TOP_DOWN_STREET")
        self.assertEqual(out["record"]["reason"],"OFF_TARGET")
        self.assertEqual(out["record"]["status"],"CANDIDATE")
        self.assertFalse(out["execute_allowed"])
        self.assertNotIn("click",out["record"])
        self.assertNotIn("screenshot",out["record"])
        self.assertEqual(out["record"]["game_version"],load_catalog()["game_version"])

    def test_same_view_deduplicates_but_does_not_approve_route(self):
        first=record_scenery(REG,capture_ref=CAP,observation=view())
        again=record_scenery(first["registry"],capture_ref=CAP,
                             observation=view(camera_revision="camera:53"))
        self.assertEqual(again["state"],"SCENERY_DEDUPLICATED")
        self.assertEqual(len(again["registry"]["records"]),1)
        self.assertEqual(again["record"]["sightings"],2)
        self.assertEqual(again["record"]["status"],"CANDIDATE")
        self.assertEqual(propose_revisit(
            again["registry"],signature=again["signature"],
            game_version=load_catalog()["game_version"],
            current_goal_id="goal:find-bloomer",target_id="item:aok"
        )["state"],"SCENERY_REVISIT_NOT_ADMITTED")

    def test_reviewed_record_is_still_only_a_hint(self):
        observed=record_scenery(REG,capture_ref=CAP,observation=view())
        reviewed=review_scenery(observed["registry"],signature=observed["signature"],
            review={"source":"OPERATOR_REVIEW","approved":True,
                    "review_ref":"review:42","route_label":"north_street"})
        result=propose_revisit(reviewed,signature=observed["signature"],
            game_version=load_catalog()["game_version"],
            current_goal_id="goal:find-bloomer",target_id="item:aok")
        self.assertEqual(result["state"],"SCENERY_REVISIT_CANDIDATE")
        self.assertFalse(result["execute_allowed"])
        self.assertIn("MAP_LEASE",result["next"])
        bad=propose_revisit(reviewed,signature=observed["signature"],
            game_version="other.patch",current_goal_id="goal:find-bloomer",target_id="item:aok")
        self.assertEqual(bad["state"],"SCENERY_REVISIT_NOT_ADMITTED")

    def test_untrusted_scene_without_two_cues_fails_closed(self):
        for mutation in (
            {"scene_cues":[{"source":"visual","token":"guess"}]},
            {"source":"MODEL_GUESS"},{"game_version":"unknown"},
            {"landmark_tokens":[]},
        ):
            with self.subTest(mutation=mutation):
                with self.assertRaises(SceneryMemoryError):
                    record_scenery(REG,capture_ref=CAP,observation=view(**mutation))

    def test_explicit_cli_write_only_when_apply(self):
        with tempfile.TemporaryDirectory() as root:
            target=Path(root)/"scenery-discoveries.v1.json"
            target.write_text(json.dumps(REG),encoding="utf-8")
            args=["record","--capture-ref",CAP,
                  "--observation-json",json.dumps(view())]
            with patch.object(cli,"REGISTRY",target):
                self.assertEqual(cli.main(args),0)
                self.assertEqual(len(json.loads(target.read_text())["records"]),0)
                self.assertEqual(cli.main(args+["--apply"]),0)
                self.assertEqual(len(json.loads(target.read_text())["records"]),1)
                self.assertEqual(cli.main(args+["--apply"]),0)
                self.assertEqual(json.loads(target.read_text())["records"][0]["sightings"],2)

if __name__=="__main__":unittest.main()
