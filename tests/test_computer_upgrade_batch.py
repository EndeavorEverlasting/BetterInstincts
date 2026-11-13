"""Deterministic five-row picker batch and player-first negative tests."""
import unittest

from betterinstincts.computer_upgrade_parts import (
    menu_catalog, plan_computer_purchase_batch, plan_computer_restock_batch,
    propose_computer_batch_step, verify_computer_batch_purchase,
)
from betterinstincts.upgrade_parts_force import UpgradePartsForceError


IDS = menu_catalog()["part_ids"]
PRICES = dict(zip(IDS, (10, 120, 90, 30, 5)))


def picker(counts=None, **changes):
    counts = counts or {}
    names = {p["id"]: p["display_name"] for p in menu_catalog()["parts"]}
    rows = [
        dict(part_id=pid, visible_label=names[pid].removesuffix("s"),
             unit_price=PRICES[pid], selected_count=counts.get(pid, 0),
             increment_visible=True, increment_hitbox_verified=True)
        for pid in IDS
    ]
    kwargs = dict(
        requests={"common_upgrade_parts": 2, "robot_salvage_parts": 1},
        picker_rows=rows, picker_revision="frame-1",
        observed_total_count=sum(counts.values()),
        observed_total_cost=sum(PRICES[k] * v for k, v in counts.items()),
        observed_funds=600569, approved_spend_cap=25,
        spending_authorized=True,
        inventory_before={pid: 0 for pid in IDS},
        buy_control_visible=True, buy_control_hitbox_verified=True,
        explicit_command=True, paused_verified=True,
        active_sim_observed=True, computer_observed=True,
        inside_lot_verified=True, human_active_or_unknown=False,
        native_capability_verified=True,
    )
    kwargs.update(changes)
    return propose_computer_batch_step(**kwargs)


