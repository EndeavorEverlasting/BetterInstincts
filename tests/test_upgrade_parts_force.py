import json
import tempfile
import unittest
from pathlib import Path

from betterinstincts.upgrade_parts_force import (
    UpgradePartsForceError,
    acquisition_source_catalog,
    next_observed_menu_choice,
    plan_acquisition_routes,
    plan_computer_order_domain,
    budget_snapshot,
    catalog_snapshot,
    evaluate_diy_parts_cert,
    how_to_buy,
    load_contract,
    plan_household_parts_budget,
    plan_parts_force,
    record_part_observation,
    resolve_part,
    status_cert,
    steps_to_operator_checklist,
)


class UpgradePartsForceTests(unittest.TestCase):
    def test_contract_household_budget_architecture(self):
        cfg = load_contract()
        self.assertEqual(cfg["architecture"]["selected"], "HOUSEHOLD_DIY_PARTS_BUDGET")
        self.assertEqual(cfg["version"], 3)
        self.assertEqual(cfg["household_budget"]["selected"], "PER_SIM_POCKET_STOCK")
        self.assertEqual(cfg["household_budget"]["preferred_acquisition_order"][0], "spawn")
        self.assertIn("phone", cfg["paths"])
        self.assertEqual(len(cfg["computer_purchase_menu"]["part_ids"]), 5)
        self.assertEqual(cfg["paths"]["computer"]["steps_template"][6]["op"], "DISCOVER_NESTED_MENU")
        self.assertIn("gsi_create_obj", cfg["forbidden"])
        self.assertTrue(cfg["offline_install"]["forbid_ea_online_connect"])
        self.assertEqual(cfg["offline_install"]["connection_required_dialog"], "STAY_OFFLINE_ONLY")
        for needle in ("ea_online_connect", "CONNECT_BUTTON", "CONNECT_ONLINE", "force_sims_online"):
            self.assertIn(needle, cfg["forbidden"])

    def test_phone_plan_never_presses_connect(self):
        plan = plan_parts_force(part_id="kitchen_upgrade_parts", path="phone", quantity=2)
        blob = json.dumps(plan).lower()
        self.assertIn("stay offline", blob)
        self.assertNotIn('"choice": "connect"', blob)
        self.assertEqual(plan["offline_install"]["forbid_ea_online_connect"], True)
        ops = [s.get("op") for s in plan["steps"]]
        self.assertIn("IF_CONNECTION_REQUIRED", ops)

    def test_catalog_diy_kit_covers_core_parts(self):
        snap = catalog_snapshot()
        ids = set(snap["diy_kit_part_ids"])
        for required in (
            "common_upgrade_parts",
            "electronic_upgrade_parts",
            "plumbing_upgrade_parts",
            "kitchen_upgrade_parts",
            "robot_salvage_parts",
            "computer_chip",
            "mechanism",
        ):
            self.assertIn(required, ids)
        self.assertFalse(snap["execute_allowed"])

    def test_budget_snapshot_pocket_destination(self):
        snap = budget_snapshot()
        self.assertEqual(snap["destination"], "sim_pocket_inventory")
        self.assertGreaterEqual(len(snap["parts"]), 7)
        self.assertTrue(all(p["destination"] == "sim_pocket_inventory" for p in snap["parts"]))

    def test_how_to_buy_names_order_path(self):
        guide = how_to_buy("robot_salvage_parts")
        blob = " ".join(guide["steps"]) + " " + str(guide["summary"])
        self.assertIn("Purchase Upgrade Parts", blob)
        self.assertIn("Order", blob)

    def test_synonym_resolves_electronics(self):
        part = resolve_part("electronics")
        self.assertEqual(part["id"], "electronic_upgrade_parts")

    def test_spawn_is_default_for_robot_salvage(self):
        plan = plan_parts_force(part_id="robot_salvage_parts", quantity=20)
        self.assertEqual(plan["path"], "spawn")
        self.assertTrue(plan["requires_testingcheats"])

    def test_phone_path_plan(self):
        plan = plan_parts_force(part_id="kitchen_upgrade_parts", path="phone", quantity=5)
        self.assertEqual(plan["path"], "phone")
        ops = [s["op"] for s in plan["steps"]]
        self.assertIn("OPEN_PHONE", ops)
        self.assertIn("REPEAT_PURCHASE", ops)

    def test_buy_mode_rejected(self):
        with self.assertRaises(UpgradePartsForceError) as ctx:
            plan_parts_force(path="buy_mode")
        self.assertIn("BUY_MODE_NOT_PREFERRED_ACQUISITION", str(ctx.exception))

    def test_household_plan_for_n_members(self):
        plan = plan_household_parts_budget(members=4, path="spawn")
        self.assertEqual(plan["state"], "HOUSEHOLD_DIY_PARTS_BUDGET_PLAN_READY")
        self.assertEqual(plan["household_members"], 4)
        self.assertEqual(len(plan["member_plans"]), 4)
        self.assertEqual(plan["destination"], "sim_pocket_inventory")
        self.assertFalse(plan["execute_allowed"])
        chords = [s for s in plan["steps"] if s.get("op") == "KEY"]
        self.assertEqual(len(chords), 3)  # Space between 4 members
        self.assertIn("robot_salvage_parts", plan["diy_kit_part_ids"])

    def test_household_invalid_n_fails(self):
        with self.assertRaises(UpgradePartsForceError):
            plan_household_parts_budget(members=0)
        with self.assertRaises(UpgradePartsForceError):
            plan_household_parts_budget(members=101)

    def test_cert_all_met_review_required(self):
        kit = catalog_snapshot()["diy_kit_part_ids"]
        observations = []
        for slot in range(2):
            observations.append(
                {
                    "member_slot": slot,
                    "parts": {pid: 20 for pid in kit},
                }
            )
        cert = evaluate_diy_parts_cert(members=2, observations=observations)
        self.assertEqual(cert["aggregate_state"], "ALL_MEMBERS_MET_REVIEW_REQUIRED")
        self.assertFalse(cert["certified"])
        self.assertEqual(cert["members_met"], 2)

    def test_cert_unknown_without_counts(self):
        observations = [{"member_slot": 0, "parts": {}}, {"member_slot": 1, "parts": {}}]
        cert = evaluate_diy_parts_cert(members=2, observations=observations)
        self.assertEqual(cert["aggregate_state"], "UNPROVEN")
        self.assertTrue(all(p["state"] == "UNKNOWN" for m in cert["members"] for p in m["parts"]))

    def test_cert_partial_short(self):
        kit = catalog_snapshot()["diy_kit_part_ids"]
        parts = {pid: 20 for pid in kit}
        parts["robot_salvage_parts"] = 2
        cert = evaluate_diy_parts_cert(
            members=1,
            observations=[{"member_slot": 0, "parts": parts}],
        )
        self.assertEqual(cert["aggregate_state"], "PARTIAL")
        salvage = next(p for p in cert["members"][0]["parts"] if p["part_id"] == "robot_salvage_parts")
        self.assertEqual(salvage["state"], "SHORT")

    def test_record_and_status_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kit = catalog_snapshot()["diy_kit_part_ids"]
            cert = None
            for pid in kit:
                cert = record_part_observation(
                    run_id="lab-n2",
                    member_slot=0,
                    part_id=pid,
                    observed_count=50,
                    members=2,
                    root=root,
                )
                record_part_observation(
                    run_id="lab-n2",
                    member_slot=1,
                    part_id=pid,
                    observed_count=50,
                    members=2,
                    root=root,
                )
            self.assertIsNotNone(cert)
            status = status_cert("lab-n2", root=root)
            self.assertEqual(status["aggregate_state"], "ALL_MEMBERS_MET_REVIEW_REQUIRED")
            self.assertEqual(status["household_members"], 2)

    def test_player_directed_yields(self):
        plan = plan_household_parts_budget(members=3, player_directed=True)
        self.assertEqual(plan["state"], "YIELD_TO_PLAYER")

    def test_checklist_mentions_space_traverse(self):
        plan = plan_household_parts_budget(members=3, path="spawn")
        lines = steps_to_operator_checklist(plan)
        blob = " | ".join(lines)
        self.assertIn("SPACE", blob)
        self.assertIn("Spawn Crafting Supplies", blob)

    def test_catalog_sources_separate_instant_eco_and_biofuel(self):
        catalog = acquisition_source_catalog()
        sources = catalog["route_catalog"]
        self.assertEqual(sources["common_upgrade_parts"]["source"], "computer_order")
        self.assertEqual(sources["eco_upgrade_parts"]["source"], "eco_fabricator")
        self.assertEqual(sources["eco_upgrade_parts"]["requirements"]["bits_per_attempt"], 15)
        self.assertEqual(sources["eco_upgrade_parts"]["requirements"]["pieces_per_attempt"], 10)
        self.assertEqual(sources["generator_fuel"]["source"], "recycler_generator")
        self.assertEqual(sources["insect_biofuel_filled_can"]["source"], "insect_farm")
        self.assertNotEqual(sources["generator_fuel"]["action_effect"],
                            sources["insect_biofuel_filled_can"]["action_effect"])
        self.assertFalse(catalog["execute_allowed"])

    def test_menu_first_visible_choice_zero_more_choices(self):
        decision = next_observed_menu_choice(
            visible_options=["Browse Web", "Order", "More Choices..."],
            desired_choice="Order",
        )
        self.assertEqual(decision["state"], "CHOICE_OBSERVED")
        self.assertEqual(decision["choice"], "Order")
        self.assertEqual(decision["page_depth"], 0)

    def test_menu_paginates_two_pages_observationally(self):
        seen = []
        for options in (["Browse Web", "More Choices"],
                        ["Play Game", "More Choices..."]):
            decision = next_observed_menu_choice(
                visible_options=options, desired_choice="Purchase Upgrade Parts", visited_signatures=seen)
            self.assertEqual(decision["state"], "MORE_CHOICES_OBSERVED")
            seen = decision["next_history"]
        goal = next_observed_menu_choice(
            visible_options=["Purchase Upgrade Parts...", "More Choices"],
            desired_choice="Purchase Upgrade Parts", visited_signatures=seen)
        self.assertEqual(goal["state"], "CHOICE_OBSERVED")
        self.assertEqual(goal["page_depth"], 2)

    def test_menu_stops_on_cycle_missing_more_ambiguous_and_depth(self):
        first = next_observed_menu_choice(visible_options=["Browse", "More Choices"], desired_choice="Order")
        self.assertEqual(next_observed_menu_choice(
            visible_options=["Browse", "More Choices"], desired_choice="Order",
            visited_signatures=first["next_history"])["reason"], "MENU_LOOP_DETECTED")
        self.assertEqual(next_observed_menu_choice(
            visible_options=["Browse"], desired_choice="Order")["reason"],
            "TARGET_NOT_IN_OBSERVED_MENU")
        self.assertEqual(next_observed_menu_choice(
            visible_options=["Order", "Order"], desired_choice="Order")["reason"],
            "DUPLICATE_VISIBLE_TARGET")
        self.assertEqual(next_observed_menu_choice(
            visible_options=["Browse", "More Choices"], desired_choice="Order",
            visited_signatures=[str(i) for i in range(load_contract()["computer_purchase_menu"]["max_menu_pages"])])["reason"], "MENU_PAGE_LIMIT_OR_AMBIGUITY")
        self.assertEqual(next_observed_menu_choice(
            visible_options=[], desired_choice="Order")["reason"], "MENU_OPTIONS_NOT_OBSERVED")

    def test_no_hardcoded_household_and_actor_selection(self):
        portraits = [
            {"slot": 4, "portrait_id": "observed:alpha", "observed": True},
            {"slot": 1, "portrait_id": "observed:beta", "observed": True},
            {"slot": 8, "portrait_id": "observed:gamma", "observed": True},
        ]
        plan = plan_acquisition_routes(
            portraits=portraits, selected_slots=[8, 1],
            requests=[{"item": "Robot Salvage Parts", "quantity": 2},
                      {"item": "Electronic Upgrade Parts", "quantity": 3}],
            packs_observed=["Discover University"],
        )
        self.assertEqual(plan["portraits_observed"], 3)
        self.assertEqual(plan["portraits_selected"], ["observed:beta", "observed:gamma"])
        opens = [s for s in plan["steps"] if s["op"] == "LEFT_CLICK_OBSERVED_COMPUTER"]
        self.assertEqual(len(opens), 2)  # once per chosen actor, NOT once per item
        self.assertTrue(all(s["requires_sim_at_computer"] is False for s in opens))
        self.assertEqual(len([s for s in plan["steps"] if s["op"] == "CONFIRM_PURCHASE_WITH_FRESH_ADMISSION"]), 4)
        self.assertTrue(all(not x["is_instant_proved"] for x in plan["action_classification"]))
        self.assertFalse(plan["execute_allowed"])
        self.assertNotIn("Charlee", json.dumps(plan))
        self.assertNotIn('"xy":', json.dumps(plan))

    def test_eco_and_fuels_never_route_through_purchase_upgrade_parts(self):
        plan = plan_acquisition_routes(
            portraits=[{"slot": 0, "portrait_id": "sim:0", "observed": True}],
            requests=[{"item": "Eco-Upgrade Parts", "quantity": 1},
                      {"item": "fuel", "quantity": 1},
                      {"item": "Insect Biofuel-Filled Can", "quantity": 1}],
            packs_observed=["Eco Lifestyle"],
        )
        ops = [s["op"] for s in plan["steps"]]
        self.assertIn("OBSERVE_HOUSEHOLD_BITS_PIECES", ops)
        self.assertIn("REQUIRE_FARM_READY_AND_HEALTHY", ops)
        self.assertIn("OBSERVE_GENERATOR_REFILL_AFFORDANCE", ops)
        self.assertNotIn("LEFT_CLICK_OBSERVED_COMPUTER", ops)
        self.assertNotIn("CONFIRM_PURCHASE_WITH_FRESH_ADMISSION", ops)
        self.assertTrue(all(not x["is_instant_proved"] for x in plan["action_classification"]))

    def test_pack_and_roster_fail_closed(self):
        profiles = [{"slot": 0, "portrait_id": "screen:0", "observed": True}]
        with self.assertRaisesRegex(UpgradePartsForceError, "PACK_NOT_OBSERVED"):
            plan_acquisition_routes(portraits=profiles, requests=[{"item": "eco parts"}],
                                    packs_observed=["base"])
        with self.assertRaisesRegex(UpgradePartsForceError, "SELECTED_PORTRAIT_NOT_OBSERVED"):
            plan_acquisition_routes(portraits=profiles, requests=[{"item": "common parts"}],
                                    selected_slots=[1])
        with self.assertRaisesRegex(UpgradePartsForceError, "PORTRAIT_NOT_ATTESTED"):
            plan_acquisition_routes(
                portraits=[{"slot": 0, "portrait_id": "screen:0", "observed": False}],
                requests=[{"item": "common parts"}])
        with self.assertRaisesRegex(UpgradePartsForceError, "DUPLICATE_PORTRAIT"):
            plan_acquisition_routes(
                portraits=profiles + profiles, requests=[{"item": "common parts"}])
        with self.assertRaisesRegex(UpgradePartsForceError, "UNKNOWN_ACQUISITION_ITEM"):
            plan_acquisition_routes(portraits=profiles, requests=[{"item": "unseen titanium coolant"}])

    def test_generic_order_domain_is_not_hardcoded_to_upgrade_parts(self):
        portraits = [
            {"slot": 7, "portrait_id": "scanned:7", "observed": True},
            {"slot": 2, "portrait_id": "scanned:2", "observed": True},
        ]
        plan = plan_computer_order_domain(
            portraits=portraits, selected_slots=[7],
            domain="Order Books", item_labels=["Observed Book A", "Observed Book B"],
        )
        self.assertEqual(plan["domain_goal"], "Order Books")
        self.assertEqual(plan["portraits_selected"], ["scanned:7"])
        self.assertEqual([s["choice"] for s in plan["steps"]
                          if s["op"] == "FIND_VISIBLE_CHOICE_OR_BOUNDED_MORE_CHOICES"],
                         ["Order", "Order Books"])
        self.assertEqual(len([s for s in plan["steps"]
                              if s["op"] == "LEFT_CLICK_OBSERVED_COMPUTER"]), 1)
        self.assertEqual(len([s for s in plan["steps"]
                              if s["op"] == "REQUIRE_VISIBLE_PURCHASE_ITEM"]), 2)
        self.assertFalse(plan["execute_allowed"])
        self.assertEqual(plan["known_item_availability"], "NOT_PROVEN_UNTIL_VISIBLE")

    def test_generic_order_domain_blocks_unspecific_or_unobserved_roster(self):
        p = [{"slot": 0, "portrait_id": "screen:0", "observed": True}]
        with self.assertRaisesRegex(UpgradePartsForceError, "SPECIFIC_ORDER_DOMAIN_REQUIRED"):
            plan_computer_order_domain(portraits=p, domain="Order", item_labels=["upgrade parts"])
        with self.assertRaisesRegex(UpgradePartsForceError, "ORDER_ITEMS_REQUIRED"):
            plan_computer_order_domain(portraits=p, domain="Books", item_labels=[])
        with self.assertRaisesRegex(UpgradePartsForceError, "SELECTED_PORTRAIT_NOT_OBSERVED"):
            plan_computer_order_domain(
                portraits=p, domain="Books", item_labels=["book"], selected_slots=[9])

    def test_player_override_refuses_all_acquisition_steps(self):
        plan = plan_acquisition_routes(
            portraits=[], requests=[], player_directed=True)
        self.assertEqual(plan["state"], "YIELD_TO_PLAYER")
        self.assertEqual(plan["steps"], [])

    def test_legacy_computer_path_preserves_PR163_observed_dispatch(self):
        plan = plan_parts_force(part_id="common_upgrade_parts", path="computer", quantity=2)
        ops = [step["op"] for step in plan["steps"]]
        self.assertIn("DISCOVER_NESTED_MENU", ops)
        self.assertFalse(plan["execute_allowed"])
        self.assertEqual(load_contract()["version"], 3)

    def test_cli_script_compiles(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "upgrade_parts_force.py"
        compile(script.read_text(encoding="utf-8"), str(script), "exec")

    def test_contract_json_roundtrip(self):
        raw = json.loads(
            (Path(__file__).resolve().parents[1] / "contracts" / "upgrade-parts-force.v1.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(raw["schema"], "betterinstincts.upgrade-parts-force/v1")
        self.assertEqual(raw["architecture"]["selected"], "HOUSEHOLD_DIY_PARTS_BUDGET")


if __name__ == "__main__":
    unittest.main()
