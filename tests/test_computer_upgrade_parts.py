"""P82/P07/P124 falsifiers for on-demand human-first computer upgrade purchases."""
import asyncio
import tempfile
import unittest
from pathlib import Path

from betterinstincts.computer_upgrade_parts import (
    enqueue_computer_menu_step, menu_catalog, plan_computer_purchase,
    propose_computer_purchase_step,
)
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.upgrade_parts_force import UpgradePartsForceError
from betterinstincts.workflow_interop import CooperativeScreenQueue


def ready(**changes):
    kwargs = dict(
        part_id="kitchen_upgrade_parts", stage="MENU", explicit_command=True,
        paused_verified=True, active_sim_observed=True, computer_observed=True,
        inside_lot_verified=True, human_active_or_unknown=False,
        native_capability_verified=True,
        menu_labels=["More Choices...", "Order", "Purchase Upgrade Parts"],
    )
    kwargs.update(changes)
    return propose_computer_purchase_step(**kwargs)


class ComputerMenuTests(unittest.TestCase):
    def test_five_operator_reported_items_separate_from_diy_kit(self):
        result = menu_catalog()
        self.assertEqual(result["part_ids"], [
            "common_upgrade_parts", "electronic_upgrade_parts",
            "kitchen_upgrade_parts", "plumbing_upgrade_parts",
            "robot_salvage_parts",
        ])
        self.assertEqual(len(result["parts"]), 5)
        self.assertFalse(result["execute_allowed"])

    def test_command_is_passive_and_never_authorizes_boot_input(self):
        result = plan_computer_purchase("plumbing_upgrade_parts", 3)
        self.assertFalse(result["execute_allowed"])
        self.assertEqual(result["boot_action"], "PASSIVE_NO_FOCUS_OR_INPUT")
        self.assertIn("OS_BLUETOOTH_SERVICE_MUTATION", result["forbidden"])
        with self.assertRaisesRegex(UpgradePartsForceError, "PART_NOT_IN_OBSERVED_COMPUTER_MENU"):
            plan_computer_purchase("computer_chip")

    def test_unknown_or_active_human_yields_without_effect(self):
        self.assertEqual(ready(human_active_or_unknown=True)["state"], "YIELD_TO_PLAYER")
        self.assertEqual(ready(human_active_or_unknown=None)["state"], "YIELD_TO_PLAYER")
        self.assertEqual(ready(explicit_command=False)["reason"], "EXPLICIT_USER_COMMAND_REQUIRED")
        self.assertEqual(ready(explicit_command="yes")["reason"], "EXPLICIT_USER_COMMAND_REQUIRED")

    def test_no_side_effect_without_live_pause_lot_computer_or_channel(self):
        self.assertEqual(ready(game_mode="BUILD")["reason"], "PAUSED_LIVE_MODE_REQUIRED")
        self.assertEqual(ready(paused_verified=False)["reason"], "PAUSED_LIVE_MODE_REQUIRED")
        self.assertEqual(ready(computer_observed=False)["reason"],
                         "FRESH_INSIDE_LOT_SIM_COMPUTER_EVIDENCE_REQUIRED")
        self.assertEqual(ready(inside_lot_verified=False)["state"], "WAIT")
        self.assertEqual(ready(active_sim_observed=False)["state"], "WAIT")
        self.assertEqual(
            ready(native_capability_verified=False, desktop_fallback_opt_in=False)["state"], "WAIT")

    def test_explicit_desktop_fallback_is_still_only_a_queue_proposal(self):
        decision = ready(native_capability_verified=False, desktop_fallback_opt_in=True)
        self.assertEqual(decision["state"], "READY_TO_QUEUE")
        self.assertFalse(decision["execute_allowed"])

    def test_dynamic_menu_prefers_visible_target_to_order_and_more_choices(self):
        self.assertEqual(ready()["action"]["label"], "Purchase Upgrade Parts")
        self.assertEqual(
            ready(menu_labels=["Order", "More Choices..."])["action"]["label"], "Order")
        self.assertEqual(
            ready(menu_labels=["More Choices..."])["action"]["label"], "More Choices...")
        self.assertEqual(
            ready(menu_labels=["More Choices..."],
                  visited_labels=["More Choices..."])["state"], "READY_TO_QUEUE")
        self.assertEqual(
            ready(menu_labels=["Some mystery action"])["reason"], "NO_RECOGNIZED_OBSERVED_MENU_BRANCH")

    def test_cycle_or_hop_limit_fails_closed(self):
        self.assertEqual(ready(page_signature_seen_before=True)["state"], "WAIT")
        self.assertEqual(ready(menu_pages_seen=16)["state"], "WAIT")
        self.assertEqual(ready(menu_pages_seen=-1)["state"], "READY_TO_QUEUE")

    def test_part_picker_never_guesses_a_row(self):
        self.assertEqual(
            ready(stage="PART_PICKER", menu_labels=["Plumbing Upgrade Parts"])["state"], "WAIT")
        action = ready(stage="PART_PICKER", menu_labels=["Kitchen Upgrade Parts"])["action"]
        self.assertEqual(action["kind"], "SELECT_VISIBLE_LABEL")
        self.assertEqual(action["label"], "Kitchen Upgrade Parts")

    def test_funds_and_spend_approval_required_before_single_purchase(self):
        fields = dict(stage="CONFIRM", menu_labels=["Buy"], unit_price_observed=10,
                      funds_observed=100, approved_spend_cap=25, inventory_before=2)
        self.assertEqual(ready(**fields)["reason"], "PURCHASE_SPENDING_AUTHORIZATION_REQUIRED")
        self.assertEqual(ready(**fields, spending_authorized=True)["state"], "READY_TO_QUEUE")
        self.assertEqual(
            ready(**fields, spending_authorized=True, approved_spend_cap=5)["state"], "WAIT")
        self.assertEqual(
            ready(**fields, spending_authorized=True, inventory_before=None)["state"], "WAIT")
        self.assertEqual(
            ready(**fields, spending_authorized=True, menu_labels=["Cancel"])["state"], "WAIT")

    def test_outcome_requires_observed_inventory_increase_no_auto_retry(self):
        self.assertEqual(
            ready(stage="VERIFY", inventory_before=2, inventory_after=2)["state"],
            "NEEDS_RECONCILIATION",
        )
        observed = ready(stage="VERIFY", inventory_before=2, inventory_after=3)
        self.assertEqual(observed["state"], "ONE_PURCHASE_OBSERVED")
        self.assertIsNone(observed["action"])

    def test_unknown_state_or_out_of_menu_item_denied(self):
        with self.assertRaisesRegex(UpgradePartsForceError, "UNKNOWN_COMPUTER_MENU_STAGE"):
            ready(stage="BLUETOOTH_SERVICE")
        with self.assertRaisesRegex(UpgradePartsForceError, "PART_NOT_IN_OBSERVED_COMPUTER_MENU"):
            ready(part_id="mechanism")


class CooperativeDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.age = 0
        self.events = []
        async def fake_sleep(_):
            pass
        self.queue = CooperativeScreenQueue(
            lambda: PresenceProbe(False, False, last_input_age_ms=self.age),
            lambda: True, lock_root=Path(self.tmp.name), sleep=fake_sleep,
        )

    async def test_human_reclaim_then_idle_fresh_validator_and_one_effect(self):
        async def validate():
            self.events.append("fresh_scene")
            return True
        async def effect(action):
            self.events.append("game_ui:" + action["label"])
        enqueue_computer_menu_step(
            self.queue, work_id="menu_first", decision=ready(),
            validate_fresh_scene=validate, perform_game_ui_effect=effect,
        )
        self.assertEqual((await self.queue.run_once())["state"], "WAITING_FOR_USER")
        self.assertEqual(self.events, [])
        self.age = 16000
        self.assertEqual((await self.queue.run_once())["state"], "COMPLETED")
        self.assertEqual(self.events, ["fresh_scene", "game_ui:Purchase Upgrade Parts"])
        self.assertEqual(len(self.queue.completed), 1)

    async def test_changed_scene_suspends_and_does_not_click(self):
        async def validate():
            return False
        async def effect(action):
            self.fail("must never execute on invalid scene")
        self.age = 16000
        enqueue_computer_menu_step(
            self.queue, work_id="stale_menu", decision=ready(),
            validate_fresh_scene=validate, perform_game_ui_effect=effect,
        )
        self.assertEqual((await self.queue.run_once())["state"], "NEEDS_REVALIDATION")
        self.assertIn("stale_menu", self.queue.needs_review)

    async def test_denied_proposal_cannot_enter_queue(self):
        async def validate():
            return True
        async def effect(action):
            self.fail("denied")
        with self.assertRaisesRegex(UpgradePartsForceError, "COMPUTER_STEP_NOT_READY"):
            enqueue_computer_menu_step(
                self.queue, work_id="denied", decision=ready(human_active_or_unknown=True),
                validate_fresh_scene=validate, perform_game_ui_effect=effect,
            )
        with self.assertRaisesRegex(UpgradePartsForceError, "GAME_UI_EFFECT_NOT_WHITELISTED"):
            enqueue_computer_menu_step(
                self.queue, work_id="malicious",
                decision={"state": "READY_TO_QUEUE",
                          "action": {"kind": "STOP_BLUETOOTH_SERVICE"}},
                validate_fresh_scene=validate, perform_game_ui_effect=effect,
            )


if __name__ == "__main__":
    unittest.main()
