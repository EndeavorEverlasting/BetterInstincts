"""Safe per-Sim continuation across household portrait selection changes.

A selection event does not prove that an off-screen action queue survived.
Pure evaluator: only the original task source may update observed outcome state.
"""
from __future__ import annotations

import math
import time
from collections.abc import Mapping

from betterinstincts.task_continuity import (
    TaskContinuityError, evaluate_task_continuity,
)

SCHEMA = "betterinstincts.selected-sim-observation/v1"


class SelectedSimContinuityError(ValueError):
    pass


def _evidence(value: object) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 120 and all(
        c.isalnum() or c in "_.:-" for c in value
    )


def evaluate_selected_sim_goal(
    task: Mapping, selection: Mapping, *,
    capture_ref: str, now: float | None = None,
) -> dict:
    """Suspend a goal for a different active Sim, revalidate after selection.

    Does not assume that another Sim's queue is still live. The task's target
    snapshot survives, but completion cannot be advanced from offscreen state.
    """
    if not isinstance(selection, Mapping) or selection.get("schema") != SCHEMA:
        raise SelectedSimContinuityError("SELECTED_SIM_SCHEMA_INVALID")
    if not isinstance(task, Mapping) or not _evidence(task.get("sim_ref")):
        raise SelectedSimContinuityError("SELECTED_SIM_TASK_INVALID")
    if not _evidence(capture_ref):
        raise SelectedSimContinuityError("SELECTED_SIM_CAPTURE_INVALID")
    # Reuse existing task validation, preserving its goal/target semantics.
    try:
        task_report = evaluate_task_continuity(
            task, capture_ref=capture_ref, now=now,
        )
    except TaskContinuityError as exc:
        raise SelectedSimContinuityError(str(exc)) from exc
    out = {
        "schema": "betterinstincts.selected-sim-continuity-result/v1",
        "goal_id": task_report["goal_id"],
        "sim_ref": task_report["sim_ref"],
        "selected_sim_ref": selection.get("selected_sim_ref"),
        "task_continuity": task_report,
        "gate": "REOBSERVE_SELECTED_SIM",
        "action": "VERIFY_CURRENT_SIM_AND_QUEUE",
        "execute_allowed": False,
        "cancel_allowed": False,
        "proof_ceiling": "SELECTED_SIM_OFFLINE_ONLY_NOT_GAME_QUEUE_PROOF",
    }
    # An explicit player cancellation or independently verified completion
    # supersedes any off-screen suspension. Never revive a canceled task.
    if task_report["state"] in {"SUPERSEDED", "VERIFIED_COMPLETE"}:
        out.update(
            gate=("PLAYER_GOAL_SUPERSEDED" if task_report["state"] == "SUPERSEDED"
                  else "TASK_VERIFIED_COMPLETE"),
            action=("YIELD_TO_PLAYER" if task_report["state"] == "SUPERSEDED"
                    else "NO_FURTHER_QUEUE"),
            state=task_report["state"],
        )
        return out
    now_value = time.time() if now is None else now
    stamp = selection.get("observed_at_unix")
    if (type(stamp) not in (int, float) or not math.isfinite(stamp)
            or type(now_value) not in (int, float) or not math.isfinite(now_value)
            or not 0 <= now_value - stamp <= 180
            or selection.get("capture_ref") != capture_ref
            or selection.get("selection_verified") is not True
            or not _evidence(selection.get("selection_proof_ref"))
            or not _evidence(selection.get("selected_sim_ref"))):
        return out
    if selection["selected_sim_ref"] != task["sim_ref"]:
        out.update(
            gate="SIM_NOT_SELECTED",
            action="PRESERVE_GOAL_OFFSCREEN",
            state="SUSPENDED_FOR_OTHER_SELECTED_SIM",
        )
        return out
    # Fresh selection is not proof of a fresh, selected-actor queue.
    if (task.get("capture_ref") != capture_ref
            or task_report["gate"] == "REOBSERVE_TASK_QUEUE"):
        return out
    out.update(
        gate="SELECTED_SIM_GOAL_EVALUATED",
        action="USE_EXISTING_TASK_CONTINUITY_GATES",
        state=task_report["state"],
    )
    return out
