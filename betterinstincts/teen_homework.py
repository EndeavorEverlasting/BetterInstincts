"""Teen High School Student daily homework — host career-performance budget.

Offline / host planning only. Never invents inventory or lot contents.
When inventory omits homework, lot-scan surfaces before computer recovery.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping, Optional, Sequence

from betterinstincts.queue_capacity import QueueCapacityError, evaluate_queue_capacity
from betterinstincts.study_space import evaluate_study_space

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "teen-homework.v1.json"
SIX = frozenset({"hunger", "bladder", "energy", "hygiene", "fun", "social"})
SURVIVAL = frozenset({"hunger", "bladder", "energy"})
SURVIVAL_THRESHOLD = 0.35
NEEDS_QUEUE_HINTS = (
    "use toilet",
    "take a shower",
    "shower",
    "bathe",
    "eat",
    "sleep",
    "nap",
    "drink",
    "brush teeth",
)
LOT_SCAN_ROUTE = "LOT_SCAN_PUT_HOMEWORK_IN_INVENTORY"


class TeenHomeworkError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 256000:
        raise TeenHomeworkError("UNSAFE_TEEN_HOMEWORK_CONTRACT")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.teen-homework/v1":
        raise TeenHomeworkError("INVALID_TEEN_HOMEWORK_SCHEMA")
    ladder = data.get("recovery_ladder", {}).get("order") or []
    if not ladder:
        raise TeenHomeworkError("TEEN_HOMEWORK_RECOVERY_LADDER_EMPTY")
    return data


def _norm(text: str) -> str:
    s = str(text or "").strip().lower().replace("_", " ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _needs(raw: Mapping[str, float]) -> dict[str, float]:
    if set(raw) != SIX:
        raise TeenHomeworkError("SIX_NEEDS_REQUIRED")
    out = {}
    for k, v in raw.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0 <= float(v) <= 1):
            raise TeenHomeworkError("INVALID_NEED")
        out[k] = float(v)
    return out


def survival_critical(needs: Mapping[str, float], *, threshold: float = SURVIVAL_THRESHOLD) -> list[str]:
    snap = _needs(needs)
    return sorted(n for n in SURVIVAL if snap[n] < threshold)


def premises_block_homework(
    *,
    location_kind: str,
    school_day_active: bool,
    sim_at_school: Optional[bool] = None,
) -> bool:
    if sim_at_school is True:
        return True
    return school_day_active or location_kind == "school"


def homework_tokens_in_objects(
    available_objects: Sequence[str],
    cfg: Optional[dict] = None,
) -> list[str]:
    """Return normalized object labels that match homework tokens (supplied observation only)."""
    cfg = cfg or load_contract()
    tokens = [_norm(t) for t in (cfg.get("lot_scan", {}).get("object_tokens") or [])]
    hits: list[str] = []
    for raw in available_objects:
        label = _norm(raw)
        if not label:
            continue
        if any(tok and (tok in label or label in tok) for tok in tokens):
            hits.append(label)
    return hits


def resolve_homework_on_lot(
    *,
    homework_on_lot: Optional[bool],
    available_objects: Sequence[str] = (),
    cfg: Optional[dict] = None,
) -> tuple[Optional[bool], list[str]]:
    """Combine explicit homework_on_lot with available_objects hits. Never invents True."""
    hits = homework_tokens_in_objects(available_objects, cfg)
    if homework_on_lot is True:
        return True, hits
    if homework_on_lot is False and not hits:
        return False, hits
    if hits:
        return True, hits
    return homework_on_lot, hits


def recovery_plan(
    cfg: Optional[dict] = None,
    *,
    homework_on_lot: Optional[bool] = None,
) -> list[dict]:
    cfg = cfg or load_contract()
    ladder = cfg.get("recovery_ladder", {}).get("order") or []
    rows = [
        {
            "id": step["id"],
            "labels": list(step.get("labels", [])),
            "steps": list(step.get("steps", [])),
            "requires_book_present": bool(step.get("requires_book_present", False)),
            "confidence": step.get("confidence", "HOST_HEURISTIC"),
        }
        for step in ladder
    ]
    if homework_on_lot is False:
        # Confirmed absent from lot — skip lot-scan put-in-inventory.
        rows = [r for r in rows if r["id"] != LOT_SCAN_ROUTE]
    return rows


def queue_homework_actions(cfg: Optional[dict] = None) -> list[dict]:
    cfg = cfg or load_contract()
    rows = cfg.get("queue_homework", {}).get("inventory_present") or []
    return [
        {
            "id": row["id"],
            "labels": list(row.get("labels", [])),
            "steps": list(row.get("steps", [])),
            "confidence": row.get("confidence", "HOST_HEURISTIC"),
        }
        for row in rows
    ]


def _queue_has_needs_work(queue: Sequence[str]) -> bool:
    for raw in queue:
        needle = _norm(raw)
        if not needle:
            continue
        for hint in NEEDS_QUEUE_HINTS:
            if hint in needle or needle in hint:
                return True
    return False


def _queue_has_homework(queue: Sequence[str]) -> bool:
    for raw in queue:
        if "homework" in _norm(raw):
            return True
    return False


def _pick_gate(
    *,
    player_directed: bool,
    already_busy: bool,
    survival: list[str],
    premises_blocked: bool,
    location_kind: str,
    homework_pending: bool,
    inventory_has_homework: Optional[bool],
    homework_on_lot: Optional[bool],
    queue: Sequence[str],
    study_space: Mapping,
    queue_budget: Mapping,
    sim_room_id: Optional[str],
    sim_seated: Optional[bool],
    sim_seat_id: Optional[str],
) -> tuple[str, str, list[dict], list[str]]:
    cfg = load_contract()
    gates = cfg["call_stack"]["gates"]
    findings: list[str] = []
    next_actions: list[dict] = []

    if player_directed or already_busy:
        row = gates["PLAYER_FIRST_OR_BUSY"]
        return "PLAYER_FIRST_OR_BUSY", row["action"], next_actions, findings

    if survival:
        row = gates["SURVIVAL_BEFORE_HOMEWORK"]
        findings.append("SURVIVAL_OUTRANKS_TEEN_HOMEWORK")
        return "SURVIVAL_BEFORE_HOMEWORK", row["action"], next_actions, findings

    if homework_pending and premises_blocked:
        row = gates["HOMEWORK_PREMISES_BLOCKED"]
        findings.append("TEEN_HOMEWORK_DEFERRED_ON_PREMISES")
        return "HOMEWORK_PREMISES_BLOCKED", row["action"], next_actions, findings

    if (
        homework_pending
        and location_kind == "home"
        and not survival
        and queue
        and _queue_has_needs_work(queue)
        and not _queue_has_homework(queue)
    ):
        row = gates["HOMEWORK_AFTER_NEEDS_QUEUE"]
        findings.append("NEEDS_QUEUE_BEFORE_HOMEWORK")
        return "HOMEWORK_AFTER_NEEDS_QUEUE", row["action"], next_actions, findings

    if (
        homework_pending
        and location_kind == "home"
        and inventory_has_homework is False
        and not survival
    ):
        row = gates["HOMEWORK_INVENTORY_MISSING"]
        next_actions = recovery_plan(cfg, homework_on_lot=homework_on_lot)
        findings.append("HOMEWORK_BOOK_NOT_IN_INVENTORY")
        if homework_on_lot is not False:
            findings.append("LOT_SCAN_BEFORE_COMPUTER_RECOVERY")
        if homework_on_lot is True:
            findings.append("HOMEWORK_OBSERVED_ON_LOT")
        return "HOMEWORK_INVENTORY_MISSING", row["action"], next_actions, findings

    if (
        homework_pending
        and location_kind == "home"
        and inventory_has_homework is True
        and not survival
    ):
        if _queue_has_homework(queue):
            row = gates["HOMEWORK_ALREADY_QUEUED"]
            findings.append("DO_NOT_DUPLICATE_HOMEWORK")
            return "HOMEWORK_ALREADY_QUEUED", row["action"], [], findings
        if study_space["state"] != "STUDY_LOCATION_CANDIDATE":
            row = gates["HOMEWORK_STUDY_SCAN_REQUIRED"]
            findings.append("NO_ATTESTED_SEATED_STUDY_OPPORTUNITY")
            next_actions = [{
                "id": "SCAN_LOT_FOR_STUDY_STATION",
                "steps": ["READ_REVISIONED_LOT_MODEL",
                          "LOCATE_ATTESTED_INDOOR_DESK_OR_TABLE",
                          "LOCATE_ASSOCIATED_SEAT",
                          "REOBSERVE_STUDY_CANDIDATE"],
                "confidence": "READ_ONLY_ADVISORY_NO_CONTROL_PERMIT",
            }]
            return "HOMEWORK_STUDY_SCAN_REQUIRED", row["action"], next_actions, findings
        if not queue_budget["enqueue_allowed"]:
            row = gates["HOMEWORK_QUEUE_CAPACITY_HOLD"]
            findings.append("QUEUE_HAS_NO_VERIFIED_BUDGET")
            return "HOMEWORK_QUEUE_CAPACITY_HOLD", row["action"], [], findings
        if (sim_room_id != study_space["room_id"]
                or sim_seated is not True
                or sim_seat_id != study_space["seat_id"]):
            row = gates["PREPARE_STUDY_LOCATION"]
            next_actions = [{
                "id": "MOVE_TO_STUDY_SEAT",
                "steps": ["OBSERVE_CURRENT_SIM_POSITION", "SELECT_OBSERVED_STUDY_SEAT",
                          "REOBSERVE_SEATED_IN_TARGET_ROOM"],
                "room_id": study_space["room_id"],
                "surface_id": study_space["surface_id"],
                "seat_id": study_space["seat_id"],
                "confidence": "HOST_HEURISTIC_NO_CONTROL_PERMIT",
            }]
            findings.append("STUDY_SEAT_BEFORE_HOMEWORK")
            return "PREPARE_STUDY_LOCATION", row["action"], next_actions, findings
        row = gates["QUEUE_TEEN_HOMEWORK"]
        next_actions = queue_homework_actions(cfg)
        findings.append("STUDY_SEAT_ATTESTED_BEFORE_HOMEWORK")
        return "QUEUE_TEEN_HOMEWORK", row["action"], next_actions, findings

    row = gates["LEISURE_OR_IDLE"]
    return "LEISURE_OR_IDLE", row["action"], next_actions, findings


def evaluate_teen_homework_turn(
    needs: Mapping[str, float],
    *,
    location_kind: str = "unknown",
    school_day_active: bool = False,
    homework_pending: bool = False,
    inventory_has_homework: Optional[bool] = None,
    homework_on_lot: Optional[bool] = None,
    available_objects: Sequence[str] = (),
    sim_at_school: Optional[bool] = None,
    queue: Sequence[str] = (),
    player_directed: bool = False,
    already_busy: bool = False,
    life_stage: str = "teen",
    lot_model: Optional[Mapping] = None,
    multitasking: Optional[bool] = None,
    sim_room_id: Optional[str] = None,
    sim_seated: Optional[bool] = None,
    sim_seat_id: Optional[str] = None,
    emotion: Optional[str] = None,
    lot_traits: Sequence[str] = (),
    capture_ref: str = "capture:teen-homework-turn",
) -> dict:
    """Return the highest-priority teen homework call-stack gate for one turn."""
    cfg = load_contract()
    snap = _needs(needs)
    survival = survival_critical(snap)
    premises_blocked = premises_block_homework(
        location_kind=location_kind,
        school_day_active=school_day_active,
        sim_at_school=sim_at_school,
    )
    resolved_on_lot, lot_hits = resolve_homework_on_lot(
        homework_on_lot=homework_on_lot,
        available_objects=available_objects,
        cfg=cfg,
    )
    try:
        queue_budget = evaluate_queue_capacity(
            queue, multitasking=multitasking, player_directed=player_directed
        )
        study_space = evaluate_study_space(
            lot_model, emotion=emotion, lot_traits=lot_traits
        )
    except (QueueCapacityError, ValueError) as exc:
        raise TeenHomeworkError(str(exc)) from exc
    gate, action, next_actions, findings = _pick_gate(
        player_directed=player_directed,
        already_busy=already_busy,
        survival=survival,
        premises_blocked=premises_blocked,
        location_kind=location_kind,
        homework_pending=homework_pending,
        inventory_has_homework=inventory_has_homework,
        homework_on_lot=resolved_on_lot,
        queue=queue,
        study_space=study_space,
        queue_budget=queue_budget,
        sim_room_id=sim_room_id,
        sim_seated=sim_seated,
        sim_seat_id=sim_seat_id,
    )
    owns_home = life_stage == "teen" or inventory_has_homework is not None
    preferred_routes = [str(a["id"]) for a in next_actions]
    return {
        "schema": "betterinstincts.teen-homework-result/v1",
        "state": "TEEN_HOMEWORK_TURN_EVALUATED",
        "capture_ref": capture_ref,
        "gate": gate,
        "action": action,
        "disposition": "OPTIMIZE" if gate == "SURVIVAL_BEFORE_HOMEWORK" else "EMULATE_THEN_OPTIMIZE",
        "preferred_routes": preferred_routes,
        "primary_route": preferred_routes[0] if preferred_routes else None,
        "next_actions": next_actions,
        "findings": sorted(set(findings)),
        "survival_critical": survival,
        "homework_pending": homework_pending,
        "inventory_has_homework": inventory_has_homework,
        "homework_on_lot": resolved_on_lot,
        "lot_homework_hits": lot_hits,
        "queue_budget": queue_budget,
        "study_space": study_space,
        "sim_room_id": sim_room_id,
        "sim_seated": sim_seated,
        "sim_seat_id": sim_seat_id,
        "life_stage": life_stage,
        "location_kind": location_kind,
        "school_day_active": school_day_active,
        "sim_at_school": sim_at_school,
        "homework_blocked_on_premises": premises_blocked,
        "owns_home_homework": owns_home and location_kind == "home",
        "call_stack_order": list(cfg["call_stack"]["order"]),
        "proof_ceiling": cfg["proof_ceiling"],
    }


def should_attach_teen_homework(
    *,
    homework_pending: bool,
    inventory_has_homework: Optional[bool],
    life_stage: Optional[str],
) -> bool:
    if not (homework_pending or inventory_has_homework is False):
        return False
    return life_stage == "teen" or inventory_has_homework is not None or inventory_has_homework is False
