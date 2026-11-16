"""Advisory steps for an observed Civil Designer Eco-Invention drafting goal."""
from __future__ import annotations

import time
from collections.abc import Mapping

from betterinstincts.build_library_checkpoint import (
    BuildLibraryCheckpointError,
    admit_live_structure_effect,
)
from betterinstincts.compatibility import VERSION_RE
from betterinstincts.hidden_object_discovery import load_contract as hidden_object_contract
from betterinstincts.house_state import LOT_ID_RE
from betterinstincts.household_object_force import reject_forbidden_console
from betterinstincts.ui_microsystems import (
    TOKEN,
    UIMicrosystemError,
    panel_observation_matches,
    plan_open_bottom_right_panel,
    validate_hitbox_calibration,
)

SCHEMA = "betterinstincts.career-drafting/v1"
MAX_OBSERVATION_AGE = 30
SCOPE = ("game_build", "session_ref", "save_ref", "household_ref", "sim_ref", "objective_ref")
PANEL = "personal_inventory"
CATALOG_UNLOCK = "bb.ignoregameplayunlocksentitlement"


def _ref(value):
    return isinstance(value, str) and TOKEN.fullmatch(value) is not None


def _record(value):
    return value if isinstance(value, Mapping) else {}


def _same_scope(row, observation, keys):
    return all(row.get(key) == observation.get(key) for key in keys)


def _fresh(row, observation):
    return _same_scope(row, observation, (*SCOPE, "lot_ref", "capture_ref"))


def _inventory_step(inventory, observation, cfg):
    """Return an inventory step, or None after a continuous top-to-bottom scan."""
    if not _fresh(inventory, observation):
        return "OBSERVE_PERSONAL_INVENTORY", {}
    if inventory.get("panel_state") == "CLOSED":
        if inventory.get("hud_clear") is True:
            hotkey = plan_open_bottom_right_panel(PANEL)
            return "OPEN_PERSONAL_INVENTORY", {
                "panel_id": PANEL, "hotkey_id": hotkey["hotkey_id"],
                "chord": hotkey["chord"], "order": hotkey["order"],
                "panel_cues": hotkey["panel_cues"],
            }
        return "OBSERVE_PERSONAL_INVENTORY", {}
    if (inventory.get("panel_state") != "OPEN"
            or inventory.get("panel_id") != PANEL
            or not _ref(inventory.get("layout_revision"))
            or not _ref(inventory.get("scan_ref"))
            or inventory.get("unfiltered") is not True):
        return "OBSERVE_UNFILTERED_PERSONAL_INVENTORY", {}

    pages = inventory.get("page_refs")
    if (not isinstance(pages, list) or not 1 <= len(pages) <= cfg["max_inventory_pages"]
            or not all(_ref(page) for page in pages) or len(set(pages)) != len(pages)
            or inventory.get("no_gaps_verified") is not True):
        return "RECONCILE_INVENTORY_SCAN", {}
    if inventory.get("current_page_ref") != pages[-1]:
        return "RECONCILE_INVENTORY_SCAN", {}
    if inventory.get("at_bottom") is True and inventory.get("started_at_top") is True:
        return None
    if inventory.get("last_scroll_from_page_ref") == pages[-1]:
        return "RECONCILE_INVENTORY_SCROLL", {}
    if inventory.get("started_at_top") is True and len(pages) == cfg["max_inventory_pages"]:
        return "INVENTORY_SCAN_LIMIT_REACHED", {}

    # The current list hitbox and visible geometry must agree. Never scroll
    # over the world or use a screen coordinate captured before a panel change.
    panel_obs = _record(inventory.get("scroll_observation"))
    calibration = _record(inventory.get("scroll_calibration"))
    width, height = inventory.get("client_width"), inventory.get("client_height")
    if (type(width) is not int or type(height) is not int
            or calibration.get("panel_id") != PANEL
            or calibration.get("target_id") != "personal_inventory.scroll_list"
            or calibration.get("ui_layout_revision") != inventory["layout_revision"]
            or calibration.get("selected_sim_revision") != inventory.get("selected_sim_revision")
            or panel_obs.get("capture_ref") != observation["capture_ref"]):
        return "CALIBRATE_INVENTORY_SCROLL_TARGET", {}
    try:
        target = validate_hitbox_calibration(calibration, mode="LIVE", width=width, height=height)
        matched = panel_observation_matches(panel_obs, target)
    except (UIMicrosystemError, TypeError, KeyError):
        matched = False
    if not matched:
        return "CALIBRATE_INVENTORY_SCROLL_TARGET", {}
    if type(inventory.get("at_bottom")) is not bool:
        return "OBSERVE_INVENTORY_SCROLL_POSITION", {}
    direction = "DOWN" if inventory.get("started_at_top") is True else "UP_TO_START"
    return "SCROLL_PERSONAL_INVENTORY", {
        "direction": direction, "cursor_client_xy": target["click"],
        "scroll_hitbox": target["hitbox"], "scan_ref": inventory["scan_ref"],
        "after_page_ref": pages[-1],
    }


