import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts.gardening_service import GardeningServiceError, evaluate_gardening_turn
from betterinstincts.host_listener import HostListenerError, activate, tick
from betterinstincts.host_stack import evaluate_turn
from betterinstincts.need_services import evaluate_need_services
from betterinstincts.player_presence import PresenceProbe


GREEN = dict(hunger=.9, bladder=.9, energy=.9, hygiene=.9, fun=.9, social=.9)
CAPTURE = "capture:garden-current"


def action(action_id="PLANT", **changes):
    row = dict(action_id=action_id, label="Plant", target_ref="plantable:observed-1",
               capture_ref=CAPTURE, available=True)
    row.update(changes)
    return row


def context(**changes):
    row = dict(capture_ref=CAPTURE, observed_at_unix=time.time(), scene_verified=True,
               queue_verified=True, responsibilities_checked=True,
               minutes_until_obligation=120, observed_actions=[action()])
    row.update(changes)
    return row


class GardeningServiceTests(unittest.TestCase):
    def run_service(self, needs=None, ctx=None, **kwargs):
        needs = dict(GREEN if needs is None else needs)
        report = evaluate_need_services(needs, available_objects=["bed", "phone"], capture_ref=CAPTURE)
        return evaluate_gardening_turn(needs, report, ctx or context(), capture_ref=CAPTURE, **kwargs)

    def test_one_observed_plant_and_goal_preserved_until_outcome(self):
        out = self.run_service(ctx=context(observed_actions=[action(), action("HARVEST")]))
        self.assertEqual(out["gate"], "GARDEN_ACTION_READY")
        self.assertEqual(len(out["next_actions"]), 1)
        self.assertEqual(out["next_actions"][0]["action_id"], "PLANT")
        self.assertFalse(out["dispatch_authorized"])
        self.assertNotIn("COMPLETE", out["goal_state"])

    def test_actual_maintenance_before_new_planting(self):
        out = self.run_service(ctx=context(observed_actions=[action(), action("WATER", label="Water")]))
        self.assertEqual(out["next_actions"][0]["action_id"], "WATER")

    def test_low_energy_with_unverified_remedy_inspects_behavior_not_building(self):
        out = self.run_service(needs={**GREEN, "energy": .1})
        self.assertEqual(out["gate"], "GARDEN_INSPECT_NEED_ACTIONS")
        self.assertEqual(out["next_actions"], [])
        self.assertEqual(out["goal_state"], "PENDING")
        self.assertEqual(out["action"], "INSPECT_EXISTING_NEED_INTERACTIONS")

    def test_observed_need_remedy_before_garden(self):
        out = self.run_service(needs={**GREEN, "energy": .1}, ctx=context(
            observed_actions=[action(), action("SLEEP_IN_BED", label="Sleep")]))
        self.assertEqual(out["gate"], "GARDEN_RECOVER_NEEDS")
        self.assertEqual(out["next_actions"][0]["action_id"], "SLEEP_IN_BED")

    def test_ground_sleep_uses_existing_need_service_and_actual_enabled_menu(self):
        needs = {**GREEN, "energy": .05}
        report = evaluate_need_services(needs, available_objects=["observed_sleepable_ground"],
                                        capture_ref=CAPTURE)
        self.assertEqual(report["primary_route"], "SLEEP_ON_GROUND")
        for enabled in (True, False):
            out = evaluate_gardening_turn(needs, report, context(observed_actions=[
                action("SLEEP_ON_GROUND", label="Sleep Here", available=enabled)
            ]), capture_ref=CAPTURE)
            self.assertEqual(out["gate"], "GARDEN_RECOVER_NEEDS" if enabled else "GARDEN_INSPECT_NEED_ACTIONS")

    def test_player_busy_school_and_absence(self):
        for flag in ("player_directed", "already_busy", "school_day_active", "sim_absent", "build_or_buy_mode"):
            with self.subTest(flag=flag):
                out = self.run_service(**{flag: True})
                self.assertEqual(out["next_actions"], [])

    def test_homework_and_deadline_protected(self):
        self.assertEqual(self.run_service(homework_pending=True)["gate"], "GARDEN_RESPONSIBILITY_FIRST")
        for minutes in (0, 20, 45):
            with self.subTest(minutes=minutes):
                out = self.run_service(ctx=context(minutes_until_obligation=minutes))
                self.assertEqual(out["gate"], "GARDEN_RESPONSIBILITY_FIRST")
        self.assertEqual(self.run_service(ctx=context(responsibilities_checked=False))["gate"],
                         "GARDEN_INSPECT_RESPONSIBILITIES")
        self.assertEqual(self.run_service(ctx=context(minutes_until_obligation=None))["gate"],
                         "GARDEN_INSPECT_RESPONSIBILITIES")
        self.assertEqual(self.run_service(ctx=context(minutes_until_obligation=None,
                                                     no_upcoming_obligation=True))["gate"], "GARDEN_ACTION_READY")

    def test_stale_and_unknown_evidence_never_selects(self):
        for changes in (dict(observed_at_unix=time.time()-181), dict(scene_verified=False),
                        dict(queue_verified=False), dict(capture_ref="capture:older"),
                        dict(observed_at_unix=float("nan"))):
            with self.subTest(changes=changes):
                self.assertEqual(self.run_service(ctx=context(**changes))["gate"], "GARDEN_REOBSERVE")

    def test_disabled_stale_and_unrelated_actions_not_selected(self):
        for row in (action(available=False), action(capture_ref="capture:old"),
                    action("BUILD_PLACE_IF_AUTHORIZED"), action("MOTHERLODE"),
                    action("TEND_GARDEN"), action(target_ref="")):
            with self.subTest(row=row):
                self.assertEqual(self.run_service(ctx=context(observed_actions=[row]))["next_actions"], [])

    def test_invalid_bounded_observation_rejected(self):
        for changes in (dict(observed_actions=[action()]*25), dict(observed_actions="Plant"),
                        dict(minutes_until_obligation=True), dict(minutes_until_obligation=-1)):
            with self.subTest(changes=changes), self.assertRaises(GardeningServiceError):
                self.run_service(ctx=context(**changes))

    def test_inputs_unchanged(self):
        ctx = context()
        before = copy.deepcopy(ctx)
        self.run_service(ctx=ctx)
        self.assertEqual(ctx, before)


