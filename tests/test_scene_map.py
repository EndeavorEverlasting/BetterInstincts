import copy
import json
from pathlib import Path
import tempfile
import unittest

from betterinstincts.scenes import (SceneError, classify, load_catalog,
                                    propose_transition, validate_catalog)
from scripts import scene_map


class SceneCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def test_broad_scene_coverage_without_fabricated_runtime(self):
        ids = {scene["id"] for scene in self.catalog["scenes"]}
        for name in ("startup_splash", "startup_loading", "main_menu", "load_game_picker",
                     "cas_story_prompt", "worlds_loading", "world_selection", "neighborhood_map",
                     "library_home", "gallery_home", "live_mode", "build_buy", "unknown"):
            self.assertIn(name, ids)
        self.assertGreaterEqual(len(ids), 30)
        self.assertIn("NOT_COMPLETE", self.catalog["coverage"])

    def test_two_independent_cues_produce_candidate_not_live_proof(self):
        scene = next(x for x in self.catalog["scenes"] if x["id"] == "cas_story_prompt")
        result = classify(self.catalog, self.catalog["game_version"], scene["required_cues"])
        self.assertEqual(result["state"], "CANDIDATE_UNVERIFIED")
        self.assertEqual(result["scene_id"], "cas_story_prompt")
        self.assertIn("NO_SCREENSHOT_VALIDATION", result["proof_ceiling"])

    def test_one_cue_or_unknown_scene_abstains(self):
        scene = self.catalog["scenes"][2]
        result = classify(self.catalog, self.catalog["game_version"], scene["required_cues"][:1])
        self.assertEqual(result["scene_id"], "unknown")
        self.assertEqual(propose_transition(self.catalog, result, "main_menu")["state"], "BLOCKED")

    def test_ambiguous_scene_never_guesses(self):
        a = self.catalog["scenes"][0]["required_cues"]
        b = self.catalog["scenes"][1]["required_cues"]
        result = classify(self.catalog, self.catalog["game_version"], a + b)
        self.assertEqual(result["state"], "AMBIGUOUS_OR_UNKNOWN")
        self.assertEqual(result["scene_id"], "unknown")

    def test_unknown_patch_fails_closed(self):
        cues = self.catalog["scenes"][0]["required_cues"]
        r = classify(self.catalog, "1.999.999.9999", cues)
        self.assertEqual(r["state"], "UNKNOWN_PATCH")

    def test_transition_is_proposal_not_automated_execution(self):
        scene = next(x for x in self.catalog["scenes"] if x["id"] == "main_menu")
        r = classify(self.catalog, self.catalog["game_version"], scene["required_cues"])
        self.assertEqual(propose_transition(self.catalog, r, "load_game_picker")["state"], "PROPOSED_MANUAL_ONLY")
        self.assertEqual(propose_transition(self.catalog, r, "live_mode")["reason"], "TRANSITION_NOT_ALLOWED")

    def test_forbidden_graph_weakening_rejected(self):
        c = copy.deepcopy(self.catalog)
        c["global_forbidden_actions"] = ["RESUME"]
        with self.assertRaisesRegex(SceneError, "FORBIDDEN_ACTIONS_WEAKENED"):
            validate_catalog(c)

    def test_unknown_scene_has_no_transitions(self):
        c = copy.deepcopy(self.catalog)
        next(x for x in c["scenes"] if x["id"] == "unknown")["transitions"].append(
            {"target": "main_menu", "gate": "OPERATOR_CONFIRMATION", "execution": "MANUAL_ONLY"})
        with self.assertRaisesRegex(SceneError, "UNKNOWN_SCENE_MUST_BE_TERMINAL"):
            validate_catalog(c)

    def test_cli_synthetic_cues_do_not_persist_or_execute(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "cues.json"
            scene = next(x for x in self.catalog["scenes"] if x["id"] == "main_menu")
            path.write_text(json.dumps(scene["required_cues"]), encoding="utf-8")
            from contextlib import redirect_stdout
            import io
            out = io.StringIO()
            with redirect_stdout(out):
                code = scene_map.main(["--game-version", self.catalog["game_version"],
                                       "--observations", str(path), "--target", "new_game_entry"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.getvalue())["proposal"]["execution"], "MANUAL_ONLY")
            self.assertEqual(len(list(Path(td).iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
