"""Offline P82 adversarial checks for P95 preference action port.

No real Sims PID, SendInput, screen control, or save mutation.
"""
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import preference_prompts as cli


def observed(stage="YES", *, captured_at=None):
    clock = int(time.time() * 1000) if captured_at is None else captured_at
    return {
        "dialog_class": (
            "sim_preference_confirmation" if stage == "OK" else "sim_preference_offer"
        ),
        "dialog_stage": "confirmation" if stage == "OK" else "offer",
        "scene": "live",
        "sim_ref": "sim:1",
        "topic_id": "gardening",
        "offer_kind": "like",
        "capture_ref": "capture:second" if stage == "OK" else "capture:first",
        "visible_buttons": ["OK"] if stage == "OK" else ["YES", "NO"],
        "captured_at_epoch_ms": clock,
        "observed_process_id": 42,
        "sim_selected": True,
        "player_queue_clear": True,
        "save_authorized": True,
        "game_build_confirmed": True,
        "target_boxes": {stage: [400, 300, 480, 335]},
    }


@contextmanager
def admitted(*args, **kwargs):
    def ensure_ready():
        return {"screen_control_allowed": True, "reason": "IDLE_CONFIRMED"}
    yield ensure_ready


class PreferenceAdapterTests(unittest.TestCase):
    def test_freshness_and_game_ownership_fail_closed(self):
        old = observed(captured_at=int(time.time() * 1000) - 100000)
        with self.assertRaisesRegex(cli.PreferenceStepError, "STALE_OR_UNDATED"):
            cli._validate_live_evidence(old, process_id=42)
        fresh = observed()
        fresh["observed_process_id"] = 999
        with self.assertRaisesRegex(cli.PreferenceStepError, "GAME_SIM_SAVE_QUEUE_NOT_OBSERVED"):
            cli._validate_live_evidence(fresh, process_id=42)
        fresh["observed_process_id"] = 42
        fresh["player_queue_clear"] = False
        with self.assertRaisesRegex(cli.PreferenceStepError, "GAME_SIM_SAVE_QUEUE_NOT_OBSERVED"):
            cli._validate_live_evidence(fresh, process_id=42)

    def test_reject_unsafe_receipt_destinations(self):
        with TemporaryDirectory() as tmp:
            with patch.object(cli, "OUTPUT", Path(tmp)), patch.object(cli, "ROOT", Path(tmp)):
                root = Path(tmp)
                with self.assertRaisesRegex(cli.PreferenceStepError, "RECEIPT_OUTSIDE_GAME_HOST"):
                    cli._receipt_path(root / "not-allowed.json")
                self.assertEqual(cli._receipt_path(root / "good.json"), root / "good.json")

    def test_one_yes_input_and_one_noncanonical_interrupt(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "yes.json"
            with (
                patch.object(cli.sys, "platform", "win32"),
                patch("betterinstincts.screen_admit.require_execute_session"),
                patch("betterinstincts.screen_admit.admitted_screen_lease", side_effect=admitted),
                patch("scripts.preference_prompts._foreground_game_window", return_value=777),
                patch("scripts.preference_prompts._client_target", return_value=(434, 312)),
                patch("scripts.win32_input.send_click") as click,
                patch.object(cli, "OUTPUT", Path(tmp)),
                patch.object(cli, "ROOT", Path(tmp)),
            ):
                receipt = cli.execute_step(
                    observed(), stage="YES", session_id="session:42", process_id=42,
                    idle_ms=30000, receipt_path=out,
                )
            self.assertEqual(receipt["state"], "INPUT_DISPATCHED")
            self.assertEqual(receipt["step"], "YES")
            self.assertTrue(out.exists())
            click.assert_called_once_with(434, 312, between_sec=0.04)

    def test_ok_requires_same_session_same_pid_receipt(self):
        later = observed("OK", captured_at=int(time.time() * 1000))
        earlier = dict(later)
        earlier.update({
            "schema": "betterinstincts.preference-step-receipt/v1",
            "state": "INPUT_DISPATCHED", "step": "YES",
            "session_id": "other-session", "process_id": 42,
            "captured_at_epoch_ms": later["captured_at_epoch_ms"] - 1000,
            "capture_ref": "capture:first",
        })
        with patch.object(cli.sys, "platform", "win32"):
            with self.assertRaisesRegex(cli.PreferenceStepError, "SAME_SESSION_PID_RECEIPT"):
                cli.execute_step(
                    later, stage="OK", session_id="session:42", process_id=42,
                    idle_ms=30000, receipt_path=Path("out.json"),
                    previous_receipt=earlier,
                )

    def test_unknown_topic_never_calls_input(self):
        value = observed()
        value["topic_id"] = "unrecognized"
        with patch.object(cli.sys, "platform", "win32"), patch(
            "scripts.win32_input.send_click"
        ) as send:
            with self.assertRaisesRegex(cli.PreferencePromptError, "STAGE_NOT_AUTHORIZED"):
                cli.execute_step(value, stage="YES", session_id="session:42",
                                 process_id=42, idle_ms=30000, receipt_path=Path("out.json"))
        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
