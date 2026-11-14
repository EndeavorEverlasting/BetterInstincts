from __future__ import annotations

import copy
import unittest

from betterinstincts.agent_session_continuity import (
    SCHEMA, SessionEvidenceError, assess_session,
)


def snapshot() -> dict:
    return {
        "schema": SCHEMA,
        "parent_objective": "Play a disposable Sims household and advance BI-002",
        "completion": {"accepted": False, "evidence_refs": []},
        "game": {
            "state": "PAUSED", "scene": "LIVE",
            "save_scope": "DISPOSABLE_VERIFIED", "capture_ref": "local:observed",
        },
        "player_presence": "INACTIVE",
        "operator_gameplay_permission": True,
        "offline_work": {"action": "", "ready": False},
        "host_access": {"state": "AVAILABLE", "evidence_refs": ["local:pid-observed"]},
    }


class AgentSessionContinuityTests(unittest.TestCase):
    def evaluate(self, data: dict, expected: str, stop: bool = False) -> None:
        outcome = assess_session(data)
        self.assertEqual(outcome["decision"], expected)
        self.assertIs(outcome["terminal_stop_valid"], stop)
        self.assertEqual(outcome["parent_complete"], expected == "COMPLETE_PROVEN")
        self.assertNotIn("game_control_permit", outcome)

    def test_paused_game_is_not_an_agent_completion_boundary(self) -> None:
        self.evaluate(snapshot(), "PREPARE_GAME_EFFECT_ADMISSION")
        self.assertIn("screen_admit", assess_session(snapshot())["next_action"])

    def test_thirteen_minutes_and_interim_p08_report_do_not_close_parent(self) -> None:
        item = snapshot()
        item["elapsed_real_minutes"] = 13
        item["last_report"] = "P08 blocked; played household; paused Friday 10:51"
        self.evaluate(item, "PREPARE_GAME_EFFECT_ADMISSION")

    def test_running_game_means_observe_not_blind_replay(self) -> None:
        item = snapshot()
        item["game"]["state"] = "RUNNING"
        self.evaluate(item, "OBSERVE_GAME")

    def test_player_activity_yields_desktop_not_entire_parent(self) -> None:
        for state in ("ACTIVE", "UNKNOWN"):
            item = snapshot()
            item["player_presence"] = state
            self.evaluate(item, "YIELD_TO_PLAYER", stop=True)
            self.assertTrue(assess_session(item)["resume_condition"])

    def test_player_active_still_permits_separate_read_only_work(self) -> None:
        item = snapshot()
        item["player_presence"] = "ACTIVE"
        item["offline_work"] = {"action": "Inspect existing BI-002 fixtures", "ready": True}
        self.evaluate(item, "CONTINUE_OFFLINE")

    def test_protected_save_denied_even_with_gameplay_permission(self) -> None:
        item = snapshot()
        item["game"]["save_scope"] = "PROTECTED"
        self.evaluate(item, "BLOCKED_EXACT", stop=True)
        item["offline_work"] = {"action": "Inspect game host tests", "ready": True}
        self.evaluate(item, "CONTINUE_OFFLINE")

    def test_unknown_save_scene_and_absent_permission_never_unpause(self) -> None:
        for key, value in (("save_scope", "UNKNOWN"), ("scene", "UNKNOWN")):
            item = snapshot()
            item["game"][key] = value
            self.evaluate(item, "REOBSERVE_HOST")
        item = snapshot()
        item["operator_gameplay_permission"] = False
        self.evaluate(item, "REOBSERVE_HOST")

    def test_offline_work_survives_host_block(self) -> None:
        item = snapshot()
        item["host_access"] = {"state": "UNAVAILABLE", "evidence_refs": ["host:denied"]}
        item["offline_work"] = {"action": "Improve duration fixtures", "ready": True}
        self.evaluate(item, "CONTINUE_OFFLINE")

    def test_host_block_requires_evidence_and_no_independent_work(self) -> None:
        item = snapshot()
        item["host_access"] = {"state": "UNAVAILABLE", "evidence_refs": []}
        self.evaluate(item, "REOBSERVE_HOST")
        item["host_access"]["evidence_refs"] = ["win32:game-process-unavailable"]
        self.evaluate(item, "BLOCKED_EXACT", stop=True)

    def test_completion_must_have_real_references(self) -> None:
        item = snapshot()
        item["completion"]["accepted"] = True
        with self.assertRaisesRegex(SessionEvidenceError, "COMPLETION_REQUIRES_EVIDENCE"):
            assess_session(item)
        item["completion"]["evidence_refs"] = ["local:actual-parent-acceptance"]
        self.evaluate(item, "COMPLETE_PROVEN", stop=True)

    def test_missing_next_action_is_not_proven_terminal(self) -> None:
        item = snapshot()
        item["game"]["state"] = "NOT_VISIBLE"
        item["host_access"] = {"state": "UNKNOWN", "evidence_refs": []}
        self.evaluate(item, "INVESTIGATE_NEXT_GATE")

    def test_offline_action_must_be_explicit(self) -> None:
        item = snapshot()
        item["offline_work"] = {"action": "", "ready": True}
        with self.assertRaisesRegex(SessionEvidenceError, "explicit action"):
            assess_session(item)

    def test_input_is_never_mutated(self) -> None:
        item = snapshot()
        original = copy.deepcopy(item)
        assess_session(item)
        self.assertEqual(item, original)


if __name__ == "__main__":
    unittest.main()
