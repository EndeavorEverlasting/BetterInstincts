"""Observed Sims purchase dialogs: bounded catalog traversal and one-effect cart plans.

Offline policy only. This does not move a cursor, spend money, modify a save,
or grant a game effect. The existing cooperative queue remains the effect owner.
A newly observed viewport/revision is needed after every proposed action.
"""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

PROOF = "OFFLINE_PURCHASE_DIALOG_POLICY_NOT_NATIVE_OR_LIVE_PROOF"
MAX_PAGES = 24
MAX_ITEMS = 240
MAX_QTY = 999
MAX_PRICE = 1_000_000
TRIGGERS = frozenset({
    "career_required_material", "garden_missing_seed", "garden_missing_ingredient",
    "handiness_upgrade_part", "servo_repair_part", "fixer_bot_repair_part",
    "apothecary_recipe", "nectar_recipe", "crafting_recipe",
    "household_restock", "explicit_player_purchase",
})
ACTIONS = frozenset({
    "SCROLL_UP_ONE_PAGE", "SCROLL_DOWN_ONE_PAGE",
    "INCREMENT_OBSERVED_ROW", "CONFIRM_OBSERVED_PURCHASE",
})


def _valid_id(value: object) -> bool:
    return isinstance(value, str) and 0 < len(value.strip()) <= 128


def _nonnegative(value: object, limit: int = MAX_QTY) -> bool:
    return type(value) is int and 0 <= value <= limit


def _hold(reason: str, *, catalog: dict | None = None,
          cart: dict | None = None, state: str = "WAIT") -> dict:
    return {"schema": "betterinstincts.purchase-dialog-decision/v1", "state": state,
            "reason": reason, "catalog": catalog, "cart": cart, "action": None,
            "execute_allowed": False, "proof_ceiling": PROOF}


def _propose(kind: str, *, catalog: dict | None = None,
             cart: dict | None = None, **fields: Any) -> dict:
    return {"schema": "betterinstincts.purchase-dialog-decision/v1",
            "state": "READY_TO_QUEUE", "reason": None, "catalog": catalog,
            "cart": cart, "action": {"kind": kind, **fields},
            "execute_allowed": False, "proof_ceiling": PROOF}


def _page(page: Mapping[str, Any]) -> tuple[dict | None, str | None]:
    """Validate a *fresh observed* dialog viewport; never infer hidden rows."""
    if not isinstance(page, Mapping):
        return None, "OBSERVED_PAGE_REQUIRED"
    if not all(_valid_id(page.get(x)) for x in ("menu_id", "actor_id", "source", "revision")):
        return None, "MENU_ACTOR_SOURCE_AND_REVISION_REQUIRED"
    scroll = page.get("scroll")
    if (not isinstance(scroll, Mapping) or
            type(scroll.get("at_top")) is not bool or
            type(scroll.get("at_bottom")) is not bool or
            type(scroll.get("verified")) is not bool or
            scroll["verified"] is not True):
        return None, "FRESH_SCROLL_ENDPOINT_OBSERVATION_REQUIRED"
    rows = page.get("rows")
    if not isinstance(rows, (list, tuple)) or not 1 <= len(rows) <= 32:
        return None, "VISIBLE_ROWS_REQUIRED"
    out, ids = [], set()
    for row in rows:
        if not isinstance(row, Mapping):
            return None, "INVALID_VISIBLE_ROW"
        item = row.get("item_id")
        label = row.get("label")
        price = row.get("unit_price")
        count = row.get("selected_count")
        if (not _valid_id(item) or not _valid_id(label) or
                not _nonnegative(price, MAX_PRICE) or
                not _nonnegative(count) or item in ids):
            return None, "INVALID_OR_DUPLICATE_VISIBLE_ROW"
        ids.add(item)
        out.append({"item_id": item, "label": label, "unit_price": price,
                    "selected_count": count, "increment_visible": row.get("increment_visible") is True,
                    "increment_hitbox_verified": row.get("increment_hitbox_verified") is True})
    signature = tuple((r["item_id"], r["label"].casefold().strip(),
                       r["unit_price"]) for r in out)
    return {"menu_id": page["menu_id"], "actor_id": page["actor_id"],
            "source": page["source"], "revision": page["revision"],
            "at_top": scroll["at_top"], "at_bottom": scroll["at_bottom"],
            "rows": out, "signature": signature}, None


