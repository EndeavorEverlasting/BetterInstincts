"""Exercise title, household and chronology routing through the launcher."""
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time
import unittest
from unittest.mock import Mock, patch

from scripts import game_host, launch_save_route, play, smart_start
from scripts.save_catalog import SCHEMA
from tests.test_launch_save_route import PATCH, RUN, lab, register
from tests.test_process_bound_play import DISPATCHED, GAME, REUSED_PID

HOUSE = "household:lab"
OTHER = "household:other"
ALL = ("Alpha", "Beta", "Gamma")


def save(number, name, *, home=HOUSE, roster=ALL, played=None):
    return {
        "save_id": lab(number, 1)["save_id"], "slot": f"Slot_{number:08X}",
        "save_name": name, "last_played_utc": played,
        "households": [{
            "household_id": home, "household_name": "Test Household" if home == HOUSE else "Other",
            "members": [{"sim_id": "sim:" + name.lower(), "sim_name": name} for name in roster],
        }],
    }


class SemanticSaveLaunchTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.path = self.root / "context.json"
        self.cert = self.root / "cert.json"
        self.catalog = {
            "schema": SCHEMA, "process": asdict(GAME), "source": "IN_GAME_SAVE_INVENTORY",
            "scene": "MAIN_MENU", "inventory_complete": True, "capture_ref": "capture:catalog",
            "observed_at_unix": time(),
        }

    def setup_route(self, saves, entries, mode="dev"):
        (self.root / "registry.json").write_text(json.dumps(register(*entries)))
        data = {
            "schema": "betterinstincts.startup-save-context/v1", "startup_mode": mode,
            "game_version": PATCH, "run_id": RUN, "registry": "registry.json",
            "save_catalog": {**self.catalog, "saves": saves},
            "navigation_profiles": {row["save_id"]: "profile.json" for row in saves},
        }
        self.path.write_text(json.dumps(data))
        (self.root / "profile.json").touch()

    def entry(self, number, day, **values):
        return {**lab(number, day), "household_id": HOUSE,
                "household_binding_confirmed": True, **values}

    def dev(self, **selection):
        return launch_save_route.route_mode("dev", GAME, self.path, launch_context=self.cert,
                                           selection=selection)

    def test_dev_uses_oldest_with_all_requested_members_in_chosen_household(self):
        self.setup_route([save(4, "Older Solo", roster=("Alpha",)),
                          save(5, "Unrelated", home=OTHER),
                          save(6, "Three-person lab"),
                          save(7, "Special protected slot"),
                          save(8, "Newer Lab")],
                         [self.entry(4, 2), self.entry(5, 1, household_id=OTHER),
                          self.entry(6, 5), self.entry(7, 1), self.entry(8, 7)])
        result = self.dev(household_name="  test HOUSEHOLD ", expected_save_name="Three-person lab",
                          minimum_members=3, required_members=list(ALL))
        self.assertEqual(result["candidate_slot"], "Slot_00000006")
        self.assertEqual(result["candidate_save_name"], "Three-person lab")
        self.assertEqual(result["household_member_ids"], ["sim:alpha", "sim:beta", "sim:gamma"])
        self.assertIsNone(result["control_permit"])

    def test_member_count_does_not_replace_required_roster_or_named_pin(self):
        self.setup_route([save(4, "Three with replacement", roster=("Alpha", "Beta", "Delta")),
                          save(6, "Earliest full"), save(8, "Later full")],
                         [self.entry(4, 1), self.entry(6, 4), self.entry(8, 7)])
        result = self.dev(household_name="Test Household", minimum_members=3,
                          required_members=list(ALL), expected_save_name="Later full")
        self.assertEqual(result["reason"], "REQUESTED_TITLE_IS_NOT_OLDEST_AUTHORIZED_ROSTER_MATCH")
        self.assertEqual(result["oldest_eligible_save_name"], "Earliest full")

    def test_name_can_resolve_but_cannot_authorize_unregistered_slot(self):
        self.setup_route([save(6, "Named lab")], [])
        result = self.dev(household_name="Test Household", expected_save_name="Named lab")
        self.assertEqual(result["reason"], "NO_ELIGIBLE_LAB_DISPOSABLE_CANDIDATE")
        self.assertEqual(result["observed_target"]["slot"], "Slot_00000006")
        self.assertIsNone(result["selected_save_id"])

    def test_process_capture_and_title_ambiguity_hold(self):
        self.setup_route([save(6, "Duplicate"), save(8, "duplicate")],
                         [self.entry(6, 2), self.entry(8, 7)])
        self.assertEqual(self.dev(expected_save_name="Duplicate")["reason"],
                         "SAVE_TITLE_MISSING_OR_AMBIGUOUS")
        self.assertEqual(launch_save_route.route_mode(
            "dev", REUSED_PID, self.path, launch_context=self.cert,
        )["reason"], "CURRENT_GAME_SAVE_CATALOG_REQUIRED")
        self.catalog["observed_at_unix"] = time() - 500
        self.setup_route([save(6, "Old capture")], [self.entry(6, 2)])
        self.assertEqual(self.dev()["reason"], "CURRENT_GAME_SAVE_CATALOG_REQUIRED")

    def test_choices_use_observed_names_and_require_unique_household(self):
        self.setup_route([save(6, "One"), save(8, "Two", home=OTHER)], [])
        with patch.object(launch_save_route, "view", return_value={"preferred_household_id": None}):
            result = self.dev()
        self.assertEqual(result["household_choices"], {HOUSE: "Test Household", OTHER: "Other"})
        self.assertEqual(result["state"], "HOUSEHOLD_CHOICE_REQUIRED")

    def test_prod_latest_observed_does_not_fall_back_to_approved_older(self):
        self.setup_route([save(6, "Older", played="2026-11-11T00:00:00Z"),
                          save(8, "Most recently played", played="2026-11-16T00:00:00Z")],
                         [self.entry(6, 3)], mode="production")
        route = launch_save_route.route_mode("production", GAME, self.path, launch_context=self.cert)
        self.assertEqual(route["candidate_save_name"], "Most recently played")
        self.assertEqual(route["reason"], "LATEST_SAVE_REQUIRES_PLAYER_LOAD")

    def test_prod_never_dispatches_explicitly_protected_slot_even_with_lab_claim(self):
        self.setup_route([save(7, "Protected", played="2026-11-16T00:00:00Z")],
                         [self.entry(7, 3)], mode="production")
        route = launch_save_route.route_mode("production", GAME, self.path, launch_context=self.cert)
        self.assertEqual(route["reason"], "LATEST_SLOT_REQUIRES_SEPARATE_AUTHORIZATION")

    def test_latest_approved_production_reaches_calibrated_loader_in_open_main_menu(self):
        self.setup_route([save(8, "Recent", played="2026-11-16T00:00:00Z")],
                         [self.entry(8, 3)], mode="production")
        latest = {"selected_save_id": lab(8, 1)["save_id"], "save_registry": "registry.json",
                  "game_version": PATCH, "selected_slot": "Slot_00000008"}
        game = {**DISPATCHED, "state": "GAME_ALREADY_RUNNING_NO_DUPLICATE_LAUNCH"}
        with (patch.object(smart_start, "observe_launched_process", return_value=GAME),
              patch.object(smart_start, "require_same_game_process"),
              patch.object(game_host, "profile", return_value=(latest, "digest")),
              patch.object(game_host, "navigate_startup_save") as dispatch):
            result = play.complete_play("production", game, {}, self.path,
                                        self.root / "receipt.json", {}, Mock())
        dispatch.assert_called_once()
        self.assertEqual(dispatch.call_args.kwargs["mode"], "production")
        self.assertEqual(result["save_state"], "PRODUCTION_SAVE_PLAY_DISPATCHED")
        self.assertEqual(result["reason"], "NATIVE_SAVE_READBACK_MISSING")

    def test_calibration_for_another_slot_holds_before_dispatch(self):
        self.setup_route([save(6, "Lab")], [self.entry(6, 2)])
        profile = {"selected_save_id": lab(6, 1)["save_id"], "save_registry": "registry.json",
                   "game_version": PATCH, "selected_slot": "Slot_00000005"}
        with (patch.object(smart_start, "observe_launched_process", return_value=GAME),
              patch.object(game_host, "profile", return_value=(profile, "digest")),
              patch.object(game_host, "navigate_startup_save") as dispatch):
            result = play.complete_play("dev", DISPATCHED, {}, self.path,
                                        self.root / "receipt.json", {}, Mock(),
                                        selection={"household_name": "Test Household"})
        dispatch.assert_not_called()
        self.assertEqual(result["stage"], "dev_calibration")
