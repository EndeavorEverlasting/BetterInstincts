"""Offline coverage for Build Mode floor-activity census."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from betterinstincts.build_floor_activity import (
    evaluate_floor_activity,
    load_contract,
    theme_from_categories,
)
from betterinstincts.host_listener import activate, deactivate, tick
from betterinstincts.player_presence import PresenceProbe


class BuildFloorActivityTests(unittest.TestCase):
    def test_contract_rejects_pixel_heuristic(self):
        cfg = load_contract()
        rejected = {r["id"] for r in cfg["architecture"]["rejected"]}
        self.assertIn("PIXEL_ONLY_HEIGHT_HEURISTIC", rejected)
        self.assertEqual(cfg["architecture"]["selected"], "FLOOR_ACTIVITY_CENSUS")

    def test_single_floor_kitchen_theme(self):
        result = evaluate_floor_activity(
            build_or_buy_mode=True,
            active_story="FLOOR_1",
            stories_touched=["FLOOR_1"],
            floor_items=[
                {"id": "fridge", "category": "appliance", "story": "FLOOR_1"},
                {"id": "island", "category": "counter_island", "story": "FLOOR_1"},
                {"id": "sink", "category": "plumbing", "story": "FLOOR_1"},
            ],
        )
        self.assertEqual(result["state"], "BUILD_FLOOR_ACTIVITY_EVALUATED")
        self.assertEqual(result["activity_span"], "SINGLE_FLOOR")
        self.assertEqual(result["active_story"], "FLOOR_1")
        self.assertEqual(result["active_theme"], "kitchen")
        self.assertIn("appliance", result["optimize_hints"])
        self.assertFalse(result["execute_allowed"])

    def test_multi_floor_span(self):
        result = evaluate_floor_activity(
            build_or_buy_mode=True,
            active_story="2",
            stories_touched=["FLOOR_1", "FLOOR_2"],
            floor_items=[
                {"id": "bed", "category": "bed", "story": "FLOOR_2"},
                {"id": "sofa", "category": "sofa", "story": "FLOOR_1"},
            ],
        )
        self.assertEqual(result["activity_span"], "MULTI_FLOOR")
        self.assertEqual(result["active_story"], "FLOOR_2")
        self.assertEqual(result["floors"]["FLOOR_2"]["theme"], "bedroom")
        self.assertEqual(result["floors"]["FLOOR_1"]["theme"], "living")

    def test_skip_when_not_build_mode(self):
        result = evaluate_floor_activity(build_or_buy_mode=False, active_story="FLOOR_1")
        self.assertEqual(result["state"], "BUILD_FLOOR_ACTIVITY_SKIPPED")

    def test_unknown_story_without_attestation(self):
        result = evaluate_floor_activity(build_or_buy_mode=True)
        self.assertEqual(result["active_story"], "UNKNOWN_STORY")
        self.assertEqual(result["activity_span"], "UNKNOWN_SPAN")
        self.assertEqual(result["active_theme"], "unknown")

    def test_theme_histogram(self):
        row = theme_from_categories(["bed", "bed", "lighting"])
        self.assertEqual(row["theme"], "bedroom")

    def test_listener_tick_attaches_floor_activity(self):
        import betterinstincts.host_listener as hl
        import shutil

        sid = "floor-lab-unit"
        session_path = hl.OUTPUT / sid
        if session_path.exists():
            shutil.rmtree(session_path)
        try:
            activate(sid)
            probe = PresenceProbe(
                foreground_is_sims=True,
                cursor_in_client=False,
                last_input_age_ms=60_000,
                operator_declared_playing=False,
                player_directed_queue=False,
                probe_ok=True,
            )
            receipt = tick(
                sid,
                {
                    "schema": "betterinstincts.host-listener.observation/v1",
                    "needs": {
                        "hunger": 0.8,
                        "bladder": 0.8,
                        "energy": 0.8,
                        "hygiene": 0.8,
                        "fun": 0.8,
                        "social": 0.8,
                    },
                    "queue": [],
                    "location_kind": "home",
                    "capture_ref": "capture:floor-lab",
                    "build_or_buy_mode": True,
                    "active_story": "FLOOR_1",
                    "stories_touched": ["FLOOR_1", "FLOOR_2"],
                    "floor_items": [
                        {
                            "id": "hydro",
                            "category": "planter",
                            "story": "FLOOR_1",
                            "label": "Hydroponic Planter",
                        }
                    ],
                },
                presence_probe=probe,
                idle_ms=15000,
            )
            fa = receipt["build_floor_activity"]
            self.assertEqual(fa["activity_span"], "MULTI_FLOOR")
            self.assertEqual(fa["active_theme"], "outdoor_garden")
            deactivate(sid)
        finally:
            if session_path.exists():
                shutil.rmtree(session_path)

    def test_cli_compiles(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "build_floor_activity.py"
        compile(script.read_text(encoding="utf-8"), str(script), "exec")
        raw = json.loads(
            (Path(__file__).resolve().parents[1] / "contracts" / "build-floor-activity.v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(raw["version"], 1)


if __name__ == "__main__":
    unittest.main()
