"""Receipt-backed economics for game-native robotics craft-and-sell work.

Read-only: the exact-build adapter owns observations and persists its receipts.
Household balance changes, cash recovery and inventory valuations are not sales.
"""
from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction

from betterinstincts.budget_eval import household_reserve
from betterinstincts.funds_inject import MAX_HOUSEHOLD_FUNDS

SCHEMA = "betterinstincts.robotics-income/v1"
MAX_RECIPES = 24
MAX_RECEIPTS = 32
MAX_MATERIALS = 16
MAX_MINUTES = 10_080  # One Sim week of active sourcing, crafting and selling.
SCOPE_KEYS = ("household_ref", "game_build", "save_ref")


class RoboticsIncomeError(ValueError):
    pass


def _ref(value: object) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 120 and all(
        c.isalnum() or c in "_.:-" for c in value
    )


def _amount(value: object, maximum: int = MAX_HOUSEHOLD_FUNDS) -> bool:
    return type(value) is int and 0 <= value <= maximum


def _rows(raw: object, limit: int) -> list[Mapping]:
    if not isinstance(raw, list) or len(raw) > limit or any(not isinstance(r, Mapping) for r in raw):
        raise RoboticsIncomeError("ROBOTICS_OBSERVATION_BOUNDS")
    return raw


def _key(row: Mapping) -> tuple[str, str]:
    recipe, channel = row.get("recipe_ref"), row.get("sale_channel")
    if not _ref(recipe) or not _ref(channel):
        raise RoboticsIncomeError("ROBOTICS_RECIPE_OR_CHANNEL_REQUIRED")
    return recipe, channel


def _ingredients(row: Mapping) -> Mapping:
    parts = row.get("ingredients")
    if (not isinstance(parts, Mapping) or not 1 <= len(parts) <= MAX_MATERIALS
            or any(not _ref(k) or not _amount(v, 1000) or v == 0 for k, v in parts.items())):
        raise RoboticsIncomeError("ROBOTICS_INGREDIENTS_INVALID")
    return parts


def _material_cost(row: Mapping, *, quote: bool, allow_partial: bool = False) -> tuple[int, int] | None:
    """Price consumed units once. Purchased units contribute to cash requirement too."""
    parts = _ingredients(row)
    materials = row.get("materials")
    if not isinstance(materials, Mapping) or not set(materials) <= set(parts):
        raise RoboticsIncomeError("ROBOTICS_MATERIALS_INVALID")
    if set(materials) != set(parts):
        return None
    total = cash = 0
    for part, value in materials.items():
        expected = parts[part]
        if not isinstance(value, Mapping):
            raise RoboticsIncomeError("ROBOTICS_MATERIAL_COST_INVALID")
        if quote:
            purchased = value.get("buy_quantity")
            if not _amount(purchased, expected):
                return None
            quantity = expected - purchased
            owned_price = value.get("owned_unit_cost")
            # A free source needs evidence too, even for already-owned stock.
            if quantity and (not _amount(owned_price) or not _ref(value.get("basis_ref"))
                             or not _ref(value.get("stock_ref"))):
                return None
            purchase_price = value.get("buy_unit_cost")
            if purchased and (not _amount(purchase_price) or not _ref(value.get("price_ref"))):
                return None
            debit = purchased * purchase_price if purchased else 0
            cash += debit
            total += debit + (quantity * owned_price if quantity else 0)
        else:
            quantity = value.get("consumed_quantity")
            if not _amount(quantity, expected) or (not allow_partial and quantity != expected):
                return None
            consumed_cost = value.get("consumed_cost")
            if (not _amount(consumed_cost) or not _ref(value.get("basis_ref"))
                    or (not quantity and consumed_cost)):
                return None
            total += consumed_cost
    return total, cash


def _terminal(row: Mapping) -> tuple[tuple[str, ...], int, int, int] | None:
    state = row.get("outcome")
    if state not in ("SOLD", "FAILED"):
        return None
    required_refs = ("attempt_ref", "native_action_ref", "debit_ref", "terminal_ref")
    if state == "SOLD":
        required_refs += ("item_ref", "sale_ref")
    refs = tuple(row.get(k) for k in required_refs)
    if not all(_ref(r) for r in refs) or len(set(refs)) != len(refs):
        return None
    if (row.get("origin") != "NATIVE_RESPONDER" or row.get("attributed") is not True
            or not _amount(row.get("workstation_fee"))
            or not _amount(row.get("other_costs"))
            or not _amount(row.get("minutes"), MAX_MINUTES) or row["minutes"] == 0):
        return None
    # Only a linked paid sale can contribute revenue. Failed attempts carry no proceeds.
    proceeds = row.get("payout")
    if not _amount(proceeds) or (state == "FAILED" and proceeds != 0):
        return None
    material = _material_cost(row, quote=False, allow_partial=state == "FAILED")
    if material is None:
        return None
    cost = row["workstation_fee"] + material[0] + row["other_costs"]
    return refs, proceeds, cost, row["minutes"]


