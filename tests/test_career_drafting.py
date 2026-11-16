import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts import house_state
from betterinstincts.career_drafting import SCOPE
from betterinstincts.career_service import evaluate_eco_invention_drafting
from betterinstincts.host_listener import activate, tick
from betterinstincts.host_stack import evaluate_turn
from betterinstincts.player_presence import PresenceProbe
from tests.test_lot_mutation_preservation import observed_two_story_lot
from tests.test_ui_mode import NEEDS, VERSION, idle, observation

CAPTURE = "capture:fresh"
NOW = 3000
COMMANDS = ["testingcheats true", "bb.ignoregameplayunlocksentitlement", "bb.showhiddenobjects"]
TABLET = "ELECTRONIC_DRAFTING_TABLET"


def obs(**fields):
    return {
        "schema": "betterinstincts.career-drafting/v1",
        "capture_ref": CAPTURE, "game_build": VERSION, "session_ref": "drafting",
        "save_ref": "save:lab", "sim_ref": "sim:test", "household_ref": "household:test",
        "lot_ref": "lot.current", "objective_ref": "objective:one",
        "mode": "LIVE", "observed_at_unix": NOW, "scene_verified": True,
        "queue_verified": True, "player_directed": False, "lab_save_verified": True,
        "eco_lifestyle": True, "effect_pending": False, "draft_already_queued": False,
        "career_track": "GREEN_TECHNICIAN", "objective": "DRAFT_ECO_INVENTION_CONCEPT",
        "objective_status": "PENDING",
        **fields,
    }


def scoped(row, **fields):
    return {**{key: row[key] for key in (*SCOPE, "lot_ref", "capture_ref")}, **fields}


def scanned(row, **fields):
    args = {
        "panel_state": "OPEN", "panel_id": "personal_inventory",
        "layout_revision": "layout:one", "scan_ref": "scan:one", "unfiltered": True,
        "page_refs": ["page:one"], "current_page_ref": "page:one", "no_gaps_verified": True,
        "started_at_top": True, "at_bottom": True,
    }
    return scoped(row, **{**args, **fields})


def evaluate(row, **kwargs):
    return evaluate_eco_invention_drafting(
        row, capture_ref=row["capture_ref"], mode=row["mode"], now=NOW, **kwargs
    )


def build_observation(**fields):
    live = obs(**fields)
    live["inventory"] = scanned(live)
    live["owned_search"] = scoped(live, current_lot_status="VERIFIED_ABSENT",
                                  household_inventory_status="VERIFIED_ABSENT",
                                  last_known_location_reviewed=True)
    live["replacement"] = scoped(live, owned_routes_exhausted=True, exhaustion_ref="proof:owned",
                                 catalog_recovery_enabled=True, purchase_attempted=False)
    proof = evaluate(live)
    row = {**live, "mode": "BUY", "capture_ref": "capture:build", "inventory": None}
    row["replacement"] = scoped(
        row, owned_routes_exhausted=True, exhaustion_ref="proof:owned",
        catalog_recovery_enabled=True, purchase_attempted=False, cheat_recovery_enabled=True,
        confirmed_commands=[], console_closed=False, cheat_sequence_started=True, live_search_receipt=proof,
    )
    return row