def _replacement_step(observation, lot_model, cfg):
    recovery = _record(observation.get("replacement"))
    if (not _fresh(recovery, observation)
            or recovery.get("owned_routes_exhausted") is not True
            or not _ref(recovery.get("exhaustion_ref"))
            or recovery.get("catalog_recovery_enabled") is not True):
        return "REVIEW_TABLET_REPLACEMENT", {}
    if recovery.get("purchase_attempted") is not False:
        return "RECONCILE_TABLET_PURCHASE", {}

    mode = observation["mode"]
    if mode == "LIVE":
        return "OPEN_BUILD_BUY_FOR_TABLET", {}
    authorization = _record(recovery.get("live_search_receipt"))
    if (not _same_scope(authorization, observation, (*SCOPE, "lot_ref"))
            or not _ref(authorization.get("capture_ref"))
            or authorization.get("capture_ref") == observation["capture_ref"]
            or authorization.get("mode") != "LIVE"
            or authorization.get("gate") != "OPEN_BUILD_BUY_FOR_TABLET"
            or authorization.get("exhaustion_ref") != recovery["exhaustion_ref"]):
        return "VERIFY_PRIOR_LIVE_TABLET_SEARCH", {}
    item = _record(recovery.get("listing"))
    exact_listing = (
        _fresh(item, observation) and item.get("definition_id") == cfg["tablet_id"]
        and item.get("label") == cfg["tablet_label"] and _ref(item.get("catalog_ref"))
        and item.get("available") is True
        and type(item.get("price")) is int and item["price"] == cfg["expected_replacement_price"]
    )
    cheat_in_progress = recovery.get("cheat_sequence_started") is True
    if not cheat_in_progress:
        if recovery.get("console_closed") is not True:
            return "VERIFY_TABLET_CONSOLE_CLOSED", {}
        if recovery.get("observed_query") != cfg["catalog_query"]:
            return "SEARCH_BUILD_BUY_FOR_TABLET", {"query": cfg["catalog_query"]}
        if not exact_listing and recovery.get("tablet_locked_or_missing_verified") is not True:
            return "VERIFY_EXACT_ZERO_COST_TABLET_LISTING", {}

    if cheat_in_progress or not exact_listing:
        step = _unlock_step(recovery)
        if step is not None:
            return step
    if recovery.get("observed_query") != cfg["catalog_query"]:
        return "SEARCH_BUILD_BUY_FOR_TABLET", {"query": cfg["catalog_query"]}
    if not exact_listing:
        return "VERIFY_EXACT_ZERO_COST_TABLET_LISTING", {}
    if (recovery.get("placement_verified") is not True
            or not _ref(recovery.get("placement_ref"))):
        return "VERIFY_TABLET_PLACEMENT", {}
    if not isinstance(lot_model, Mapping) or lot_model.get("lot_id") != observation["lot_ref"]:
        return "VERIFY_WHOLE_LOT_BUILD_CHECKPOINT", {}
    try:
        checkpoint = admit_live_structure_effect(
            lot_model, "PURCHASE_BUILD_OBJECT", held_object=recovery.get("held_object")
        )
    except (BuildLibraryCheckpointError, TypeError, ValueError):
        return "VERIFY_WHOLE_LOT_BUILD_CHECKPOINT", {}
    if checkpoint["state"] != "LIBRARY_ADMIT":
        return "VERIFY_WHOLE_LOT_BUILD_CHECKPOINT", {}
    return "PURCHASE_AND_PLACE_ONE_TABLET", {
        "catalog_ref": item["catalog_ref"], "placement_ref": recovery["placement_ref"],
        "price": item["price"], "quantity": 1,
    }


