"""On-demand, computer-native upgrade-part purchase navigation.

Only proposes one *observed* game UI effect at a time. The existing
CooperativeScreenQueue owns player presence, desktop leases and fresh checks.
No SendInput, autostart, host service control, save access or OS repair here.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from betterinstincts.live_host_ops import assess_interaction_channel
from betterinstincts.upgrade_parts_force import (
    UpgradePartsForceError, _clamp_quantity, load_contract, resolve_part,
)
from betterinstincts.workflow_interop import CooperativeScreenQueue

PROOF = "OFFLINE_COMPUTER_MENU_QUEUE_NOT_LIVE_PURCHASE_PROOF"
STAGES = frozenset({"PORTRAIT", "COMPUTER", "MENU", "PART_PICKER", "CONFIRM", "VERIFY"})
EFFECT_KINDS = frozenset({"SELECT_OBSERVED_PORTRAIT", "OPEN_OBSERVED_COMPUTER", "SELECT_VISIBLE_LABEL", "INCREMENT_OBSERVED_PART_ROW", "CONFIRM_OBSERVED_PURCHASE"})
MORE_CHOICES = frozenset({"more choices", "more choices...", "more choices…"})


def menu_catalog(cfg: dict | None = None) -> dict:
    """Five operator-reported *purchase-menu* items, not the entire DIY kit."""
    cfg = cfg or load_contract()
    menu = cfg.get("computer_purchase_menu") or {}
    ids = menu.get("part_ids")
    if not isinstance(ids, list) or len(ids) != 5 or len(set(ids)) != 5:
        raise UpgradePartsForceError("COMPUTER_MENU_CATALOG_INVALID")
    parts = [resolve_part(pid, cfg=cfg) for pid in ids]
    if any(not p.get("computer_buyable") for p in parts):
        raise UpgradePartsForceError("COMPUTER_MENU_UNBUYABLE_PART")
    return {
        "schema": "betterinstincts.computer-upgrade-menu/v1",
        "source": menu.get("evidence_source"),
        "part_ids": list(ids),
        "parts": [{"id": p["id"], "display_name": p["display_name"]} for p in parts],
        "entry": "observed computer/laptop interactions",
        "target_label": "Purchase Upgrade Parts",
        "intermediate_menu_depth": "UNKNOWN_DISCOVER_BY_LABEL",
        "execute_allowed": False,
        "proof_ceiling": PROOF,
    }


def plan_computer_purchase(part_id: str, quantity: int = 1, *, cfg: dict | None = None) -> dict:
    """Passive boot-safe plan; a CLI command alone NEVER operates the screen."""
    cfg = cfg or load_contract()
    part = resolve_part(part_id, cfg=cfg)
    if part["id"] not in menu_catalog(cfg)["part_ids"]:
        raise UpgradePartsForceError("PART_NOT_IN_OBSERVED_COMPUTER_MENU")
    count = _clamp_quantity(quantity, cfg)
    return {
        "schema": "betterinstincts.computer-upgrade-purchase-intent/v1",
        "part_id": part["id"], "display_name": part["display_name"],
        "quantity": count, "destination": "sim_pocket_inventory",
        "on_demand": True, "boot_action": "PASSIVE_NO_FOCUS_OR_INPUT",
        "sequence": ["COMPUTER", "MENU", "PART_PICKER", "CONFIRM", "VERIFY"],
        "discovery": "Choose only observed semantic labels; menu depth and labels may differ by game build.",
        "required": [
            "EXPLICIT_USER_COMMAND", "LIVE_PAUSED_INSIDE_LOT",
            "VERIFIED_GAME_COMPUTER_AND_ACTIVE_SIM", "FRESH_MENU_OBSERVATIONS",
            "COOPERATIVE_QUEUE_WITH_TWO_IDLE_PROBES",
            "FRESH_CONTEXT_VALIDATION_BEFORE_EVERY_EFFECT",
            "PURCHASE_SPENDING_APPROVAL", "INVENTORY_OUTCOME_READBACK",
        ],
        "forbidden": [
            "AUTOBOOT_CLICKS", "OS_BLUETOOTH_SERVICE_MUTATION",
            "OS_DRIVER_OR_PAIRING_MUTATION", "INPUT_PREFERENCE_CHANGES",
            "HARDCODED_XY", "UNOBSERVED_MENU_DEPTH", "EA_CONNECT",
            "BLIND_PURCHASE_RETRY", "SPEED_OR_SAVE_MUTATION",
        ],
        "execute_allowed": False, "proof_ceiling": PROOF,
    }


def _norm(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _hold(reason: str, *, state: str = "WAIT") -> dict:
    return {"state": state, "reason": reason, "action": None,
            "execute_allowed": False, "proof_ceiling": PROOF}


def _ready(kind: str, label: str | None = None) -> dict:
    if kind not in EFFECT_KINDS:
        raise UpgradePartsForceError("GAME_UI_EFFECT_NOT_WHITELISTED")
    return {
        "state": "READY_TO_QUEUE", "action": {"kind": kind, "label": label},
        "requires_fresh_scene_and_player_admission": True,
        "execute_allowed": False,  # only the cooperative queue can dispatch
        "proof_ceiling": PROOF,
    }


def propose_computer_purchase_step(
    *,
    part_id: str,
    stage: str,
    explicit_command: bool,
    game_mode: str = "LIVE",
    paused_verified: bool = False,
    active_sim_observed: bool = False,
    computer_observed: bool = False,
    inside_lot_verified: bool = False,
    menu_labels: Sequence[str] = (),
    menu_scope: str = "ROOT",
    order_menu_observed: bool = False,
    visited_labels: Sequence[str] = (),
    menu_pages_seen: int = 0,
    page_signature_seen_before: bool = False,
    native_capability_verified: bool = False,
    desktop_fallback_opt_in: bool = False,
    human_active_or_unknown: bool = True,
    spending_authorized: bool = False,
    unit_price_observed: int | None = None,
    funds_observed: int | None = None,
    approved_spend_cap: int | None = None,
    inventory_before: int | None = None,
    inventory_after: int | None = None,
    target_portrait_id: str | None = None,
    observed_portrait_ids: Sequence[str] = (),
    target_portrait_hitbox_verified: bool = False,
    current_selected_portrait_id: str | None = None,
    cfg: dict | None = None,
) -> dict:
    """Propose ONE action from fresh observations. Never grant screen control.

    The caller must supply a new, trusted observation and rerun this decision
    for every state transition. Menu state is not reconstructed from old XY.
    """
    cfg = cfg or load_contract()
    part = resolve_part(part_id, cfg=cfg)
    if part["id"] not in menu_catalog(cfg)["part_ids"]:
        raise UpgradePartsForceError("PART_NOT_IN_OBSERVED_COMPUTER_MENU")
    stage = str(stage).upper()
    if stage not in STAGES:
        raise UpgradePartsForceError("UNKNOWN_COMPUTER_MENU_STAGE")
    if explicit_command is not True:
        return _hold("EXPLICIT_USER_COMMAND_REQUIRED")
    if human_active_or_unknown is not False:
        return _hold("PLAYER_CONTROL_TAKES_PRIORITY", state="YIELD_TO_PLAYER")
    if str(game_mode).upper() != "LIVE" or paused_verified is not True:
        return _hold("PAUSED_LIVE_MODE_REQUIRED")
    if (active_sim_observed is not True or inside_lot_verified is not True
            or computer_observed is not True):
        return _hold("FRESH_INSIDE_LOT_SIM_COMPUTER_EVIDENCE_REQUIRED")
    channel = assess_interaction_channel(
        native_capability_verified=native_capability_verified,
        desktop_fallback_opt_in=desktop_fallback_opt_in,
    )
    if not channel["channel"]:
        return _hold("VERIFIED_NATIVE_CHANNEL_OR_EXPLICIT_DESKTOP_OPT_IN_REQUIRED")

    if stage == "PORTRAIT":
        # No stale roster index or inferred click position. The downstream
        # adapter independently resolves a fresh on-screen portrait hitbox
        # under the existing cooperative queue's scene/player admission.
        if (not isinstance(target_portrait_id, str) or not target_portrait_id
                or len(target_portrait_id) > 128):
            return _hold("TARGET_PORTRAIT_ID_REQUIRED")
        if (not isinstance(observed_portrait_ids, (list, tuple))
                or len(observed_portrait_ids) > 100
                or not all(isinstance(v, str) and v for v in observed_portrait_ids)
                or len(set(observed_portrait_ids)) != len(observed_portrait_ids)):
            return _hold("OBSERVED_PORTRAIT_ROSTER_REQUIRED")
        if target_portrait_id not in observed_portrait_ids:
            return _hold("TARGET_PORTRAIT_NOT_IN_FRESH_ROSTER")
        if target_portrait_hitbox_verified is not True:
            return _hold("PORTRAIT_HITBOX_NOT_FRESHLY_VERIFIED")
        if current_selected_portrait_id == target_portrait_id:
            return _hold("PORTRAIT_ALREADY_SELECTED", state="ALREADY_SELECTED")
        return _ready("SELECT_OBSERVED_PORTRAIT", target_portrait_id)
    if stage == "COMPUTER":
        return _ready("OPEN_OBSERVED_COMPUTER")
    if stage == "MENU":
        if not isinstance(menu_pages_seen, int) or isinstance(menu_pages_seen, bool):
            return _hold("MENU_HOP_COUNT_INVALID")
        max_pages = int(cfg["computer_purchase_menu"]["max_menu_pages"])
        if menu_pages_seen < 0:
            return _hold("MENU_HOP_COUNT_INVALID")
        if menu_pages_seen >= max_pages or page_signature_seen_before is not False:
            return _hold("MENU_DISCOVERY_BOUNDED_OR_CYCLE_DETECTED")
        # User-authoritative interaction chain:
        # computer -> Order -> nested Purchase Upgrade Parts -> picker.
        # Discovery depth can vary on BOTH menus. The caller must re-observe
        # the menu context after the Order effect; this policy never infers
        # entering Order merely because Purchase Upgrade Parts is visible.
        scope = str(menu_scope or "").upper()
        if scope not in {"ROOT", "ORDER"}:
            return _hold("UNKNOWN_ORDER_MENU_SCOPE")
        if scope == "ORDER" and order_menu_observed is not True:
            return _hold("ORDER_SUBMENU_NOT_OBSERVED")
        options = {_norm(label): label for label in menu_labels if isinstance(label, str)}
        seen = {_norm(label) for label in visited_labels}
        target = "order" if scope == "ROOT" else "purchase upgrade parts"
        # An ambiguous duplicate visible target must not yield a coordinate.
        if sum(_norm(label) == target for label in menu_labels if isinstance(label, str)) > 1:
            return _hold("AMBIGUOUS_VISIBLE_ORDER_TARGET")
        if target in options and target not in seen:
            return _ready("SELECT_VISIBLE_LABEL", options[target])
        for key, original in options.items():
            if key in MORE_CHOICES:
                return _ready("SELECT_VISIBLE_LABEL", original)
        return _hold("NO_RECOGNIZED_OBSERVED_MENU_BRANCH")
    if stage == "PART_PICKER":
        label = part["display_name"]
        options = {_norm(row): row for row in menu_labels if isinstance(row, str)}
        if _norm(label) not in options:
            return _hold("REQUESTED_PART_NOT_VISIBLE_IN_PICKER")
        return _ready("SELECT_VISIBLE_LABEL", options[_norm(label)])
    if stage == "CONFIRM":
        if spending_authorized is not True:
            return _hold("PURCHASE_SPENDING_AUTHORIZATION_REQUIRED")
        amounts = (unit_price_observed, funds_observed, approved_spend_cap)
        if any(type(n) is not int or n < 0 for n in amounts):
            return _hold("FRESH_PRICE_FUNDS_AND_SPENDING_CAP_REQUIRED")
        if unit_price_observed > min(funds_observed, approved_spend_cap):
            return _hold("INSUFFICIENT_FUNDS_OR_SPENDING_CAP")
        if type(inventory_before) is not int or inventory_before < 0:
            return _hold("POCKET_INVENTORY_BASELINE_REQUIRED")
        if not any(_norm(x) in {"buy", "purchase", "confirm"} for x in menu_labels):
            return _hold("CONFIRM_CONTROL_NOT_VISIBLE")
        return _ready("CONFIRM_OBSERVED_PURCHASE")
    if stage == "VERIFY":
        if (type(inventory_before) is int and type(inventory_after) is int
                and inventory_before >= 0 and inventory_after > inventory_before):
            return {"state": "ONE_PURCHASE_OBSERVED", "part_id": part["id"],
                    "inventory_delta": inventory_after - inventory_before,
                    "action": None, "execute_allowed": False, "proof_ceiling": PROOF}
        return _hold("INVENTORY_OUTCOME_UNPROVEN_RECONCILE_BEFORE_RETRY",
                     state="NEEDS_RECONCILIATION")
    raise UpgradePartsForceError("UNREACHABLE_COMPUTER_MENU_STAGE")


def enqueue_computer_menu_step(
    queue: CooperativeScreenQueue,
    *,
    work_id: str,
    decision: Mapping[str, Any],
    validate_fresh_scene: Callable[[], Awaitable[bool]],
    perform_game_ui_effect: Callable[[dict[str, Any]], Awaitable[Any]],
) -> None:
    """Schedule exactly one independently revalidated game action.

    The game adapter must implement the typed, whitelisted effect ONLY and
    must never touch operating-system services, adapters, Bluetooth or saves.
    Partially interrupted work uses queue.reconcile, not blind retries.
    """
    if not isinstance(queue, CooperativeScreenQueue):
        raise UpgradePartsForceError("COOPERATIVE_QUEUE_REQUIRED")
    action = decision.get("action")
    if decision.get("state") != "READY_TO_QUEUE" or not isinstance(action, dict):
        raise UpgradePartsForceError("COMPUTER_STEP_NOT_READY")
    if action.get("kind") not in EFFECT_KINDS:
        raise UpgradePartsForceError("GAME_UI_EFFECT_NOT_WHITELISTED")
    if not callable(validate_fresh_scene) or not callable(perform_game_ui_effect):
        raise UpgradePartsForceError("FRESH_VALIDATOR_AND_ADAPTER_REQUIRED")

    async def effect() -> Any:
        return await perform_game_ui_effect(dict(action))

    queue.enqueue_effect(work_id, validate_fresh_scene, effect)


# Picker quantities are transaction selections, not five independent purchases.
# A host may request the next decision only after a NEW independently observed
# picker revision; it must never replay a queued arrow click from stale UI.
def _batch_quantities(requested: Mapping[str, int], cfg: dict) -> dict[str, int]:
    if not isinstance(requested, Mapping) or not requested or len(requested) > 5:
        raise UpgradePartsForceError("BATCH_REQUESTS_REQUIRED")
    allowed = set(menu_catalog(cfg)["part_ids"])
    result: dict[str, int] = {}
    for part_id, count in requested.items():
        if not isinstance(part_id, str) or part_id not in allowed:
            raise UpgradePartsForceError("BATCH_PART_NOT_IN_COMPUTER_PICKER")
        if type(count) is not int:
            raise UpgradePartsForceError("BATCH_QUANTITY_MUST_BE_INTEGER")
        result[part_id] = _clamp_quantity(count, cfg)
    return result


def plan_computer_purchase_batch(
    requests: Mapping[str, int], *, cfg: dict | None = None,
) -> dict:
    """Read-only five-kind purchase intent. Not an input/admission permit."""
    cfg = cfg or load_contract()
    quantities = _batch_quantities(requests, cfg)
    return {
        "schema": "betterinstincts.computer-upgrade-batch-intent/v1",
        "quantities": quantities,
        "part_order": menu_catalog(cfg)["part_ids"],
        "destination": "selected_sim_pocket_inventory",
        "picker_route": "OBSERVED_COMPUTER_ORDER_PURCHASE_UPGRADE_PARTS",
        "max_effects_per_decision": 1,
        "reobserve_after_each_arrow": True,
        "confirm_once_after_exact_totals": True,
        "reconcile_inventory_and_funds_before_new_purchase": True,
        "boot_action": "PASSIVE_NO_FOCUS_OR_INPUT",
        "execute_allowed": False,
        "proof_ceiling": PROOF,
    }


def plan_computer_restock_batch(
    *, stock_targets: Mapping[str, int], pocket_counts: Mapping[str, int],
    cfg: dict | None = None,
) -> dict:
    """Convert observed *personal* stock shortages to a passive picker plan."""
    cfg = cfg or load_contract()
    if not isinstance(stock_targets, Mapping) or not isinstance(pocket_counts, Mapping):
        raise UpgradePartsForceError("PERSONAL_STOCK_OBSERVATIONS_REQUIRED")
    allowed = set(menu_catalog(cfg)["part_ids"])
    if not stock_targets or any(k not in allowed for k in stock_targets):
        raise UpgradePartsForceError("COMPUTER_RESTOCK_TARGETS_INVALID")
    shortages: dict[str, int] = {}
    for part_id, target in stock_targets.items():
        current = pocket_counts.get(part_id)
        if type(target) is not int or not 0 <= target <= int(cfg["quantity"]["max"]):
            raise UpgradePartsForceError("INVALID_STOCK_TARGET")
        if type(current) is not int or current < 0:
            raise UpgradePartsForceError("PERSONAL_STOCK_OBSERVATIONS_REQUIRED")
        if current < target:
            shortages[part_id] = target - current
    if not shortages:
        return {
            "state": "STOCK_TARGETS_ALREADY_MET", "quantities": {},
            "execute_allowed": False, "proof_ceiling": PROOF,
        }
    result = plan_computer_purchase_batch(shortages, cfg=cfg)
    result["stock_targets"] = dict(stock_targets)
    result["inventory_baseline"] = {pid: pocket_counts[pid] for pid in stock_targets}
    return result


def propose_computer_batch_step(
    *, requests: Mapping[str, int], picker_rows: Sequence[Mapping[str, Any]],
    picker_revision: str, last_acted_revision: str | None = None,
    observed_total_count: int | None = None,
    observed_total_cost: int | None = None,
    observed_funds: int | None = None,
    approved_spend_cap: int | None = None,
    spending_authorized: bool = False,
    inventory_before: Mapping[str, int] | None = None,
    buy_control_visible: bool = False,
    buy_control_hitbox_verified: bool = False,
    explicit_command: bool = False,
    game_mode: str = "LIVE", paused_verified: bool = False,
    active_sim_observed: bool = False, computer_observed: bool = False,
    inside_lot_verified: bool = False, human_active_or_unknown: bool = True,
    native_capability_verified: bool = False,
    desktop_fallback_opt_in: bool = False,
    cfg: dict | None = None,
) -> dict:
    """Propose ONE increment or final Buy from a fresh five-row picker snapshot.

    Rows must be supplied by a trusted live observer, not inferred from this
    function or the user's example screenshot. The queue callback must compare
    the revision and row hitbox again immediately before the effect.
    """
    cfg = cfg or load_contract()
    quantities = _batch_quantities(requests, cfg)
    gate = propose_computer_purchase_step(
        part_id=next(iter(quantities)), stage="COMPUTER",
        explicit_command=explicit_command, game_mode=game_mode,
        paused_verified=paused_verified,
        active_sim_observed=active_sim_observed,
        computer_observed=computer_observed,
        inside_lot_verified=inside_lot_verified,
        human_active_or_unknown=human_active_or_unknown,
        native_capability_verified=native_capability_verified,
        desktop_fallback_opt_in=desktop_fallback_opt_in, cfg=cfg,
    )
    if gate["state"] != "READY_TO_QUEUE":
        return gate
    if (not isinstance(picker_revision, str) or not picker_revision.strip()
            or len(picker_revision) > 128
            or picker_revision == last_acted_revision):
        return _hold("FRESH_PICKER_REVISION_REQUIRED")
    if not isinstance(picker_rows, (list, tuple)) or len(picker_rows) != 5:
        return _hold("FIVE_OBSERVED_PICKER_ROWS_REQUIRED")

    allowed_ids = menu_catalog(cfg)["part_ids"]
    rows: dict[str, Mapping[str, Any]] = {}
    max_qty = int(cfg["quantity"]["max"])
    for row in picker_rows:
        if not isinstance(row, Mapping):
            return _hold("INVALID_OBSERVED_PICKER_ROW")
        pid = row.get("part_id")
        if pid not in allowed_ids or pid in rows:
            return _hold("INVALID_OR_DUPLICATE_PICKER_PART")
        count, price = row.get("selected_count"), row.get("unit_price")
        if (type(count) is not int or not 0 <= count <= max_qty
                or type(price) is not int or price < 0):
            return _hold("FRESH_PICKER_COUNT_AND_PRICE_REQUIRED")
        # A row is identified from the observed label, not by a fixed XY.
        # Screenshot uses singular "Part"; the contract catalog uses "Parts".
        name = resolve_part(pid, cfg=cfg)["display_name"]
        accepted = {_norm(name), _norm(name.removesuffix("s"))}
        if _norm(row.get("visible_label")) not in accepted:
            return _hold("OBSERVED_PART_ROW_LABEL_MISMATCH")
        rows[pid] = row
    if set(rows) != set(allowed_ids):
        return _hold("FIVE_OBSERVED_PICKER_ROWS_REQUIRED")
    if (type(observed_total_count) is not int or type(observed_total_cost) is not int
            or observed_total_count < 0 or observed_total_cost < 0):
        return _hold("FRESH_PICKER_TOTALS_REQUIRED")
    selected_count = sum(row["selected_count"] for row in rows.values())
    selected_cost = sum(row["selected_count"] * row["unit_price"] for row in rows.values())
    if observed_total_count != selected_count or observed_total_cost != selected_cost:
        return _hold("PICKER_TOTALS_DO_NOT_RECONCILE")
    if spending_authorized is not True:
        return _hold("PURCHASE_SPENDING_AUTHORIZATION_REQUIRED")
    if any(type(v) is not int or v < 0 for v in
           (observed_funds, approved_spend_cap)):
        return _hold("FRESH_FUNDS_AND_SPEND_CAP_REQUIRED")
    planned_cost = sum(quantities.get(pid, 0) * rows[pid]["unit_price"]
                       for pid in allowed_ids)
    if planned_cost > min(observed_funds, approved_spend_cap):
        return _hold("BATCH_EXCEEDS_FUNDS_OR_APPROVED_SPENDING_CAP")
    if any(rows[pid]["selected_count"] > quantities.get(pid, 0)
           for pid in allowed_ids):
        return _hold("PICKER_SELECTION_EXCEEDS_AUTHORIZED_BATCH")

    for pid in allowed_ids:
        row = rows[pid]
        if row["selected_count"] < quantities.get(pid, 0):
            if row.get("increment_visible") is not True:
                return _hold("INCREMENT_CONTROL_NOT_VISIBLE")
            if row.get("increment_hitbox_verified") is not True:
                return _hold("INCREMENT_CONTROL_NOT_FRESHLY_VERIFIED")
            action = _ready("INCREMENT_OBSERVED_PART_ROW", pid)
            action["action"].update({
                "expected_selected_count": row["selected_count"],
                "expected_total_count": observed_total_count,
                "picker_revision": picker_revision,
            })
            return action

    if (not isinstance(inventory_before, Mapping)
            or any(type(inventory_before.get(pid)) is not int
                   or inventory_before[pid] < 0 for pid in allowed_ids)):
        return _hold("FIVE_PART_PERSONAL_INVENTORY_BASELINE_REQUIRED")
    if buy_control_visible is not True or buy_control_hitbox_verified is not True:
        return _hold("BUY_CONTROL_NOT_FRESHLY_VERIFIED")
    action = _ready("CONFIRM_OBSERVED_PURCHASE")
    action["action"].update({
        "expected_total_count": observed_total_count,
        "expected_total_cost": observed_total_cost,
        "picker_revision": picker_revision,
    })
    return action


def verify_computer_batch_purchase(
    *, requests: Mapping[str, int],
    inventory_before: Mapping[str, int], inventory_after: Mapping[str, int],
    funds_before: int, funds_after: int, expected_total_cost: int,
    cfg: dict | None = None,
) -> dict:
    """One final Buy is complete only with exact pocket and funds readback."""
    cfg = cfg or load_contract()
    quantities = _batch_quantities(requests, cfg)
    allowed = menu_catalog(cfg)["part_ids"]
    if any(not isinstance(v, Mapping) for v in (inventory_before, inventory_after)):
        return _hold("BATCH_OUTCOME_UNPROVEN", state="NEEDS_RECONCILIATION")
    if (any(type(mapping.get(pid)) is not int or mapping[pid] < 0
            for mapping in (inventory_before, inventory_after) for pid in allowed)
            or any(type(n) is not int or n < 0 for n in
                   (funds_before, funds_after, expected_total_cost))):
        return _hold("BATCH_OUTCOME_UNPROVEN", state="NEEDS_RECONCILIATION")
    deltas = {pid: inventory_after[pid] - inventory_before[pid] for pid in allowed}
    if (any(deltas[pid] != quantities.get(pid, 0) for pid in allowed)
            or funds_before - funds_after != expected_total_cost):
        return _hold("BATCH_OUTCOME_UNPROVEN_RECONCILE_BEFORE_RETRY",
                     state="NEEDS_RECONCILIATION")
    return {
        "state": "BATCH_PURCHASE_OBSERVED", "inventory_deltas": deltas,
        "spend_observed": expected_total_cost,
        "action": None, "execute_allowed": False, "proof_ceiling": PROOF,
    }


def enqueue_computer_batch_step(
    queue: CooperativeScreenQueue, *, work_id: str,
    decision: Mapping[str, Any],
    validate_fresh_scene: Callable[[], Awaitable[bool]],
    validate_fresh_picker: Callable[[dict[str, Any]], Awaitable[bool]],
    perform_game_ui_effect: Callable[[dict[str, Any]], Awaitable[Any]],
) -> None:
    """Queue one arrow/Buy only after rechecking the exact observed picker.

    The trusted adapter's fresh-picker validator must reobserve the same
    active Sim, five row IDs, chosen row/button hitbox, selected count,
    funds, total cost, and revision. A Boolean from stale cache is not proof.
    """
    action = decision.get("action")
    if (decision.get("state") != "READY_TO_QUEUE"
            or not isinstance(action, dict)
            or action.get("kind") not in {
                "INCREMENT_OBSERVED_PART_ROW", "CONFIRM_OBSERVED_PURCHASE"
            }
            or not isinstance(action.get("picker_revision"), str)
            or not action["picker_revision"]
            or not callable(validate_fresh_picker)):
        raise UpgradePartsForceError("FRESH_BATCH_PICKER_ACTION_REQUIRED")

    async def validate_both() -> bool:
        if not await validate_fresh_scene():
            return False
        return await validate_fresh_picker(dict(action))

    enqueue_computer_menu_step(
        queue, work_id=work_id, decision=decision,
        validate_fresh_scene=validate_both,
        perform_game_ui_effect=perform_game_ui_effect,
    )