class DraftingTests(unittest.TestCase):
    def test_hotkey_and_bounded_calibrated_scroll(self):
        row = obs()
        row["inventory"] = scoped(row, panel_state="CLOSED", hud_clear=True)
        plan = evaluate(row)
        self.assertEqual(plan["gate"], "OPEN_PERSONAL_INVENTORY")
        self.assertEqual(plan["chord"], ["I"])
        self.assertFalse(plan["execute_allowed"])

        calibration = {
            "panel_id": "personal_inventory", "target_id": "personal_inventory.scroll_list",
            "hitbox": [1400, 660, 1850, 957], "x": 1625, "y": 808,
            "ui_layout_revision": "layout:one", "selected_sim_revision": "portrait:one",
        }
        current = {
            "capture_ref": CAPTURE, "panel_id": "personal_inventory",
            "panel_hitbox": calibration["hitbox"], "panel_visible": True,
            "panel_obscured": False, "panel_animation_stable": True, "target_enabled": True,
            "ui_layout_revision": "layout:one", "selected_sim_revision": "portrait:one",
            "panel_cues": [
                {"source": "visual", "token": "panel:live_personal_inventory"},
                {"source": "operator", "token": "personal_inventory_visible"},
            ],
        }
        inv = scanned(row, at_bottom=False, selected_sim_revision="portrait:one",
                      client_width=1919, client_height=1079, scroll_observation=current,
                      scroll_calibration=calibration)
        row["inventory"] = inv
        plan = evaluate(row)
        self.assertEqual(plan["gate"], "SCROLL_PERSONAL_INVENTORY")
        self.assertEqual(plan["cursor_client_xy"], [1625, 808])
        self.assertEqual(plan["direction"], "DOWN")
        inv["last_scroll_from_page_ref"] = "page:one"
        self.assertEqual(evaluate(row)["gate"], "RECONCILE_INVENTORY_SCROLL")
        inv.pop("last_scroll_from_page_ref")
        for patch_fields, gate in (
            ({"scroll_calibration": {**calibration, "y": 5}}, "CALIBRATE_INVENTORY_SCROLL_TARGET"),
            ({"scroll_observation": {**current, "selected_sim_revision": "portrait:two"}},
             "CALIBRATE_INVENTORY_SCROLL_TARGET"),
            ({"page_refs": ["page:one"] * 2}, "RECONCILE_INVENTORY_SCAN"),
            ({"page_refs": [f"page:{n}" for n in range(24)], "current_page_ref": "page:23"},
             "INVENTORY_SCAN_LIMIT_REACHED"),
            ({"at_bottom": True, "no_gaps_verified": False}, "RECONCILE_INVENTORY_SCAN"),
            ({"at_bottom": True}, "CHECK_CURRENT_LOT_AND_HOUSEHOLD_STORAGE"),
        ):
            with self.subTest(gate=gate):
                row["inventory"] = {**inv, **patch_fields}
                self.assertEqual(evaluate(row)["gate"], gate)

    def test_owned_tablet_exact_interaction_and_distinct_completion(self):
        row = obs()
        tablet = scoped(row, location="CURRENT_LOT", definition_id=TABLET,
                        object_ref="obj:tablet", pickup_available=True,
                        owned_by_household=True, on_lot_target_verified=True)
        row["tablet"] = tablet
        self.assertEqual(evaluate(row)["gate"], "PUT_TABLET_IN_PERSONAL_INVENTORY")
        tablet.update(location="PERSONAL_INVENTORY")
        self.assertEqual(evaluate(row)["gate"], "INSPECT_TABLET_INTERACTIONS")
        tablet["draft_interaction"] = scoped(
            row, object_ref="obj:tablet", enabled=True,
            label="Draft a Municipal Concept", interaction_ref="interaction:eco")
        self.assertEqual(evaluate(row)["gate"], "VERIFY_EXACT_ENABLED_DRAFT_INTERACTION")
        tablet["draft_interaction"]["label"] = "Draft Eco-Invention Concept"
        self.assertEqual(evaluate(row)["gate"], "DRAFT_ECO_INVENTION_CONCEPT")
        for fields, gate in (
            ({"effect_pending": True}, "RECONCILE_DRAFTING_EFFECT"),
            ({"draft_already_queued": True}, "VERIFY_NO_DUPLICATE_DRAFT"),
            ({"objective_status": "UNKNOWN"}, "VERIFY_DRAFT_OBJECTIVE_STATE"),
            ({"objective_status": "COMPLETE"}, "VERIFY_DRAFT_OBJECTIVE_STATE"),
            ({"objective_status": "COMPLETE", "completion": scoped(
                row, blueprint_ref="proof:blueprint", objective_progress_ref="proof:progress")},
             "DRAFT_OBJECTIVE_COMPLETE"),
            ({"objective": "FABRICATE_ECO_UPGRADE_PART"}, "NO_MATCHING_DRAFT_OBJECTIVE"),
            ({"player_directed": True}, "DRAFTING_PLAYER_FIRST"),
            ({"observed_at_unix": NOW - 31}, "REOBSERVE_DRAFTING_SCOPE"),
            ({"sim_ref": "sim:other"}, "VERIFY_TABLET_IDENTITY_AND_LOCATION"),
            ({"lab_save_verified": False}, "REOBSERVE_DRAFTING_SCOPE"),
        ):
            with self.subTest(gate=gate):
                self.assertEqual(evaluate({**row, **fields})["gate"], gate)

    def test_review_last_known_lot_before_replacement(self):
        row = obs()
        row["inventory"] = scanned(row)
        row["replacement"] = scoped(row, owned_routes_exhausted=True, exhaustion_ref="proof:owned",
                                   catalog_recovery_enabled=True, purchase_attempted=False)
        search = scoped(row, current_lot_status="VERIFIED_ABSENT", household_inventory_status="VERIFIED_ABSENT",
                        last_seen=scoped(row, lot_ref="lot.away", object_ref="obj:last", definition_id=TABLET))
        row["owned_search"] = search
        report = evaluate(row)
        self.assertEqual(report["gate"], "REVIEW_LAST_KNOWN_LOT_FOR_TABLET")
        self.assertEqual(report["lot_ref"], "lot.away")
        search["prior_lot_review"] = scoped(row, reviewed_lot_ref="lot.away",
                                            object_ref="obj:last", status="VERIFIED_ABSENT")
        self.assertEqual(evaluate(row)["gate"], "OPEN_BUILD_BUY_FOR_TABLET")
        search["prior_lot_review"]["reviewed_lot_ref"] = "lot.unrelated"
        self.assertEqual(evaluate(row)["gate"], "REVIEW_LAST_KNOWN_LOT_FOR_TABLET")

    def test_ordered_catalog_search_and_exact_zero_cost_placement(self):
        model, manifest = observed_two_story_lot()
        row = build_observation(lot_ref=model["lot_id"])
        recovery = row["replacement"]
        proof = recovery.pop("live_search_receipt")
        self.assertEqual(evaluate(row)["gate"], "VERIFY_PRIOR_LIVE_TABLET_SEARCH")
        recovery["live_search_receipt"] = proof
        recovery["console_closed"] = True
        ordinary_catalog = {**row, "replacement": {**recovery, "cheat_sequence_started": False}}
        self.assertEqual(evaluate(ordinary_catalog)["query"], "tablet")
        ordinary_catalog["replacement"].update(observed_query="tablet",
                                                tablet_locked_or_missing_verified=True)
        self.assertEqual(evaluate(ordinary_catalog)["gate"], "OPEN_TABLET_CHEAT_CONSOLE")
        ordinary_catalog["replacement"]["cheat_recovery_enabled"] = False
        self.assertEqual(evaluate(ordinary_catalog)["gate"], "CHEAT_RECOVERY_DISABLED")
        self.assertEqual(evaluate(row)["chord"], ["CTRL", "SHIFT", "C"])
        recovery["console_closed"] = False
        for offset, command in enumerate(COMMANDS):
            recovery["confirmed_commands"] = COMMANDS[:offset]
            result = evaluate(row)
            self.assertEqual(result["gate"], "ENTER_TABLET_UNLOCK_COMMAND")
            self.assertEqual((result["command"], result["submit_key"]), (command, "Enter"))
        recovery["confirmed_commands"] = [COMMANDS[1]]
        self.assertEqual(evaluate(row)["gate"], "RECONCILE_TABLET_CONSOLE")
        recovery["confirmed_commands"] = COMMANDS
        self.assertEqual(evaluate(row)["gate"], "CLOSE_TABLET_CHEAT_CONSOLE")
        recovery["console_closed"] = True
        self.assertEqual(evaluate(row)["query"], "tablet")
        recovery["observed_query"] = "tablet"
        listing = scoped(row, available=True, catalog_ref="catalog:tablet",
                         definition_id=TABLET, label="Slablet", price=0)
        recovery["listing"] = listing
        self.assertEqual(evaluate(row)["gate"], "VERIFY_EXACT_ZERO_COST_TABLET_LISTING")
        listing["label"] = "Electronic Drafting Tablet"
        recovery.update(placement_verified=True, placement_ref="place:table")
        self.assertEqual(evaluate(row, lot_model=model)["gate"], "VERIFY_WHOLE_LOT_BUILD_CHECKPOINT")
        with tempfile.TemporaryDirectory() as tmp, patch.object(house_state, "ROOT", Path(tmp)):
            saved = house_state.attest_library_save(
                model, building_id=model["lot_id"], library_item_name="Backup",
                capture_ref="capture:library", lot_manifest=manifest, operator_confirmed=True,
            )
            report = evaluate(row, lot_model=saved)
            self.assertEqual(report["gate"], "PURCHASE_AND_PLACE_ONE_TABLET")
            self.assertEqual((report["price"], report["quantity"]), (0, 1))
            self.assertFalse(report["execute_allowed"])
            without_cheats = {**row, "replacement": {**recovery, "cheat_sequence_started": False,
                                                       "cheat_recovery_enabled": False}}
            self.assertEqual(evaluate(without_cheats, lot_model=saved)["gate"], "PURCHASE_AND_PLACE_ONE_TABLET")
            listing["price"] = 1
            self.assertEqual(evaluate(row, lot_model=saved)["gate"],
                             "VERIFY_EXACT_ZERO_COST_TABLET_LISTING")
            listing["price"] = 0
            recovery["purchase_attempted"] = True
            self.assertEqual(evaluate(row, lot_model=saved)["gate"], "RECONCILE_TABLET_PURCHASE")
            row["tablet"] = scoped(row, definition_id=TABLET, object_ref="obj:placed",
                                   location="PLACED_IN_BUILD", owned_by_household=True,
                                   placement_outcome_ref="proof:placed")
            self.assertEqual(evaluate(row, lot_model=saved)["gate"], "RETURN_TO_LIVE_AND_VERIFY_TABLET")

    def test_host_stack_and_listener_preserve_player_and_mode_authority(self):
        row = obs(observed_at_unix=time.time())
        row["inventory"] = scoped(row, panel_state="CLOSED", hud_clear=True)
        report = evaluate_turn(NEEDS, capture_ref=CAPTURE, career_drafting=row,
                               career_drafting_mode="LIVE")
        self.assertEqual(report["next_gate"], "OPEN_PERSONAL_INVENTORY")
        result = evaluate_turn({**NEEDS, "hunger": 0.1}, capture_ref=CAPTURE,
                               career_drafting=row, career_drafting_mode="LIVE")
        self.assertEqual(result["career_drafting"]["gate"], "DRAFTING_NEEDS_FIRST")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("betterinstincts.host_listener.ROOT", root), patch(
                    "betterinstincts.host_listener.OUTPUT", root / "dist" / "host-listener"):
                activate("drafting")
                raw = {**observation("LIVE"), "career_drafting": row, "capture_ref": CAPTURE,
                       "active_lot_id": row["lot_ref"]}
                result = tick("drafting", raw, presence_probe=idle())
                self.assertEqual(result["host_stack"]["career_drafting"]["gate"], "OPEN_PERSONAL_INVENTORY")
                wrong_actor = tick("drafting", {**raw, "actor_ref": "sim:other"}, presence_probe=idle())
                self.assertEqual(wrong_actor["host_stack"]["career_drafting"]["gate"], "REOBSERVE_DRAFTING_SCOPE")
                player = tick("drafting", raw, presence_probe=PresenceProbe(True, True, last_input_age_ms=0))
                self.assertEqual(player["listener_action"], "YIELD_TO_PLAYER")
                build = build_observation()
                build["observed_at_unix"] = time.time()
                raw = {**observation("BUY"), "career_drafting": build,
                       "capture_ref": build["capture_ref"], "active_lot_id": build["lot_ref"]}
                receipt = tick("drafting", raw, presence_probe=idle())
                self.assertEqual(receipt["career_drafting"]["command"], COMMANDS[0])
                self.assertFalse(receipt["execute_clicks"])


if __name__ == "__main__":
    unittest.main()
