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
        self.assertTrue(any(h["id"] == "H1" for h in cfg["root_cause_analysis"]["leading_hypotheses"]))

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
            for y in range(980, 1080):
                for x in range(0, 1920, 3):
                    img.putpixel((x, y), (220, 200, 80))
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
            self.assertEqual(report.next_gate, "CAMERA_THEN_BUILD_LIVE_OR_RESTART")

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
        self.assertNotEqual(out["next_gate"], "EXECUTE_INSTINCTS_PLAN")
        self.assertEqual(out["viewport"]["classification"], "FULL_CLIENT_BLACK")
        self.assertIn(out["viewport_risk"]["risk_level"], {"ELEVATED", "HIGH"})

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