class GardeningHostIntegrationTests(unittest.TestCase):
    def test_host_uses_same_need_service_once_and_never_builds_on_failed_route(self):
        with patch("betterinstincts.host_stack.evaluate_need_services", wraps=evaluate_need_services) as service:
            out = evaluate_turn({**GREEN, "energy": .1}, gardening=context(), queue=[],
                                capture_ref=CAPTURE, location_kind="home",
                                viewport={"state": "VIEWPORT_OK"})
        self.assertEqual(service.call_count, 1)
        self.assertEqual(out["next_gate"], "GARDEN_INSPECT_NEED_ACTIONS")
        self.assertNotIn("PLACE", out["fallback"]["action"])
        self.assertEqual(out["gardening"]["goal_state"], "PENDING")

    def test_actual_garden_path_and_parent_viewport_player_guards(self):
        base = dict(gardening=context(), capture_ref=CAPTURE, queue=[], location_kind="home",
                    viewport={"state": "VIEWPORT_OK"})
        self.assertEqual(evaluate_turn(GREEN, **base)["next_gate"], "GARDEN_ACTION_READY")
        self.assertEqual(evaluate_turn(GREEN, **base, player_directed=True)["next_gate"],
                         "RESPECT_PLAYER_OR_BUSY_STATE")
        out = evaluate_turn(GREEN, **{**base, "viewport": {"state": "UNKNOWN"}})
        self.assertNotEqual(out["next_gate"], "GARDEN_ACTION_READY")

    def test_listener_transports_gardening_to_stack_without_dispatch(self):
        with tempfile.TemporaryDirectory() as temp, patch(
            "betterinstincts.host_listener.ROOT", Path(temp).resolve()
        ), patch("betterinstincts.host_listener.OUTPUT", Path(temp).resolve() / "dist/host-listener"):
            activate("garden-test")
            obs = dict(schema="betterinstincts.host-listener.observation/v1", needs=GREEN,
                       queue=[], location_kind="home", capture_ref=CAPTURE,
                       viewport={"state": "VIEWPORT_OK"}, gardening=context())
            out = tick("garden-test", obs, presence_probe=PresenceProbe(
                False, False, last_input_age_ms=20000, probe_ok=True))
            self.assertEqual(out["host_stack"]["next_gate"], "GARDEN_ACTION_READY")
            self.assertFalse(out["execute_clicks"])
            with self.assertRaisesRegex(HostListenerError, "OBSERVATION_GARDENING_INVALID"):
                tick("garden-test", {**obs, "gardening": []})

    def test_absent_gardening_preserves_existing_path(self):
        out = evaluate_turn(GREEN, capture_ref=CAPTURE, viewport={"state": "VIEWPORT_OK"})
        self.assertIsNone(out["gardening"])
        self.assertEqual(out["next_gate"], "LAB_SAVE_AS_BI_CONT_WHEN_AUTHORIZED")


if __name__ == "__main__":
    unittest.main()