def _cohorts(raw: object, scope: tuple[str, str, str]) -> dict:
    runs: dict[tuple[str, str], list[tuple[int, int, int, str, Mapping]]] = {}
    blocked: set[tuple[str, str]] = set()
    by_proof: dict[str, list[Mapping]] = {}
    pending: list[Mapping] = []
    for row in _rows(raw, MAX_RECEIPTS):
        if tuple(row.get(k) for k in SCOPE_KEYS) != scope:
            continue
        key = _key(row)
        if row.get("origin") != "NATIVE_RESPONDER":
            continue
        if row.get("outcome") in ("IN_FLIGHT", "UNSOLD"):
            pending.append(row)
            continue
        proof = _terminal(row)
        if proof is None:
            blocked.add(key)  # Open/partial attempt must be reconciled before a retry.
            continue
        refs, cash_in, cost, minutes = proof
        if row in by_proof.get(refs[0], ()):
            continue
        for ref in refs:
            owners = by_proof.setdefault(ref, [])
            if owners:
                blocked.add(key)
                blocked.update(_key(old) for old in owners)
            owners.append(row)
        runs.setdefault(key, []).append((cash_in, cost, minutes, refs[0], row["ingredients"]))
    for row in pending:
        attempt = row.get("attempt_ref")
        candidates = by_proof.get(attempt, ()) if _ref(attempt) else ()
        key = _key(row)
        if len(candidates) != 1:
            blocked.add(key)
            continue
        terminal = candidates[0]
        if (key != _key(terminal) or attempt != terminal.get("attempt_ref")
                or row.get("native_action_ref") != terminal.get("native_action_ref")
                or (row.get("outcome") == "UNSOLD" and (
                    not _ref(row.get("item_ref")) or row["item_ref"] != terminal.get("item_ref")))):
            blocked.add(key)
    return runs, blocked


def evaluate_robotics_income(observation: Mapping, *, household_ref: str,
                             game_build: str, save_ref: object, capture_ref: str) -> dict:
    """Compare bounded recipe cohorts; return ranked advice and full accounting."""
    if (not isinstance(observation, Mapping) or observation.get("schema") != SCHEMA
            or not _ref(save_ref)
            or tuple(observation.get(k) for k in (*SCOPE_KEYS, "capture_ref"))
            != (household_ref, game_build, save_ref, capture_ref)
            or not _amount(observation.get("available_funds"))
            or not _ref(observation.get("funds_proof_ref"))):
        raise RoboticsIncomeError("ROBOTICS_SCOPE_OR_CURRENT_FUNDS_UNVERIFIED")
    runs, blocked = _cohorts(observation.get("receipts"), (household_ref, game_build, save_ref))
    reserve = household_reserve(observation["available_funds"])
    offers = {}
    for row in _rows(observation.get("offers"), MAX_RECIPES):
        key = _key(row)
        action, sim = row.get("action_id"), row.get("sim_ref")
        if (not _ref(action) or not _ref(sim) or action in offers.get(sim, {})
                or row.get("capture_ref") != capture_ref
                or not _ref(row.get("quote_ref"))):
            raise RoboticsIncomeError("ROBOTICS_OFFER_IDENTITY_INVALID")
        samples = runs.get(key, ())
        count = len(samples)
        revenue = sum(v[0] for v in samples)
        realized_cost = sum(v[1] for v in samples)
        net = revenue - realized_cost
        minutes = sum(v[2] for v in samples)
        offer = {
            "action_id": action, "sim_ref": sim,
            "recipe_ref": key[0], "sale_channel": key[1],
            "sample_count": count, "realized_revenue": revenue, "realized_cost": realized_cost,
            "realized_net": net, "attempt_refs": sorted(v[3] for v in samples),
            "observed_active_minutes": minutes, "full_unit_cost": None, "upfront_cash": None,
            "projected_net_per_attempt": None, "projected_net_per_sim_hour": None,
            "income_yield": None, "state": "REOBSERVE_FULL_COST",
        }
        offers.setdefault(sim, {})[action] = offer
        if key in blocked or any(v[4] != _ingredients(row) for v in samples):
            offer.update(state="RECONCILE_NATIVE_RECEIPTS", realized_revenue=None,
                         realized_cost=None, realized_net=None)
            continue
        if not _amount(row.get("workstation_fee")) or not _amount(row.get("other_costs")):
            continue
        material = _material_cost(row, quote=True)
        if material is None:
            continue
        common_cost = row["workstation_fee"] + row["other_costs"]
        cost, cash = common_cost + material[0], common_cost + material[1]
        offer.update(full_unit_cost=cost, upfront_cash=cash)
        if not count:
            offer["state"] = "OBSERVE_NATIVE_SALE_OR_FAILURE"
            continue
        # Price the current mix and include failed attempts with zero revenue.
        # The weaker of realized and current economics is the upper limit on advice.
        conservative_net = min(net, revenue - count * cost)
        rate = Fraction(60 * conservative_net, minutes)
        offer.update(projected_net_per_attempt=float(Fraction(conservative_net, count)),
                     projected_net_per_sim_hour=float(rate))
        if conservative_net <= 0:
            offer["state"] = "HOLD_NONPOSITIVE_NET"
        elif cash > reserve["spend_max"]:
            offer["state"] = "HOLD_HOUSEHOLD_RESERVE"
        else:
            # Map §/Sim-hour into the existing [0, 1] domain yield; §60/h gives 0.5.
            offer.update(state="POSITIVE_NET_CANDIDATE",
                         income_yield=float(rate / (rate + 60)))
    return {"offers": offers, "minimum_household_balance": reserve["minimum_household_balance"],
            "proof_ceiling": "SUPPLIED_NATIVE_RECEIPT_ECONOMICS_ONLY"}
