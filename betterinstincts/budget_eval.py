"""Host budget + money-stat judgment: secure need objects, earn when broke.

Money is a first-class critical stat when funds are desperate — earn path is
never suppressed by purchase lockdown. Read-only planner; no SendInput.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

from betterinstincts.instincts_host import NEED_OBJECTS, _urgency

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "host-budget.v1.json"
NEEDS = ROOT / "contracts" / "needs.v1.json"
MAX_BYTES = 48_000
SIX = frozenset({"hunger", "bladder", "energy", "hygiene", "fun", "social"})


class BudgetEvalError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise BudgetEvalError("HOST_BUDGET_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.host-budget/v1":
        raise BudgetEvalError("BAD_HOST_BUDGET_SCHEMA")
    floors = cfg.get("floors") or {}
    if not isinstance(floors.get("emergency_reserve"), (int, float)):
        raise BudgetEvalError("EMERGENCY_RESERVE_REQUIRED")
    if not isinstance(floors.get("soft_budget_floor"), (int, float)):
        raise BudgetEvalError("SOFT_BUDGET_FLOOR_REQUIRED")
    if not isinstance(cfg.get("catalog"), list) or not cfg["catalog"]:
        raise BudgetEvalError("BUDGET_CATALOG_REQUIRED")
    return cfg


def _need_cfg() -> dict:
    return json.loads(NEEDS.read_text(encoding="utf-8"))


def money_urgency(funds: float, cfg: Optional[dict] = None) -> str:
    """Treat household funds like a motive band: critical | low | watch | ok."""
    cfg = cfg or load_contract()
    emergency = float(cfg["floors"]["emergency_reserve"])
    soft = float(cfg["floors"]["soft_budget_floor"])
    if funds < emergency:
        return "critical"
    if funds < soft:
        return "low"
    if funds < soft * 2:
        return "watch"
    return "ok"


def _owned_classes(owned: Sequence[str]) -> set[str]:
    return {str(x).lower() for x in owned}


def _class_present(need: str, owned: set[str]) -> bool:
    return any(obj in owned for obj in NEED_OBJECTS[need])


def _cheapest_for_need(need: str, catalog: Sequence[dict]) -> Optional[dict]:
    rows = [
        r for r in catalog
        if isinstance(r, dict) and r.get("need") == need and isinstance(r.get("price"), (int, float))
    ]
    if not rows:
        return None
    return sorted(rows, key=lambda r: (float(r["price"]), str(r.get("id"))))[0]


def evaluate(
    funds: float,
    needs: Mapping[str, float],
    owned_objects: Sequence[str] = (),
    *,
    moodlets: Sequence[str] = (),
    player_directed: bool = False,
    capture_ref: str = "capture:budget",
) -> dict:
    """Plan money-stat + need-object securing. Earn is never blocked by lockdown."""
    if player_directed:
        return {
            "state": "YIELD_PLAYER_PURCHASE_OR_WORK",
            "money_urgency": None,
            "next_gate": "RESPECT_PLAYER_OR_BUSY_STATE",
            "actions": [],
            "proof_ceiling": "PLAYER_FIRST",
        }
    if isinstance(funds, bool) or not isinstance(funds, (int, float)) or funds < 0:
        raise BudgetEvalError("INVALID_FUNDS")
    if set(needs) != SIX:
        raise BudgetEvalError("SIX_NEEDS_REQUIRED")

    cfg = load_contract()
    need_cfg = _need_cfg()
    urgent_t = float(need_cfg["urgency_threshold"])
    preempt_t = float(need_cfg["preemptive_threshold"])
    emergency = float(cfg["floors"]["emergency_reserve"])
    soft = float(cfg["floors"]["soft_budget_floor"])
    spend_max = max(0.0, float(funds) - emergency)
    owned = _owned_classes(owned_objects)
    m_urg = money_urgency(float(funds), cfg)

    gaps = []
    for need in cfg.get("need_object_priority") or list(NEED_OBJECTS):
        level = float(needs[need])
        urg = _urgency(level, urgent_t, preempt_t)
        present = _class_present(need, owned)
        if urg in {"critical", "low"} and not present:
            item = _cheapest_for_need(need, cfg["catalog"])
            price = float(item["price"]) if item else None
            affordable = item is not None and price is not None and price <= spend_max and price > 0
            gaps.append({
                "need": need,
                "urgency": urg,
                "level": level,
                "object_classes": list(NEED_OBJECTS[need]),
                "cheapest": item,
                "affordable": affordable,
            })

    actions = []
    next_gate = "CONTINUE_HOST_LANE"

    # Money is a critical host stat — earn first when desperate, regardless of Buy lockdown.
    if m_urg == "critical":
        actions.append({
            "id": "earn_income_critical",
            "kind": "EARN_BEFORE_SPEND",
            "reason": "MONEY_STAT_CRITICAL",
            "note": "Funds below emergency_reserve — pursue income; do not open luxury Buy.",
        })
        next_gate = "EARN_INCOME_CRITICAL"
    elif m_urg == "low":
        actions.append({
            "id": "earn_income_low",
            "kind": "EARN_BEFORE_SPEND",
            "reason": "MONEY_STAT_LOW",
            "note": "Below soft_budget_floor — prefer earning / using owned objects over new purchases.",
        })
        if next_gate == "CONTINUE_HOST_LANE":
            next_gate = "EARN_BEFORE_SPEND"

    # Secure cheapest adequate only when affordable after reserve.
    for gap in gaps:
        item = gap["cheapest"]
        if gap["affordable"] and item is not None:
            actions.append({
                "id": "secure_" + gap["need"],
                "kind": "SECURE_NEED_OBJECT",
                "need": gap["need"],
                "catalog_id": item.get("id"),
                "object_class": item.get("object_class"),
                "price": item.get("price"),
                "reason": "NEED_OBJECT_GAP_AFFORDABLE",
            })
            if next_gate in {"CONTINUE_HOST_LANE", "EARN_BEFORE_SPEND"} and m_urg != "critical":
                next_gate = "SECURE_NEED_OBJECT"
        else:
            actions.append({
                "id": "hold_" + gap["need"],
                "kind": "HOLD_PURCHASE",
                "need": gap["need"],
                "reason": "UNAFFORDABLE_OR_NO_CATALOG",
                "fallback": "USE_OWNED_OR_MAP_TRAVEL_OR_EARN",
            })
            if m_urg != "critical" and next_gate == "CONTINUE_HOST_LANE":
                next_gate = "HOLD_PURCHASE_EARN_OR_TRAVEL"

    if float(funds) < emergency:
        actions.append({
            "id": "budget_lockdown",
            "kind": "BUDGET_LOCKDOWN",
            "reason": "BELOW_EMERGENCY_RESERVE",
            "note": "Block discretionary Buy; earn path remains mandatory.",
        })
        # Lockdown never cancels EARN_INCOME_CRITICAL.
        if next_gate not in {"EARN_INCOME_CRITICAL", "SECURE_NEED_OBJECT"}:
            next_gate = "BUDGET_LOCKDOWN_EARN"

    # Free moodlet relief hint (no spend).
    if moodlets and m_urg in {"critical", "low"}:
        actions.append({
            "id": "prefer_free_mood_relief",
            "kind": "FREE_MOODLET_RELIEF",
            "moodlets": list(moodlets)[:8],
            "reason": "AVOID_PAID_MOOD_FIX_WHILE_BROKE",
        })

    return {
        "state": "BUDGET_EVALUATED",
        "funds": float(funds),
        "money_urgency": m_urg,
        "emergency_reserve": emergency,
        "soft_budget_floor": soft,
        "spend_max": spend_max,
        "gaps": gaps,
        "actions": actions,
        "next_gate": next_gate,
        "owned_objects": sorted(owned),
        "capture_ref": capture_ref,
        "proof_ceiling": cfg.get("proof_ceiling"),
        "invariants": {
            "earn_never_blocked_by_lockdown": True,
            "player_first": True,
            "no_spend_below_emergency_reserve": True,
        },
    }