def _same_scope(catalog: Mapping[str, Any], view: Mapping[str, Any]) -> bool:
    return all(catalog.get(key) == view[key] for key in ("menu_id", "actor_id", "source"))


def _observed_viewport_span(catalog: Mapping[str, Any], rows: list[dict]) -> tuple[int, int] | None:
    """Locate a fresh viewport by ordered catalog identities, not its old window.

    After scrolling back from an end-clamped page, valid visible rows may form
    a new window. Admit only a contiguous, correctly ordered known subset;
    unknown, rearranged or skipped items must never guide a blind scroll.
    """
    items = catalog.get("items")
    if not isinstance(items, Mapping) or not items:
        return None
    positions = {item_id: i for i, item_id in enumerate(items)}
    try:
        indices = [positions[row["item_id"]] for row in rows]
    except (KeyError, TypeError):
        return None
    if indices != list(range(indices[0], indices[0] + len(indices))):
        return None
    return indices[0], indices[-1]


def _catalog_state(view: Mapping[str, Any]) -> dict:
    return {"menu_id": view["menu_id"], "actor_id": view["actor_id"],
            "source": view["source"], "phase": "SEEK_TOP", "seek": [],
            "pages": [], "items": {}, "complete": False}


def discover_dialog_page(page: Mapping[str, Any], *,
                         catalog: dict | None = None,
                         last_acted_revision: str | None = None) -> dict:
    """Scan top-to-bottom, one verified page at a time, including overlap.

    The first observation may be midway through a list. We must seek top
    before cataloging it, then continue to the observed bottom. A repeated
    viewport or an exhausted bound fails closed instead of blind scrolling.
    """
    view, error = _page(page)
    if error:
        return _hold(error, catalog=catalog)
    if view["revision"] == last_acted_revision:
        return _hold("FRESH_PAGE_REVISION_REQUIRED", catalog=catalog)
    state = _catalog_state(view) if catalog is None else dict(catalog)
    if not _same_scope(state, view):
        return _hold("MENU_OR_SELECTED_PORTRAIT_CHANGED", catalog=catalog)
    if state.get("complete") is True:
        return _hold("CATALOG_ALREADY_COMPLETE", catalog=state, state="COMPLETE")
    if (not isinstance(state.get("pages"), list) or
            not isinstance(state.get("seek"), list) or
            not isinstance(state.get("items"), dict)):
        return _hold("CATALOG_STATE_INVALID", catalog=catalog)
    signature = [list(x) for x in view["signature"]]
    if state.get("phase") == "SEEK_TOP" and not view["at_top"]:
        if (signature in state["seek"] or len(state["seek"]) >= MAX_PAGES):
            return _hold("SCROLL_TO_TOP_STALLED_OR_BOUNDED", catalog=state)
        state["seek"] = [*state["seek"], signature]
        return _propose("SCROLL_UP_ONE_PAGE", catalog=state,
                        revision=view["revision"], menu_id=view["menu_id"],
                        actor_id=view["actor_id"])
    if state.get("phase") not in ("SEEK_TOP", "SCAN_DOWN"):
        return _hold("CATALOG_PHASE_INVALID", catalog=state)
    state["phase"] = "SCAN_DOWN"
    if any(p["signature"] == signature for p in state["pages"]):
        return _hold("SCROLL_DID_NOT_REVEAL_NEW_ROWS", catalog=state)
    if len(state["pages"]) >= MAX_PAGES:
        return _hold("CATALOG_PAGE_BOUND_REACHED", catalog=state)
    items = dict(state["items"])
    for row in view["rows"]:
        item = row["item_id"]
        identity = {"item_id": item, "label": row["label"],
                    "unit_price": row["unit_price"]}
        if item in items and items[item] != identity:
            return _hold("CATALOG_ITEM_IDENTITY_OR_PRICE_CHANGED", catalog=state)
        items[item] = identity
    if len(items) > MAX_ITEMS:
        return _hold("CATALOG_ITEM_BOUND_REACHED", catalog=state)
    state["items"] = items
    state["pages"] = [*state["pages"],
                      {"signature": signature, "item_ids": [r["item_id"] for r in view["rows"]]}]
    if view["at_bottom"]:
        state["complete"] = True
        return _hold("BOTTOM_OF_CATALOG_OBSERVED", catalog=state, state="COMPLETE")
    return _propose("SCROLL_DOWN_ONE_PAGE", catalog=state,
                    revision=view["revision"], menu_id=view["menu_id"],
                    actor_id=view["actor_id"])


