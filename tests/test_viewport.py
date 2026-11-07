import tempfile
import unittest
from pathlib import Path

from PIL import Image

from betterinstincts.host_stack import evaluate_turn
from betterinstincts.viewport import (
    SCENE_ID,
    analyze_image,
    load_contract,
    predict_risk,
    report_to_dict,
)

ROOT = Path(__file__).resolve().parents[1]
OBSERVED_BLACK = ROOT / "dist" / "game-host" / "bi002-quiz-boot" / "printwindow-after-black.png"
SIX = {n: 0.9 for n in ("hunger", "bladder", "energy", "hygiene", "fun", "social")}


class ViewportTests(unittest.TestCase):
    def test_contract_loads_with_rca_and_ladder(self):
        cfg = load_contract()
        self.assertEqual(cfg["scene_id"], SCENE_ID)
        self.assertIn("root_cause_analysis", cfg)
        self.assertGreaterEqual(len(cfg["recovery_ladder"]), 5)
        self.assertTrue(any(a["id"] == "A2" for a in cfg["avoidance"]))
        self.assertTrue(any(a["id"] == "A7" for a in cfg["avoidance"]))
        self.assertTrue(any(h["id"] == "H5" for h in cfg["root_cause_analysis"]["leading_hypotheses"]))
        self.assertTrue(any(c["id"] == "C9" for c in cfg["root_cause_analysis"]["causal_chain"]))
        self.assertTrue(any(h["id"] == "H1" for h in cfg["root_cause_analysis"]["leading_hypotheses"]))
        ladder = [row["step"] for row in cfg["recovery_ladder"]]
        self.assertIn("ENTER_BUILD_BUY_UNSTICK", ladder)
        self.assertLess(
            ladder.index("ENTER_BUILD_BUY_UNSTICK"),
            ladder.index("EXIT_BUILD_BUY_TO_LIVE"),
        )
        self.assertTrue(any(f["id"] == "FB_BUILD_BUY_UNSTICK" for f in cfg["fallback_mechanisms"]))

    def test_full_black_synthetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "black.png"
            Image.new("RGB", (1920, 1080), (0, 0, 0)).save(path)
            report = analyze_image(path)
            self.assertEqual(report.state, "VIEWPORT_ANOMALY")
            self.assertEqual(report.classification, "FULL_CLIENT_BLACK")
            self.assertEqual(report.scene_id, SCENE_ID)
            self.assertIn("AUTHORIZED_GAME_RESTART", report.recovery_ladder)
            payload = report_to_dict(report)
            self.assertTrue(payload["rca_summary"])

    def test_content_present_synthetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scene.png"
            img = Image.new("RGB", (1920, 1080), (30, 90, 40))
            for y in range(1000, 1080):
                for x in range(0, 1920, 4):
                    img.putpixel((x, y), (200, 180, 60))
            img.save(path)
            report = analyze_image(path)
            self.assertEqual(report.state, "VIEWPORT_OK")
            self.assertEqual(report.classification, "CONTENT_PRESENT")

    def test_hud_alive_world_black(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dark_world.png"
            img = Image.new("RGB", (1920, 1080), (2, 2, 2))
            # Top Live HUD only — uniform strip, not a Buy catalog tray.
            for y in range(0, 70):
                for x in range(1100, 1920, 2):
                    img.putpixel((x, y), (180, 180, 180))
            img.save(path)
            report = analyze_image(path)
            self.assertEqual(report.classification, "VIEWPORT_BLACK_HUD_ALIVE")
            self.assertEqual(report.next_gate, "CAMERA_RECOVER_THEN_RECAPTURE")

    def test_void_lot_platform_wireframe(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wireframe.png"
            img = Image.new("RGB", (1920, 1080), (0, 0, 0))
            # Sparse bright rectangle edges in world region (lot platform).
            for x in range(700, 1200):
                img.putpixel((x, 500), (180, 200, 220))
                img.putpixel((x, 560), (180, 200, 220))
            for y in range(500, 561):
                img.putpixel((700, y), (180, 200, 220))
                img.putpixel((1199, y), (180, 200, 220))
            img.save(path)
            report = analyze_image(path, step=4)
            self.assertEqual(report.classification, "VOID_LOT_PLATFORM_WIREFRAME")
            self.assertEqual(report.next_gate, "ENTER_BUILD_BUY_UNSTICK")

    def test_build_buy_catalog_recovery_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "buy_catalog.png"
            img = Image.new("RGB", (1920, 1080), (2, 2, 2))
            # High-variance Buy tray along the bottom (catalog icons).
            colors = [(220, 180, 60), (40, 120, 200), (200, 80, 80), (80, 200, 120)]
            for y in range(960, 1080):
                for x in range(0, 1920, 2):
                    img.putpixel((x, y), colors[(x // 40) % len(colors)])
            img.save(path)
            report = analyze_image(path, step=4)
            self.assertEqual(report.classification, "BUILD_BUY_CATALOG_RECOVERY")
            self.assertEqual(report.state, "VIEWPORT_MODE_BUILD_BUY")
            self.assertEqual(report.next_gate, "EXIT_BUY_TO_LIVE_OR_OPERATOR_SAVE_EXIT")

    def test_enter_build_buy_unstick_step_is_dispatchable(self):
        from scripts import viewport_recover as recover

        self.assertTrue(hasattr(recover, "run_recovery_step"))
        # Dry structural contract: step name + Build coords match LOCAL_OBSERVED unstick.
        self.assertEqual(recover.HUD_BUILD, (1505, 22))
        self.assertEqual(recover.HUD_LIVE_FROM_BUILD, (1585, 35))

    def test_predict_risk_elevated_after_cas_abort(self):
        risk = predict_risk({
            "after_cas_abort": True,
            "after_manage_worlds": True,
            "empty_lot": True,
            "night": True,
            "no_lights_placed": True,
        })
        self.assertEqual(risk["risk_level"], "HIGH")
        self.assertIn("PRINTWINDOW_CAPTURE", risk["required_before_clicks"])

    def test_host_stack_viewport_outranks_needs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "black.png"
            Image.new("RGB", (640, 360), (0, 0, 0)).save(path)
            viewport = report_to_dict(analyze_image(path))
        out = evaluate_turn(
            {**SIX, "hunger": 0.05},
            available_objects=("fridge",),
            viewport=viewport,
            viewport_context={"after_cas_abort": True},
        )
        self.assertEqual(out["next_gate"], "ENTER_BUILD_BUY_UNSTICK")
        self.assertEqual(out["viewport"]["classification"], "FULL_CLIENT_BLACK")
        self.assertEqual(out["fallback"]["mechanism"], "ENTER_BUILD_BUY_UNSTICK")
        self.assertIn(out["viewport_risk"]["risk_level"], {"ELEVATED", "HIGH"})

    def test_host_stack_build_buy_blocks_needs(self):
        out = evaluate_turn(
            {**SIX, "hunger": 0.05},
            available_objects=("fridge",),
            viewport={
                "state": "VIEWPORT_MODE_BUILD_BUY",
                "classification": "BUILD_BUY_CATALOG_RECOVERY",
                "next_gate": "EXIT_BUY_TO_LIVE_OR_OPERATOR_SAVE_EXIT",
            },
        )
        self.assertEqual(out["next_gate"], "EXIT_BUY_TO_LIVE_OR_OPERATOR_SAVE_EXIT")
        self.assertEqual(out["fallback"]["mechanism"], "BUILD_BUY_CATALOG_RECOVERY")
        self.assertNotEqual(out["next_gate"], "EXECUTE_INSTINCTS_PLAN")

    def test_observed_black_capture_if_present(self):
        if not OBSERVED_BLACK.is_file():
            self.skipTest("observed black capture not in workspace")
        report = analyze_image(OBSERVED_BLACK)
        self.assertEqual(report.state, "VIEWPORT_ANOMALY")
        self.assertIn(report.classification, {
            "FULL_CLIENT_BLACK", "VIEWPORT_NEAR_BLACK", "VIEWPORT_BLACK_HUD_ALIVE",
        })

    def test_cli_compiles(self):
        script = ROOT / "scripts" / "viewport_recover.py"
        compile(script.read_text(encoding="utf-8"), str(script), "exec")


if __name__ == "__main__":
    unittest.main()
