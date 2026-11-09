"""Needs-first gardening behavior, composed by the existing host stack.

Consumes current observed interactions, not item-type guesses. A deferred goal
survives needs recovery and responsibility windows. Never queues UI or builds.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Mapping

from betterinstincts.need_service_base import normalize_needs, threshold_pair
from betterinstincts.task_continuity import TaskContinuityError, evaluate_task_continuity

CONTRACT = Path(__file__).resolve().parents[1] / "contracts/gardening-service.v1.json"


class GardeningServiceError(ValueError):
    pass


def load_contract() -> dict:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.gardening-service/v1":
        raise GardeningServiceError("GARDENING_CONTRACT_INVALID")
    return data


def _number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _text(value: object, limit: int = 160) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit and all(
        ord(char) >= 32 for char in value
    )


def _observed_actions(context: Mapping, capture_ref: str, limit: int) -> list[dict]:
    rows = context.get("observed_actions", [])
    if not isinstance(rows, list) or len(rows) > limit:
        raise GardeningServiceError("GARDENING_OBSERVED_ACTIONS_INVALID")
    actions = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise GardeningServiceError("GARDENING_ACTION_NOT_OBJECT")
        if (
            row.get("available") is True
            and row.get("capture_ref") == capture_ref
            and _text(row.get("action_id"), 64)
            and _text(row.get("label"), 80)
            and _text(row.get("target_ref"))
        ):
            actions.append({key: row[key] for key in (
                "action_id", "label", "target_ref", "capture_ref"
            )})
    return actions


def evaluate_gardening_turn(
    needs: Mapping[str, float],
    need_report: Mapping,
    context: Mapping,
    *,
    capture_ref: str,
    player_directed: bool = False,
    already_busy: bool = False,
    sim_absent: bool = False,
    build_or_buy_mode: bool = False,
    school_day_active: bool = False,
    homework_pending: bool = False,
    now: float | None = None,
) -> dict:
    """Select one currently observed action or an executable inspection query.

    The caller supplies the same needs-service result used for its normal turn;
    this module neither reruns that service nor replaces its policy/thresholds.
    """
    if not isinstance(context, Mapping) or not isinstance(need_report, Mapping):
        raise GardeningServiceError("GARDENING_CONTEXT_INVALID")
    cfg = load_contract()
    bounds = cfg["bounds"]
    snap = normalize_needs(needs)
    _, floor = threshold_pair()
    result = {
        "schema": "betterinstincts.gardening-result/v1",
        "goal": "PLANT_AND_MAINTAIN_GARDEN",
        "goal_state": "PENDING",
        "capture_ref": capture_ref,
        "next_actions": [],
        "inspection_targets": [],
        "needs_gate": need_report.get("gate"),
        "activity_window_sim_minutes": bounds["activity_window_sim_minutes"],
        "dispatch_authorized": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }
    continuity = None
    if "task_continuity" in context:
        try:
            continuity = evaluate_task_continuity(
                context["task_continuity"], capture_ref=capture_ref, now=now
            )
        except TaskContinuityError as exc:
            raise GardeningServiceError(str(exc)) from exc
        result["task_continuity"] = continuity

    def finish(gate: str, action: str, *, inspections: tuple[str, ...] = ()) -> dict:
        result.update(gate=gate, action=action, inspection_targets=list(inspections))
        return result

    if player_directed:
        return finish("GARDEN_PLAYER_FIRST", "YIELD_WITH_GOAL_PRESERVED")
    if already_busy:
        if continuity is not None and continuity["gate"] == "AUTONOMOUS_TASK_INTERRUPTION":
            return finish("GARDEN_AUTONOMOUS_INTERRUPTION", "WAIT_REOBSERVE_UNSOLICITED_ACTIVITY")
        if continuity is not None and continuity["gate"] == "TASK_ALREADY_QUEUED":
            return finish("GARDEN_TASK_ALREADY_QUEUED", "DO_NOT_DUPLICATE_QUEUE")
        return finish("GARDEN_PLAYER_FIRST", "YIELD_WITH_GOAL_PRESERVED")
    if build_or_buy_mode:
        return finish("GARDEN_LIVE_MODE_REQUIRED", "RETURN_TO_OBSERVED_LIVE_CONTEXT")
    if sim_absent or school_day_active:
        return finish("GARDEN_RESPONSIBILITY_FIRST", "PRESERVE_ATTENDANCE")

    stamp = context.get("observed_at_unix")
    at = time.time() if now is None else now
    if (
        not _number(stamp) or not _number(at)
        or not 0 <= at - stamp <= bounds["max_capture_age_seconds"]
        or context.get("capture_ref") != capture_ref
        or need_report.get("capture_ref") != capture_ref
        or context.get("scene_verified") is not True
        or context.get("queue_verified") is not True
    ):
        return finish("GARDEN_REOBSERVE", "INSPECT_CURRENT_STATE", inspections=(
            "LIVE_SCENE", "NEEDS_PANEL", "PLAYER_QUEUE", "PLANT_INTERACTIONS"
        ))
    actions = _observed_actions(context, capture_ref, bounds["max_observed_actions"])
    low = [need for need, value in snap.items() if value < floor]
    if low:
        result["needs_below_floor"] = sorted(low)
        # A predicted type-based route is never enough to queue a remedy. It
        # must match an actually available interaction in this same capture.
        primary = need_report.get("primary_route")
        observed = next((row for row in actions if row["action_id"] == primary), None)
        if observed is not None:
            result["next_actions"] = [observed]
            return finish("GARDEN_RECOVER_NEEDS", "EXECUTE_OBSERVED_NEED_REMEDY")
        return finish("GARDEN_INSPECT_NEED_ACTIONS", "INSPECT_EXISTING_NEED_INTERACTIONS", inspections=(
            "CURRENT_LOT_NEED_INTERACTIONS", "SIM_INVENTORY_NEED_INTERACTIONS"
        ))
    if homework_pending:
        return finish("GARDEN_RESPONSIBILITY_FIRST", "FINISH_HOMEWORK_BEFORE_GARDENING")
    if context.get("responsibilities_checked") is not True:
        return finish("GARDEN_INSPECT_RESPONSIBILITIES", "READ_CURRENT_RESPONSIBILITIES", inspections=(
            "SCHOOL_OR_CAREER_PANEL", "CURRENT_DAILY_TASK", "NEXT_ATTENDANCE_TIME"
        ))
    minutes = context.get("minutes_until_obligation")
    if minutes is None:
        if context.get("no_upcoming_obligation") is not True:
            return finish("GARDEN_INSPECT_RESPONSIBILITIES", "READ_NEXT_OBLIGATION_TIME", inspections=(
                "NEXT_ATTENDANCE_TIME",
            ))
    elif not _number(minutes) or minutes < 0:
        raise GardeningServiceError("GARDENING_OBLIGATION_TIME_INVALID")
    elif minutes <= bounds["activity_window_sim_minutes"] + bounds["responsibility_reserve_sim_minutes"]:
        return finish("GARDEN_RESPONSIBILITY_FIRST", "KEEP_TIME_FOR_NEXT_OBLIGATION")
    if continuity is not None:
        gate = continuity["gate"]
        if gate in {"PLAYER_CHANGED_GOAL", "PLAYER_CHANGED_QUEUE"}:
            return finish("GARDEN_PLAYER_FIRST", "YIELD_WITH_GOAL_PRESERVED")
        if gate == "TASK_VERIFIED_COMPLETE":
            result["goal_state"] = "VERIFIED_COMPLETE"
            return finish("GARDEN_TASK_VERIFIED_COMPLETE", "NO_FURTHER_QUEUE")
        if gate == "TASK_ALREADY_QUEUED":
            return finish("GARDEN_TASK_ALREADY_QUEUED", "DO_NOT_DUPLICATE_QUEUE")
        if gate == "AUTONOMOUS_TASK_INTERRUPTION":
            return finish("GARDEN_AUTONOMOUS_INTERRUPTION", "WAIT_REOBSERVE_UNSOLICITED_ACTIVITY")
        if gate != "TASK_RESUME_CANDIDATE":
            return finish("GARDEN_REOBSERVE_TASK", "INSPECT_CURRENT_QUEUE_AND_ACTOR")
        target = continuity["next_target_ref"]
        selected = next((row for row in actions if
                         row["action_id"] == continuity["action_id"] and
                         row["target_ref"] == target), None)
        if selected is None:
            return finish("GARDEN_INSPECT_TASK_TARGET", "INSPECT_EXACT_PENDING_PLANT", inspections=(target,))
        result["next_actions"] = [selected]
        result["goal_state"] = "READY_FOR_ONE_OBSERVED_INTERACTION"
        return finish("GARDEN_ACTION_READY", "GARDEN_ONE_INTERACTION_THEN_REOBSERVE")
    for action_id in cfg["action_order"]:
        selected = next((row for row in actions if row["action_id"] == action_id), None)
        if selected is not None:
            result["next_actions"] = [selected]
            result["goal_state"] = "READY_FOR_ONE_OBSERVED_INTERACTION"
            return finish("GARDEN_ACTION_READY", "GARDEN_ONE_INTERACTION_THEN_REOBSERVE")
    return finish("GARDEN_INSPECT_PLANTS", "INSPECT_EXISTING_PLANTS_AND_PLANTABLES", inspections=(
        "CURRENT_LOT_PLANT_INTERACTIONS", "SIM_INVENTORY_PLANTABLES"
    ))