def derive_demand(catalog: Mapping[str, Any], activities: list[dict]) -> dict:
    """Translate verified career/garden/repair/craft demands, not menu visibility, into stock gaps."""
    if not isinstance(catalog, Mapping) or catalog.get("complete") is not True:
        return _hold("COMPLETE_OBSERVED_CATALOG_REQUIRED")
    if not isinstance(activities, list) or not activities or len(activities) > MAX_ITEMS:
        return _hold("BOUNDED_ACTIVITY_REQUIREMENTS_REQUIRED")
    requests: dict[str, int] = {}
    for item in activities:
        if not isinstance(item, Mapping) or item.get("kind") not in TRIGGERS:
            return _hold("UNREVIEWED_ACTIVITY_TRIGGER")
        if (item.get("menu_id") != catalog["menu_id"] or
                item.get("actor_id") != catalog["actor_id"] or
                not _valid_id(item.get("evidence_ref"))):
            return _hold("FRESH_ACTIVITY_MENU_ACTOR_EVIDENCE_REQUIRED")
        item_id = item.get("item_id")
        if item_id not in catalog["items"]:
            return _hold("REQUIRED_ITEM_NOT_IN_FULL_CATALOG")
        required, owned = item.get("required"), item.get("owned")
        if not _nonnegative(required) or not _nonnegative(owned):
            return _hold("BOUNDED_REQUIRED_AND_OWNED_COUNTS_REQUIRED")
        gap = max(0, required - owned)
        if requests.get(item_id, 0) + gap > MAX_QTY:
            return _hold("MERGED_DEMAND_QUANTITY_BOUND_EXCEEDED")
        requests[item_id] = requests.get(item_id, 0) + gap
    return {"schema": "betterinstincts.purchase-demand/v1",
            "requests": {k: v for k, v in requests.items() if v},
            "actor_id": catalog["actor_id"], "menu_id": catalog["menu_id"],
            "execute_allowed": False, "proof_ceiling": PROOF}