def _unlock_step(recovery):
    cfg_hidden = hidden_object_contract()
    testing, show_hidden = cfg_hidden["ordered_console_lines"]
    console_lines = (testing, CATALOG_UNLOCK, show_hidden)
    confirmed = recovery.get("confirmed_commands", [])
    if (not isinstance(confirmed, list) or len(confirmed) > len(console_lines)
            or confirmed != list(console_lines[:len(confirmed)])):
        return "RECONCILE_TABLET_CONSOLE", {}
    if len(confirmed) < len(console_lines):
        if recovery.get("cheat_recovery_enabled") is not True:
            return "CHEAT_RECOVERY_DISABLED", {}
        if recovery.get("console_closed") is True:
            return "OPEN_TABLET_CHEAT_CONSOLE", {
                "chord": cfg_hidden["platform_console_chords"]["windows"],
            }
        if recovery.get("console_closed") is not False:
            return "OBSERVE_TABLET_CHEAT_CONSOLE", {}
        line = console_lines[len(confirmed)]
        reject_forbidden_console(line)
        return "ENTER_TABLET_UNLOCK_COMMAND", {"command": line, "submit_key": "Enter"}
    if recovery.get("console_closed") is not True:
        return "CLOSE_TABLET_CHEAT_CONSOLE", {}
    return None


