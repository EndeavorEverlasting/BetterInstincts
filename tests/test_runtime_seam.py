"""Native status-only, effect-free seam notice classification."""
from __future__ import annotations

import unittest
from betterinstincts.runtime_seam import GAPS, notice_for

BUILD = "1.121.361.1020"


class NativeSeamTest(unittest.TestCase):
    def test_known_missing_evidence_is_bounded_and_stable(self):
        first = notice_for("PORTRAIT_EVIDENCE_UNQUALIFIED", game_build=BUILD, session="run-private")
        repeat = notice_for("PORTRAIT_EVIDENCE_UNQUALIFIED", game_build=BUILD, session="run-private")
        self.assertEqual(first, repeat)
        self.assertEqual(first["capability"], "NATIVE_PORTRAIT_OBSERVER_EVIDENCE")
        self.assertEqual(first["effect_admission"], "NOT_GRANTED")
        self.assertEqual(len(first["session_tag"]), 16)
        self.assertNotIn("run-private", str(first))
        self.assertEqual(first["stage"], "native_runtime")

    def test_normal_yields_and_pending_actions_are_not_seams(self):
        for result in ("YIELD_TO_PLAYER", "RESTOCK_CONTROL_HELD_OR_UNVERIFIED",
                       "QUEUED", "NATIVE_DISPATCH_RECONCILIATION",
                       "PORTRAIT_SELECTION_REOBSERVE", "NO_NATIVE_PROPOSAL",
                       "NATIVE_PORT_FANTASY", "", None):
            self.assertIsNone(notice_for(result, game_build=BUILD), result)

    def test_unknown_or_unsafe_build_and_status_fail_closed(self):
        self.assertIsNone(notice_for("NATIVE_FRAME_UNQUALIFIED", game_build="latest"))
        self.assertIsNone(notice_for("NATIVE_FRAME_UNQUALIFIED", game_build=BUILD, session=None)["session_tag"])
        self.assertEqual(set(GAPS), {"NATIVE_FRAME_UNQUALIFIED", "NATIVE_SESSION_REBIND_REQUIRED",
                                    "PORTRAIT_EVIDENCE_UNQUALIFIED", "NATIVE_PROPOSAL_ID_UNVERIFIED"})


if __name__ == "__main__":
    unittest.main()