def propose_dialog_cart_step(
    *, catalog: Mapping[str, Any], page: Mapping[str, Any],
    requests: Mapping[str, int], observed_total_count: int,
    observed_total_cost: int, observed_funds: int, approved_spend_cap: int,
    inventory_before: Mapping[str, int], cart: dict | None = None,
    spending_authorized: bool = False, explicit_command: bool = False,
    player_idle_verified: bool = False, paused_live_verified: bool = False,
    scene_and_actor_verified: bool = False, native_channel_verified: bool = False,
    desktop_fallback_opt_in: bool = False,
    buy_control_visible: bool = False, buy_control_hitbox_verified: bool = False,
    last_acted_revision: str | None = None,
) -> dict:
    """Select at most one observed increment, scroll, or final confirmation.

    No action is executed by this function. A pending increment is committed
    to cart state *only* after its visible row AND global totals are read back.
    """
    view, error = _page(page)
    if error:
        return _hold(error, cart=cart)
    if (not isinstance(catalog, Mapping) or catalog.get("complete") is not True
            or not _same_scope(catalog, view)):
        return _hold("COMPLETE_CATALOG_AND_MATCHING_ACTOR_REQUIRED", cart=cart)
    if (not explicit_command or not spending_authorized):
        return _hold("EXPLICIT_SPENDING_AUTHORIZATION_REQUIRED", cart=cart)
    if not player_idle_verified or not paused_live_verified or not scene_and_actor_verified:
        return _hold("FRESH_PLAYER_SCENE_AND_ACTOR_GUARD_REQUIRED", cart=cart)
    if not (native_channel_verified or desktop_fallback_opt_in):
        return _hold("VERIFIED_CHANNEL_OR_EXPLICIT_FALLBACK_OPT_IN_REQUIRED", cart=cart)
    if view["revision"] == last_acted_revision:
        return _hold("FRESH_PAGE_REVISION_REQUIRED", cart=cart)
    if (not isinstance(requests, Mapping) or not requests or
            any(k not in catalog["items"] or not _nonnegative(v) or v == 0
                for k, v in requests.items())):
        return _hold("POSITIVE_OBSERVED_REQUESTS_REQUIRED", cart=cart)
    if not all(_nonnegative(v, MAX_PRICE * MAX_QTY * MAX_ITEMS) for v in
               (observed_total_cost, observed_funds, approved_spend_cap)):
        return _hold("FRESH_COST_FUNDS_AND_CAP_REQUIRED", cart=cart)
    if not _nonnegative(observed_total_count, MAX_QTY * MAX_ITEMS):
        return _hold("FRESH_TOTAL_COUNT_REQUIRED", cart=cart)
    if (not isinstance(inventory_before, Mapping) or
            any(not _nonnegative(inventory_before.get(k)) for k in requests)):
        return _hold("SELECTED_SIM_INVENTORY_BASELINE_REQUIRED", cart=cart)
    by_id = {r["item_id"]: r for r in view["rows"]}
    for r in view["rows"]:
        if (r["item_id"] not in catalog["items"] or
                catalog["items"][r["item_id"]]["unit_price"] != r["unit_price"] or
                catalog["items"][r["item_id"]]["label"] != r["label"]):
            return _hold("VISIBLE_ROW_NOT_IN_FRESH_CATALOG", cart=cart)
    span = _observed_viewport_span(catalog, view["rows"])
    if span is None:
        return _hold("CURRENT_VIEWPORT_NOT_CATALOGED", cart=cart)
    state = {"selected": {}, "pending": None, "actor_id": view["actor_id"],
             "menu_id": view["menu_id"]} if cart is None else dict(cart)
    if (state.get("actor_id") != view["actor_id"] or
            state.get("menu_id") != view["menu_id"] or
            not isinstance(state.get("selected"), dict)):
        return _hold("CART_ACTOR_OR_MENU_CHANGED", cart=cart)
    selected = dict(state["selected"])
    if any(k not in requests or not _nonnegative(v) for k, v in selected.items()):
        return _hold("CART_SELECTION_INVALID", cart=cart)
    if state.get("pending") is not None:
        pending = state["pending"]
        if not isinstance(pending, Mapping):
            return _hold("CART_PENDING_STATE_INVALID", cart=cart)
        if pending.get("kind") == "CONFIRM_OBSERVED_PURCHASE":
            return _hold("PURCHASE_OUTCOME_REQUIRES_RECONCILIATION",
                         cart=state, state="NEEDS_RECONCILIATION")
        if view["revision"] == pending.get("revision"):
            return _hold("PENDING_EFFECT_REQUIRES_FRESH_READBACK", cart=state)
        if pending.get("kind") in ("SCROLL_UP_ONE_PAGE", "SCROLL_DOWN_ONE_PAGE"):
            before_index = pending.get("from_start_index")
            movement = span[0] - before_index if type(before_index) is int else 0
            if (movement == 0 or
                    (pending["kind"] == "SCROLL_UP_ONE_PAGE" and movement >= 0) or
                    (pending["kind"] == "SCROLL_DOWN_ONE_PAGE" and movement <= 0)):
                return _hold("SCROLL_EFFECT_NOT_RECONCILED",
                             cart=state, state="NEEDS_RECONCILIATION")
        elif pending.get("kind") == "INCREMENT_OBSERVED_ROW":
            pid = pending.get("item_id")
            row = by_id.get(pid)
            if (row is None or row["selected_count"] != pending.get("next_count")
                    or observed_total_count != pending.get("next_total_count")
                    or observed_total_cost != pending.get("next_total_cost")):
                return _hold("PENDING_CART_EFFECT_NOT_RECONCILED",
                             cart=state, state="NEEDS_RECONCILIATION")
            selected[pid] = row["selected_count"]
        else:
            return _hold("CART_PENDING_STATE_INVALID", cart=state)
        state["pending"] = None
    # An observed increment survives subsequent holds (budget/availability).
    state["selected"] = selected
    expected_count = sum(selected.values())
    expected_cost = sum(v * catalog["items"][k]["unit_price"] for k, v in selected.items())
    if (expected_count != observed_total_count or expected_cost != observed_total_cost
            or any(r["selected_count"] != selected.get(r["item_id"], 0)
                   for r in view["rows"])):
        return _hold("CART_TOTALS_OR_VISIBLE_COUNTS_MISMATCH", cart=state)
    planned_cost = sum(count * catalog["items"][pid]["unit_price"]
                       for pid, count in requests.items())
    if (planned_cost > min(observed_funds, approved_spend_cap)
            or expected_cost > planned_cost):
        return _hold("APPROVED_CAP_OR_FUNDS_EXCEEDED", cart=state)
    if any(selected.get(pid, 0) > count for pid, count in requests.items()):
        return _hold("CART_HAS_UNREQUESTED_QUANTITY", cart=state)
    state["selected"] = selected
    for pid in requests:
        if selected.get(pid, 0) >= requests[pid]:
            continue
        if pid in by_id:
            row = by_id[pid]
            if not row["increment_visible"] or not row["increment_hitbox_verified"]:
                return _hold("FRESH_INCREMENT_CONTROL_REQUIRED", cart=state)
            state["pending"] = {
                "kind": "INCREMENT_OBSERVED_ROW", "item_id": pid,
                "revision": view["revision"], "next_count": row["selected_count"] + 1,
                "next_total_count": expected_count + 1,
                "next_total_cost": expected_cost + row["unit_price"],
            }
            return _propose("INCREMENT_OBSERVED_ROW", cart=state, item_id=pid,
                            revision=view["revision"], actor_id=view["actor_id"],
                            expected_selected_count=row["selected_count"],
                            approved_spend_cap=approved_spend_cap)
        target_position = list(catalog["items"]).index(pid)
        if span[0] <= target_position <= span[1]:
            return _hold("TARGET_ITEM_VIEWPORT_UNRESOLVED", cart=state)
        direction = ("SCROLL_UP_ONE_PAGE" if target_position < span[0]
                     else "SCROLL_DOWN_ONE_PAGE")
        if (direction == "SCROLL_UP_ONE_PAGE" and view["at_top"]) or (
                direction == "SCROLL_DOWN_ONE_PAGE" and view["at_bottom"]):
            return _hold("SCROLL_ENDPOINT_CONTRADICTS_TARGET_PAGE", cart=state)
        state["pending"] = {"kind": direction, "revision": view["revision"],
                            "from_start_index": span[0]}
        return _propose(direction, cart=state, revision=view["revision"],
                        actor_id=view["actor_id"], menu_id=view["menu_id"])
    if not buy_control_visible or not buy_control_hitbox_verified:
        return _hold("FRESH_BUY_CONTROL_REQUIRED", cart=state)
    state["pending"] = {"kind": "CONFIRM_OBSERVED_PURCHASE",
                        "revision": view["revision"],
                        "expected_total_cost": planned_cost}
    return _propose("CONFIRM_OBSERVED_PURCHASE", cart=state,
                    revision=view["revision"], actor_id=view["actor_id"],
                    expected_total_count=expected_count, expected_total_cost=planned_cost,
                    approved_spend_cap=approved_spend_cap)


