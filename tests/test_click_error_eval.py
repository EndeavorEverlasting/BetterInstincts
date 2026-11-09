"""Offline falsifiers for click-error scoring and Escape-cancel decisions."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from betterinstincts.click_error_eval import (
    ClickErrorEvalError,
    decide_post_click,
    evaluate_against_chrome,
    evaluate_click,
    evaluate_session,
    load_contract_eval,
)
from betterinstincts.ui_chrome import resolve_target

ROOT = Path(__file__).resolve().parents[1]


class ClickErrorEvalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = load_contract_eval()

    def test_contract_escape_cancel_policy(self) -> None:
        self.assertIs(self.cfg["execute_allowed_default"], False)
        self.assertEqual(self.cfg["architecture"]["selected"], "POST_CLICK_VERIFY_ESCAPE_CANCEL")
        self.assertEqual(self.cfg["recovery"]["on_non_hit"], "ESCAPE_CANCEL")
        self.assertIn("AUTO_RECLICK", self.cfg["recovery"]["forbidden"])

    def test_hit_continues_without_escape(self) -> None:
        hit = evaluate_click(
            intended_x=140,
            intended_y=864,
            observed_x=143,
            observed_y=862,
            client_width=1920,
            client_height=1080,
            cfg=self.cfg,
        )
        decision = decide_post_click(hit, cfg=self.cfg)
        self.assertEqual(hit["classification"], "HIT")
        self.assertEqual(decision["decision"], "CONTINUE")
        self.assertIs(decision["continue_recipe"], True)
        self.assertIsNone(decision["recovery"])
        self.assertIs(decision["execute_allowed"], False)

    def test_above_search_miss_triggers_escape_cancel(self) -> None:
        intended = resolve_target(
            "catalog.search_field",
            mode="BUILD",
            client_width=1920,
            client_height=1080,
        )
        miss = evaluate_against_chrome(
            target_id="catalog.search_field",
            mode="BUILD",
            observed_x=intended["x"],
            observed_y=intended["y"] - 54,
            client_width=1920,
            client_height=1080,
            eval_cfg=self.cfg,
        )
        self.assertEqual(miss["classification"], "MISS")
        self.assertEqual(miss["vertical_bias"], "ABOVE_TARGET")
        self.assertEqual(miss["surface_risk"], "LOT_PUNCH_THROUGH_RISK")
        self.assertEqual(miss["post_click"]["decision"], "ESCAPE_CANCEL")
        self.assertIs(miss["post_click"]["continue_recipe"], False)
        self.assertEqual(miss["post_click"]["recovery"]["chord"], ["ESC"])
        self.assertEqual(miss["post_click"]["recovery"]["hotkey_id"], "CANCEL_HOLD")

    def test_remeasured_search_client_pixels(self) -> None:
        intended = resolve_target(
            "catalog.search_field",
            mode="BUILD",
            client_width=1920,
            client_height=1080,
        )
        self.assertEqual(intended["x"], 140)
        self.assertEqual(intended["y"], 864)

    def test_session_aggregates_above_target_and_escape(self) -> None:
        intended = resolve_target(
            "catalog.search_field",
            mode="BUILD",
            client_width=1920,
            client_height=1080,
        )
        session = evaluate_session(
            [
                {
                    "target_id": "catalog.search_field",
                    "mode": "BUILD",
                    "observed_x": intended["x"],
                    "observed_y": intended["y"],
                    "client_width": 1920,
                    "client_height": 1080,
                },
                {
                    "target_id": "catalog.search_field",
                    "mode": "BUILD",
                    "observed_x": intended["x"],
                    "observed_y": intended["y"] - 80,
                    "client_width": 1920,
                    "client_height": 1080,
                },
            ],
            eval_cfg=self.cfg,
        )
        self.assertEqual(session["trial_count"], 2)
        self.assertEqual(session["classifications"]["HIT"], 1)
        self.assertEqual(session["classifications"]["MISS"], 1)
        self.assertEqual(session["above_target_rate"], 0.5)
        self.assertEqual(session["escape_cancel_count"], 1)
        self.assertEqual(session["lot_punch_through_risk_count"], 1)

    def test_bad_coords_fail_closed(self) -> None:
        with self.assertRaisesRegex(ClickErrorEvalError, "CLICK_COORDS"):
            evaluate_click(
                intended_x=1,
                intended_y=1,
                observed_x="bad",  # type: ignore[arg-type]
                observed_y=1,
                client_width=1920,
                client_height=1080,
                cfg=self.cfg,
            )

    def test_fixture_session_file(self) -> None:
        path = ROOT / "tests" / "fixtures" / "click-error-session.v1.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        session = evaluate_session(payload["trials"], eval_cfg=self.cfg)
        self.assertGreaterEqual(session["above_target_rate"], 0.5)
        self.assertGreater(session["escape_cancel_count"], 0)


if __name__ == "__main__":
    unittest.main()
