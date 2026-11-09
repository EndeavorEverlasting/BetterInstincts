"""Bounded, evidence-qualified continuity for player-selected multi-target tasks.

Pure P95/P124 seam: never clicks, cancels, edits saves or starts a listener.
The caller owns durable target observations and exact UI admission.
"""
from __future__ import annotations

import math
import time
from collections.abc import Mapping

SCHEMA = "betterinstincts.task-continuity/v1"
MAX_TARGETS = 32
MAX_QUEUE = 24
MAX_AGE_SECONDS = 180
STATES = {"PENDING", "IN_PROGRESS", "VERIFIED_DONE"}
ORIGINS = {"PLAYER", "SIM_AUTONOMY", "HOST", "UNKNOWN"}


class TaskContinuityError(ValueError):
    """Invalid or untrustworthy task record; never a reason to act."""


def _ref(value: object) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 120
        and all(c.isalnum() or c in "_:.-" for c in value)
    )


def _number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def evaluate_task_continuity(
    record: Mapping, *, capture_ref: str, now: float | None = None
) -> dict:
    """Classify a current queue without inferring action origin or completion.

    SIM_AUTONOMY attribution requires a source observation reference.
    A returned resumption is only an inspection/action candidate, NEVER input
    authorization. The active player and the existing host/need gates outrank it.
    """
    if not isinstance(record, Mapping) or record.get("schema") != SCHEMA:
        raise TaskContinuityError("TASK_CONTINUITY_SCHEMA_INVALID")
    if any(not _ref(record.get(key)) for key in
           ("goal_id", "sim_ref", "action_id", "player_command_ref")):
        raise TaskContinuityError("TASK_CONTINUITY_IDENTITY_INVALID")
    targets = record.get("targets")
    if not isinstance(targets, list) or not 1 <= len(targets) <= MAX_TARGETS:
        raise TaskContinuityError("TASK_CONTINUITY_TARGETS_INVALID")
    seen: set[str] = set()
    pending: list[str] = []
    verified: list[str] = []
    for item in targets:
        if not isinstance(item, Mapping) or not _ref(item.get("target_ref")):
            raise TaskContinuityError("TASK_CONTINUITY_TARGET_INVALID")
        target = item["target_ref"]
        if target in seen or item.get("state") not in STATES:
            raise TaskContinuityError("TASK_CONTINUITY_TARGET_STATE_INVALID")
        seen.add(target)
        if item["state"] == "VERIFIED_DONE":
            # Never promote a naked completion flag into gameplay success.
            if not (_ref(item.get("outcome_ref")) and _ref(item.get("outcome_capture_ref"))):
                raise TaskContinuityError("TASK_CONTINUITY_OUTCOME_PROOF_REQUIRED")
            verified.append(target)
        else:
            pending.append(target)
    result = {
        "schema": "betterinstincts.task-continuity-result/v1",
        "goal_id": record["goal_id"],
        "sim_ref": record["sim_ref"],
        "action_id": record["action_id"],
        "capture_ref": capture_ref,
        "target_count": len(targets),
        "verified_done_count": len(verified),
        "verified_done_targets": verified,
        "pending_targets": pending,
        "next_target_ref": pending[0] if pending else None,
        "state": "PENDING",
        "gate": "REOBSERVE_TASK_QUEUE",
        "action": "INSPECT_CURRENT_QUEUE",
        "execute_allowed": False,
        "cancel_allowed": False,
        "proof_ceiling": "OFFLINE_TASK_CONTINUITY_NOT_GAME_OUTCOME",
    }

    def finish(gate: str, action: str, state: str = "PENDING") -> dict:
        result.update(gate=gate, action=action, state=state)
        return result

    stamp = record.get("observed_at_unix")
    instant = time.time() if now is None else now
    if (
        not _number(stamp) or not _number(instant)
        or not 0 <= instant - stamp <= MAX_AGE_SECONDS
        or record.get("capture_ref") != capture_ref
        or record.get("queue_verified") is not True
    ):
        return finish("REOBSERVE_TASK_QUEUE", "INSPECT_CURRENT_QUEUE")

    override = record.get("player_override")
    if override is not None:
        if (not isinstance(override, Mapping)
                or override.get("kind") not in {"CANCEL_GOAL", "REPLACE_GOAL"}
                or not _ref(override.get("proof_ref"))):
            raise TaskContinuityError("TASK_CONTINUITY_OVERRIDE_PROOF_INVALID")
        return finish("PLAYER_CHANGED_GOAL", "YIELD_TO_PLAYER", "SUPERSEDED")

    if not pending:
        return finish("TASK_VERIFIED_COMPLETE", "NO_FURTHER_QUEUE", "VERIFIED_COMPLETE")

    queue = record.get("queue")
    if not isinstance(queue, list) or len(queue) > MAX_QUEUE:
        raise TaskContinuityError("TASK_CONTINUITY_QUEUE_INVALID")
    classified: list[tuple[str, str, str]] = []
    for row in queue:
        if not isinstance(row, Mapping) or not _ref(row.get("action_id")):
            raise TaskContinuityError("TASK_CONTINUITY_QUEUE_ROW_INVALID")
        if row.get("capture_ref") != capture_ref or row.get("sim_ref") != record["sim_ref"]:
            return finish("REOBSERVE_TASK_QUEUE", "INSPECT_CURRENT_QUEUE")
        origin = row.get("origin", "UNKNOWN")
        if origin not in ORIGINS:
            raise TaskContinuityError("TASK_CONTINUITY_ORIGIN_INVALID")
        # Game queue labels alone cannot establish autonomous vs human origin.
        if origin != "UNKNOWN" and not _ref(row.get("origin_proof_ref")):
            origin = "UNKNOWN"
        target = row.get("target_ref")
        if target is not None and not _ref(target):
            raise TaskContinuityError("TASK_CONTINUITY_QUEUE_TARGET_INVALID")
        classified.append((row["action_id"], target or "", origin))

    # The player may always displace an old command. Do not fight their new queue.
    if any(origin == "PLAYER" and not (
        action == record["action_id"] and target in pending
    ) for action, target, origin in classified):
        return finish("PLAYER_CHANGED_QUEUE", "YIELD_TO_PLAYER")

    # Do not duplicate still-queued fertilization, even if chatting is active.
    if any(action == record["action_id"] and target in pending
           for action, target, _ in classified):
        return finish("TASK_ALREADY_QUEUED", "WAIT_FOR_QUEUED_TASK", "IN_PROGRESS")

    if any(origin == "UNKNOWN" for _, _, origin in classified):
        return finish("REOBSERVE_TASK_QUEUE", "INSPECT_QUEUE_ORIGIN")
    if any(origin == "SIM_AUTONOMY" for _, _, origin in classified):
        return finish("AUTONOMOUS_TASK_INTERRUPTION",
                      "REVIEW_DISTRACTION_THEN_REOBSERVE", "INTERRUPTED")
    if classified:
        return finish("OTHER_VERIFIED_WORK", "WAIT_THEN_REOBSERVE")

    return finish("TASK_RESUME_CANDIDATE", "FIND_ONE_CURRENT_TARGET_AFFORDANCE")