def verify_dialog_purchase(*, catalog: Mapping[str, Any], cart: Mapping[str, Any],
                           requests: Mapping[str, int], inventory_before: Mapping[str, int],
                           inventory_after: Mapping[str, int], funds_before: int,
                           funds_after: int) -> dict:
    """Require exact selected-Sim item deltas and household funds delta."""
    base = _hold("PURCHASE_OUTCOME_UNPROVEN", state="NEEDS_RECONCILIATION")
    if not isinstance(cart, Mapping) or not isinstance(catalog, Mapping):
        return base
    pending = cart.get("pending")
    if (cart.get("actor_id") != catalog.get("actor_id")
            or cart.get("menu_id") != catalog.get("menu_id")):
        return base
    if (not isinstance(pending, Mapping) or
            pending.get("kind") != "CONFIRM_OBSERVED_PURCHASE"):
        return base
    if (not all(isinstance(x, Mapping) for x in
                (requests, inventory_before, inventory_after)) or
            not _nonnegative(funds_before, MAX_PRICE * MAX_QTY * MAX_ITEMS) or
            not _nonnegative(funds_after, MAX_PRICE * MAX_QTY * MAX_ITEMS)):
        return base
    try:
        expected_cost = sum(catalog["items"][k]["unit_price"] * v
                            for k, v in requests.items())
        if (cart.get("selected") != dict(requests)
                or expected_cost != pending.get("expected_total_cost")
                or funds_before - funds_after != expected_cost):
            return base
        if any(not _nonnegative(inventory_before.get(k))
               or not _nonnegative(inventory_after.get(k))
               or inventory_after[k] - inventory_before[k] != count
               for k, count in requests.items()):
            return base
    except (KeyError, TypeError, ValueError):
        return base
    return {"schema": "betterinstincts.purchase-dialog-outcome/v1",
            "state": "PURCHASE_OBSERVED", "actor_id": catalog["actor_id"],
            "menu_id": catalog["menu_id"], "items": dict(requests),
            "spent": expected_cost, "execute_allowed": False, "proof_ceiling": PROOF}


def enqueue_dialog_step(queue: Any, *, work_id: str, decision: Mapping[str, Any],
                        validate_fresh_scene: Callable[[], Awaitable[bool]],
                        perform_game_ui_effect: Callable[[dict], Awaitable[Any]]) -> None:
    """Reuse existing cooperative one-effect checkpoint, never a parallel clicker."""
    from betterinstincts.workflow_interop import CooperativeScreenQueue
    if not isinstance(queue, CooperativeScreenQueue):
        raise ValueError("COOPERATIVE_SCREEN_QUEUE_REQUIRED")
    action = decision.get("action")
    if (decision.get("state") != "READY_TO_QUEUE" or
            not isinstance(action, dict) or action.get("kind") not in ACTIONS or
            not callable(validate_fresh_scene) or not callable(perform_game_ui_effect)):
        raise ValueError("FRESH_WHITELISTED_EFFECT_REQUIRED")

    # Deferred work must never read a caller-owned mutable decision again.
    admitted_action = deepcopy(action)

    async def effect() -> Any:
        return await perform_game_ui_effect(deepcopy(admitted_action))

    queue.enqueue_effect(work_id, validate_fresh_scene, effect)