def evaluate_drafting(observation, *, cfg, capture_ref, mode, lot_model=None,
                      now=None, player_blocked=False, needs_safe=True):
    """Evaluate one capture. A consumer must obtain its own one-effect admission."""
    def report(step, **parameters):
        return {
            "schema": "betterinstincts.career-drafting-result/v1", "gate": step,
            "capture_ref": capture_ref, "execute_allowed": False,
            "proof_ceiling": "CAREER_DRAFTING_ADVISORY_ONLY", **parameters,
        }

    obs = _record(observation)
    if obs.get("schema") != SCHEMA:
        return report("REOBSERVE_DRAFTING_SCOPE")
    if player_blocked or obs.get("player_directed") is not False:
        return report("DRAFTING_PLAYER_FIRST")
    if not needs_safe:
        return report("DRAFTING_NEEDS_FIRST")

    at = time.time() if now is None else now
    stamp = obs.get("observed_at_unix")
    if (type(stamp) not in (int, float) or not 0 <= stamp <= 1_000_000_000_000
            or type(at) not in (int, float) or not 0 <= at <= 1_000_000_000_000
            or not 0 <= at - stamp <= MAX_OBSERVATION_AGE
            or obs.get("capture_ref") != capture_ref
            or not all(_ref(obs.get(k)) for k in (*SCOPE, "capture_ref"))
            or not isinstance(obs.get("lot_ref"), str)
            or LOT_ID_RE.fullmatch(obs["lot_ref"]) is None
            or VERSION_RE.fullmatch(obs["game_build"]) is None
            or mode not in ("LIVE", "BUY", "BUILD") or obs.get("mode") != mode
            or obs.get("scene_verified") is not True or obs.get("queue_verified") is not True
            or obs.get("lab_save_verified") is not True or obs.get("eco_lifestyle") is not True):
        return report("REOBSERVE_DRAFTING_SCOPE")
    if obs.get("career_track") != cfg["track"] or obs.get("objective") != cfg["objective"]:
        return report("NO_MATCHING_DRAFT_OBJECTIVE")
    status = obs.get("objective_status")
    if status == "COMPLETE":
        completion = _record(obs.get("completion"))
        if (_fresh(completion, obs) and _ref(completion.get("blueprint_ref"))
                and _ref(completion.get("objective_progress_ref"))
                and completion["blueprint_ref"] != completion["objective_progress_ref"]):
            return report("DRAFT_OBJECTIVE_COMPLETE")
    if status != "PENDING":
        return report("VERIFY_DRAFT_OBJECTIVE_STATE")

    if obs.get("effect_pending") is not False:
        return report("RECONCILE_DRAFTING_EFFECT")
    tablet = _record(obs.get("tablet"))
    if tablet and (not _fresh(tablet, obs) or not _ref(tablet.get("object_ref"))
                   or tablet.get("definition_id") != cfg["tablet_id"]
                   or tablet.get("location") not in ("PERSONAL_INVENTORY", "CURRENT_LOT", "PLACED_IN_BUILD")):
        return report("VERIFY_TABLET_IDENTITY_AND_LOCATION")
    if tablet:
        target = tablet["object_ref"]
        location = tablet["location"]
        if mode != "LIVE":
            if (location != "PLACED_IN_BUILD" or tablet.get("owned_by_household") is not True
                    or not _ref(tablet.get("placement_outcome_ref"))):
                return report("VERIFY_TABLET_PLACEMENT_OUTCOME")
            return report("RETURN_TO_LIVE_AND_VERIFY_TABLET", object_ref=target)
        if (location == "CURRENT_LOT" and tablet.get("pickup_available") is True
                and tablet.get("owned_by_household") is True
                and tablet.get("on_lot_target_verified") is True):
            return report("PUT_TABLET_IN_PERSONAL_INVENTORY", object_ref=target)
        if location != "PERSONAL_INVENTORY":
            return report("VERIFY_SAFE_TABLET_PICKUP", object_ref=target)
        if obs.get("draft_already_queued") is not False:
            return report("VERIFY_NO_DUPLICATE_DRAFT", object_ref=target)
        interaction = _record(tablet.get("draft_interaction"))
        if not interaction:
            return report("INSPECT_TABLET_INTERACTIONS", object_ref=target)
        if (not _fresh(interaction, obs) or interaction.get("object_ref") != target
                or interaction.get("label") != cfg["interaction_label"]
                or interaction.get("enabled") is not True or not _ref(interaction.get("interaction_ref"))):
            return report("VERIFY_EXACT_ENABLED_DRAFT_INTERACTION", object_ref=target)
        return report(
            "DRAFT_ECO_INVENTION_CONCEPT", object_ref=target,
            interaction_ref=interaction["interaction_ref"],
            verify_after="OBSERVE_BLUEPRINT_AND_MATCHING_OBJECTIVE_PROGRESS",
        )

    replacement = _record(obs.get("replacement"))
    if replacement and replacement.get("purchase_attempted") is not False:
        return report("RECONCILE_TABLET_PURCHASE")
    if mode == "LIVE":
        step = _inventory_step(_record(obs.get("inventory")), obs, cfg)
        if step is not None:
            gate, parameters = step
            return report(gate, **parameters)
        search = _record(obs.get("owned_search"))
        if not _fresh(search, obs):
            return report("CHECK_CURRENT_LOT_AND_HOUSEHOLD_STORAGE")
        if search.get("household_inventory_status") == "TABLET_FOUND":
            return report("RECOVER_TABLET_FROM_HOUSEHOLD_STORAGE")
        if (search.get("current_lot_status") != "VERIFIED_ABSENT"
                or search.get("household_inventory_status") != "VERIFIED_ABSENT"):
            return report("CHECK_CURRENT_LOT_AND_HOUSEHOLD_STORAGE")
        last_seen = _record(search.get("last_seen"))
        if last_seen and (
                not _same_scope(last_seen, obs, SCOPE[:-1])
                or not isinstance(last_seen.get("lot_ref"), str)
                or LOT_ID_RE.fullmatch(last_seen["lot_ref"]) is None
                or not _ref(last_seen.get("object_ref"))
                or last_seen.get("definition_id") != cfg["tablet_id"]):
            return report("VERIFY_LAST_KNOWN_TABLET_LOCATION")
        if last_seen and last_seen["lot_ref"] != obs["lot_ref"]:
            prior_lot = _record(search.get("prior_lot_review"))
            if (not _fresh(prior_lot, obs)
                    or prior_lot.get("reviewed_lot_ref") != last_seen["lot_ref"]
                    or prior_lot.get("object_ref") != last_seen["object_ref"]
                    or prior_lot.get("status") not in ("VERIFIED_ABSENT", "VERIFIED_INACCESSIBLE")):
                return report("REVIEW_LAST_KNOWN_LOT_FOR_TABLET", lot_ref=last_seen["lot_ref"],
                              object_ref=last_seen["object_ref"])
        elif search.get("last_known_location_reviewed") is not True:
            return report("REVIEW_LAST_KNOWN_TABLET_LOCATION")

    step, parameters = _replacement_step(obs, lot_model, cfg)
    if step == "OPEN_BUILD_BUY_FOR_TABLET":
        parameters.update({key: obs[key] for key in (*SCOPE, "lot_ref")})
        parameters.update(mode="LIVE", exhaustion_ref=replacement["exhaustion_ref"])
    return report(step, **parameters)
