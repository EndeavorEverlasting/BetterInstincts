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
STAGES = frozenset({"COMPUTER", "MENU", "PART_PICKER", "CONFIRM", "VERIFY"})
EFFECT_KINDS = frozenset({"OPEN_OBSERVED_COMPUTER", "SELECT_VISIBLE_LABEL", "CONFIRM_OBSERVED_PURCHASE"})
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
    if not explicit_command:
        return _hold("EXPLICIT_USER_COMMAND_REQUIRED")
    if human_active_or_unknown:
        return _hold("PLAYER_CONTROL_TAKES_PRIORITY", state="YIELD_TO_PLAYER")
    if str(game_mode).upper() != "LIVE" or not paused_verified:
        return _hold("PAUSED_LIVE_MODE_REQUIRED")
    if not active_sim_observed or not inside_lot_verified or not computer_observed:
        return _hold("FRESH_INSIDE_LOT_SIM_COMPUTER_EVIDENCE_REQUIRED")
    channel = assess_interaction_channel(
        native_capability_verified=native_capability_verified,
        desktop_fallback_opt_in=desktop_fallback_opt_in,
    )
    if not channel["channel"]:
        return _hold("VERIFIED_NATIVE_CHANNEL_OR_EXPLICIT_DESKTOP_OPT_IN_REQUIRED")

    if stage == "COMPUTER":
        return _ready("OPEN_OBSERVED_COMPUTER")
    if stage == "MENU":
        if not isinstance(menu_pages_seen, int) or isinstance(menu_pages_seen, bool):
            return _hold("MENU_HOP_COUNT_INVALID")
        max_pages = int(cfg["computer_purchase_menu"]["max_menu_pages"])
        if menu_pages_seen >= max_pages or page_signature_seen_before:
            return _hold("MENU_DISCOVERY_BOUNDED_OR_CYCLE_DETECTED")
        options = {_norm(label): label for label in menu_labels if isinstance(label, str)}
        seen = {_norm(label) for label in visited_labels}
        for preferred in ("purchase upgrade parts", "order"):
            if preferred in options and preferred not in seen:
                return _ready("SELECT_VISIBLE_LABEL", options[preferred])
        for key, original in options.items():
            if key in MORE_CHOICES and key not in seen:
                return _ready("SELECT_VISIBLE_LABEL", original)
        return _hold("NO_RECOGNIZED_OBSERVED_MENU_BRANCH")
    if stage == "PART_PICKER":
        label = part["display_name"]
        options = {_norm(row): row for row in menu_labels if isinstance(row, str)}
        if _norm(label) not in options:
            return _hold("REQUESTED_PART_NOT_VISIBLE_IN_PICKER")
        return _ready("SELECT_VISIBLE_LABEL", options[_norm(label)])
    if stage == "CONFIRM":
        if not spending_authorized:
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