class ComputerBatchPlannerTests(unittest.TestCase):
    def test_passive_intent_is_five_row_scoped(self):
        plan = plan_computer_purchase_batch({
            "common_upgrade_parts": 2, "robot_salvage_parts": 1,
        })
        self.assertEqual(plan["max_effects_per_decision"], 1)
        self.assertTrue(plan["reobserve_after_each_arrow"])
        self.assertFalse(plan["execute_allowed"])
        self.assertEqual(plan["part_order"], IDS)
        for invalid in ({}, {"mechanism": 1},
                        {"common_upgrade_parts": True},
                        {"common_upgrade_parts": 0},
                        {"common_upgrade_parts": 100}):
            with self.subTest(invalid=invalid), self.assertRaises(UpgradePartsForceError):
                plan_computer_purchase_batch(invalid)

    def test_restock_uses_observed_pocket_shortage_not_household_storage(self):
        result = plan_computer_restock_batch(
            stock_targets={"common_upgrade_parts": 20, "robot_salvage_parts": 10},
            pocket_counts={"common_upgrade_parts": 18, "robot_salvage_parts": 12},
        )
        self.assertEqual(result["quantities"], {"common_upgrade_parts": 2})
        self.assertEqual(result["inventory_baseline"]["common_upgrade_parts"], 18)
        self.assertEqual(plan_computer_restock_batch(
            stock_targets={"common_upgrade_parts": 20},
            pocket_counts={"common_upgrade_parts": 25},
        )["state"], "STOCK_TARGETS_ALREADY_MET")
        with self.assertRaisesRegex(UpgradePartsForceError, "PERSONAL_STOCK"):
            plan_computer_restock_batch(
                stock_targets={"common_upgrade_parts": 20}, pocket_counts={},
            )

    def test_one_arrow_per_new_picker_observation_then_one_buy(self):
        a = picker()
        self.assertEqual(a["state"], "READY_TO_QUEUE")
        self.assertEqual(a["action"]["kind"], "INCREMENT_OBSERVED_PART_ROW")
        self.assertEqual(a["action"]["label"], "common_upgrade_parts")
        self.assertEqual(a["action"]["expected_selected_count"], 0)
        self.assertFalse(a["execute_allowed"])

        b = picker({"common_upgrade_parts": 1}, picker_revision="frame-2",
                   last_acted_revision="frame-1")
        self.assertEqual(b["action"]["kind"], "INCREMENT_OBSERVED_PART_ROW")
        self.assertEqual(b["action"]["expected_selected_count"], 1)
        c = picker({"common_upgrade_parts": 2}, picker_revision="frame-3",
                   last_acted_revision="frame-2")
        self.assertEqual(c["action"]["label"], "robot_salvage_parts")
        d = picker({"common_upgrade_parts": 2, "robot_salvage_parts": 1},
                   picker_revision="frame-4", last_acted_revision="frame-3")
        self.assertEqual(d["action"]["kind"], "CONFIRM_OBSERVED_PURCHASE")
        self.assertEqual(d["action"]["expected_total_count"], 3)
        self.assertEqual(d["action"]["expected_total_cost"], 25)
        self.assertFalse(d["execute_allowed"])

    def test_all_five_parts_can_be_planned_with_fresh_observed_prices(self):
        req = {pid: 1 for pid in IDS}
        obs = picker(requests=req, approved_spend_cap=255)
        self.assertEqual(obs["action"]["label"], IDS[0])
        all_selected = picker(
            requests=req, approved_spend_cap=255,
            observed_total_count=5, observed_total_cost=255,
            picker_rows=[{**r, "selected_count": 1} for r in picker_rows()],
        )
        self.assertEqual(all_selected["action"]["kind"], "CONFIRM_OBSERVED_PURCHASE")

    def test_fail_closed_for_player_and_untrusted_session(self):
        for kwargs, reason in (
            ({"human_active_or_unknown": True}, "PLAYER_CONTROL_TAKES_PRIORITY"),
            ({"human_active_or_unknown": None}, "PLAYER_CONTROL_TAKES_PRIORITY"),
            ({"explicit_command": False}, "EXPLICIT_USER_COMMAND_REQUIRED"),
            ({"paused_verified": False}, "PAUSED_LIVE_MODE_REQUIRED"),
            ({"game_mode": "BUILD"}, "PAUSED_LIVE_MODE_REQUIRED"),
            ({"inside_lot_verified": False},
             "FRESH_INSIDE_LOT_SIM_COMPUTER_EVIDENCE_REQUIRED"),
            ({"native_capability_verified": False},
             "VERIFIED_NATIVE_CHANNEL_OR_EXPLICIT_DESKTOP_OPT_IN_REQUIRED"),
        ):
            with self.subTest(kwargs=kwargs):
                result = picker(**kwargs)
                self.assertEqual(result["action"], None)
                self.assertEqual(result["reason"], reason)

    def test_no_spend_or_price_without_exact_receipts(self):
        for kwargs, reason in (
            ({"spending_authorized": False}, "PURCHASE_SPENDING_AUTHORIZATION_REQUIRED"),
            ({"approved_spend_cap": 24}, "BATCH_EXCEEDS_FUNDS_OR_APPROVED_SPENDING_CAP"),
            ({"observed_funds": 24}, "BATCH_EXCEEDS_FUNDS_OR_APPROVED_SPENDING_CAP"),
            ({"observed_total_count": 1}, "PICKER_TOTALS_DO_NOT_RECONCILE"),
            ({"observed_total_cost": 1}, "PICKER_TOTALS_DO_NOT_RECONCILE"),
            ({"picker_revision": ""}, "FRESH_PICKER_REVISION_REQUIRED"),
            ({"picker_revision": "stale", "last_acted_revision": "stale"},
             "FRESH_PICKER_REVISION_REQUIRED"),
        ):
            with self.subTest(kwargs=kwargs):
                result = picker(**kwargs)
                self.assertEqual(result["action"], None)
                self.assertEqual(result["reason"], reason)

    def test_rows_and_buy_control_must_be_fresh(self):
        base = picker_rows()
        for rows, reason in (
            (base[:-1], "FIVE_OBSERVED_PICKER_ROWS_REQUIRED"),
            (base[:-1] + [base[0]], "INVALID_OR_DUPLICATE_PICKER_PART"),
            ([{**base[0], "visible_label": "Different"}] + base[1:],
             "OBSERVED_PART_ROW_LABEL_MISMATCH"),
            ([{**base[0], "unit_price": True}] + base[1:],
             "FRESH_PICKER_COUNT_AND_PRICE_REQUIRED"),
            ([{**base[0], "increment_hitbox_verified": False}] + base[1:],
             "INCREMENT_CONTROL_NOT_FRESHLY_VERIFIED"),
        ):
            with self.subTest(reason=reason):
                self.assertEqual(picker(picker_rows=rows)["reason"], reason)
        fully_selected = {"common_upgrade_parts": 2, "robot_salvage_parts": 1}
        self.assertEqual(picker(
            fully_selected, buy_control_hitbox_verified=False)["reason"],
            "BUY_CONTROL_NOT_FRESHLY_VERIFIED")
        self.assertEqual(picker(fully_selected, inventory_before={})["reason"],
                         "FIVE_PART_PERSONAL_INVENTORY_BASELINE_REQUIRED")

    def test_existing_manual_selection_never_expands_spending_authority(self):
        over = picker({"common_upgrade_parts": 3, "robot_salvage_parts": 1},
                      approved_spend_cap=200)
        self.assertEqual(over["reason"], "PICKER_SELECTION_EXCEEDS_AUTHORIZED_BATCH")
        unrequested = picker({"kitchen_upgrade_parts": 1},
                             approved_spend_cap=200)
        self.assertEqual(unrequested["reason"],
                         "PICKER_SELECTION_EXCEEDS_AUTHORIZED_BATCH")

    def test_exact_pocket_and_simoleon_readback_or_no_retry(self):
        before = {pid: 8 for pid in IDS}
        after = dict(before, common_upgrade_parts=10, robot_salvage_parts=9)
        kwargs = dict(requests={"common_upgrade_parts": 2, "robot_salvage_parts": 1},
                      inventory_before=before, inventory_after=after,
                      funds_before=100, funds_after=75, expected_total_cost=25)
        good = verify_computer_batch_purchase(**kwargs)
        self.assertEqual(good["state"], "BATCH_PURCHASE_OBSERVED")
        self.assertFalse(good["execute_allowed"])
        for changes in (
            {"funds_after": 74}, {"inventory_after": before},
            {"inventory_after": dict(after, kitchen_upgrade_parts=9)},
            {"inventory_before": {}}, {"funds_before": None},
        ):
            with self.subTest(changes=changes):
                self.assertEqual(
                    verify_computer_batch_purchase(**{**kwargs, **changes})["state"],
                    "NEEDS_RECONCILIATION",
                )


def picker_rows():
    names = {p["id"]: p["display_name"] for p in menu_catalog()["parts"]}
    return [
        dict(part_id=pid, visible_label=names[pid].removesuffix("s"),
             unit_price=PRICES[pid], selected_count=0,
             increment_visible=True, increment_hitbox_verified=True)
        for pid in IDS
    ]


if __name__ == "__main__":
    unittest.main()
