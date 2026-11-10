"""Offline falsifiers for click miss-cause learning."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from betterinstincts.click_miss_cause import (
    ClickMissCauseError,
    classify_miss_cause,
    empty_corpus,
    feature_vector,
    ingest_parts_buy_ledger,
    load_contract,
    record_miss_row,
    summarize_corpus,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "click-miss-cause-seed.v1.json"


class ClickMissCauseTests(unittest.TestCase):
    def test_contract_pins_causes_and_features(self):
        cfg = load_contract()
        self.assertFalse(cfg["execute_allowed_default"])
        self.assertIn("PEER_HUD_COLLISION", cfg["miss_causes"])
        self.assertIn("OVERLAY_CLEAR_WIPE", cfg["miss_causes"])
        self.assertEqual(cfg["classifier"]["id"], "RULE_V1")
        names = cfg["feature_schema"]["order"]
        self.assertEqual(names[0], "error_px")
        self.assertIn("peer_hud_busy", names)

    def test_hit_is_none(self):
        out = classify_miss_cause(geometry="HIT")
        self.assertEqual(out["miss_cause"], "NONE")
        self.assertFalse(out["execute_allowed"])

    def test_peer_hud_beats_hitbox_drift(self):
        out = classify_miss_cause(
            geometry="MISS",
            peer_hud_busy=True,
            error_px=200.0,
        )
        self.assertEqual(out["miss_cause"], "PEER_HUD_COLLISION")
        self.assertIn("WAITING_FOR_AGENT", out["recommended_practice"])

    def test_overlay_clear_wipe(self):
        out = classify_miss_cause(
            geometry="MISS",
            overlay_clear_during_peer_lease=True,
            intended_surface_absent=True,
        )
        self.assertEqual(out["miss_cause"], "OVERLAY_CLEAR_WIPE")

    def test_wrong_control(self):
        out = classify_miss_cause(geometry="WRONG_CONTROL", wrong_control=True)
        self.assertEqual(out["miss_cause"], "WRONG_CONTROL")

    def test_zoom_insufficient_before_hitbox(self):
        out = classify_miss_cause(
            geometry="MISS",
            object_pick_identify_used=False,
            zoom_fraction=0.2,
            error_px=90.0,
        )
        self.assertEqual(out["miss_cause"], "ZOOM_INSUFFICIENT")

    def test_feature_vector_length_pinned(self):
        cfg = load_contract()
        feats = feature_vector(geometry="MISS", peer_hud_busy=True, error_px=12.0, cfg=cfg)
        self.assertEqual(len(feats["values"]), len(cfg["feature_schema"]["order"]))
        self.assertEqual(feats["by_name"]["peer_hud_busy"], 1.0)

    def test_override_requires_label_source(self):
        book = empty_corpus()
        with self.assertRaisesRegex(ClickMissCauseError, "CAUSE_OVERRIDE_REQUIRES_LABEL_SOURCE"):
            record_miss_row(
                book,
                target_id="live.phone",
                client_xy=[282, 1055],
                geometry="MISS",
                miss_cause="PEER_HUD_COLLISION",
                classify_kwargs={"geometry": "MISS", "error_px": 10.0},
                label_source="RULE_V1",
            )

    def test_ingest_parts_buy_fixture_labels_interop(self):
        ledger = json.loads(FIXTURE.read_text(encoding="utf-8"))
        book = ingest_parts_buy_ledger(ledger)
        causes = [r["miss_cause"] for r in book["rows"]]
        self.assertIn("OVERLAY_CLEAR_WIPE", causes)
        self.assertIn("WRONG_CONTROL", causes)
        self.assertIn("PEER_HUD_COLLISION", causes)
        self.assertIn("ZOOM_INSUFFICIENT", causes)
        summary = summarize_corpus(book)
        self.assertGreaterEqual(summary["total_rows"], 4)
        ranked = {r["miss_cause"] for r in summary["ranked_practices"]}
        self.assertIn("PEER_HUD_COLLISION", ranked)


if __name__ == "__main__":
    unittest.main()
