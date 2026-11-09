"""Conservative, observation-based Sims action queue admission (offline advisory).

Operator-observed ranges are heuristics, not asserted patch-invariant limits.
This module neither clicks nor cancels, and a missing multitasking observation
never becomes permission to enqueue.
"""
from __future__ import annotations

from typing import Optional, Sequence


class QueueCapacityError(ValueError):
    pass


def evaluate_queue_capacity(
    queue: Sequence[str],
    *,
    multitasking: Optional[bool] = None,
    player_directed: bool = False,
    rejected_last_enqueue: bool = False,
) -> dict:
    if not isinstance(queue, (list, tuple)) or len(queue) > 16:
        raise QueueCapacityError("QUEUE_OBSERVATION_INVALID")
    if any(not isinstance(x, str) or not x.strip() or len(x) > 80 for x in queue):
        raise QueueCapacityError("QUEUE_ITEM_INVALID")
    if multitasking is not None and type(multitasking) is not bool:
        raise QueueCapacityError("MULTITASKING_OBSERVATION_INVALID")
    if type(rejected_last_enqueue) is not bool:
        raise QueueCapacityError("ENQUEUE_REJECTION_OBSERVATION_INVALID")
    observed = len(queue)
    band = [2, 3] if multitasking is True else [6, 7] if multitasking is False else None
    conservative_limit = band[0] if band else None
    if player_directed:
        gate = "PLAYER_QUEUE_YIELD"
    elif rejected_last_enqueue:
        gate = "REOBSERVE_AFTER_ENQUEUE_REJECTION"
    elif conservative_limit is None:
        gate = "MULTITASKING_OBSERVATION_REQUIRED"
    elif observed >= conservative_limit:
        gate = "QUEUE_CAPACITY_HOLD"
    else:
        gate = "QUEUE_CAPACITY_AVAILABLE"
    quota = max(0, conservative_limit - observed) if gate == "QUEUE_CAPACITY_AVAILABLE" else 0
    return {
        "state": "QUEUE_CAPACITY_EVALUATED",
        "gate": gate,
        "observed_queue_count": observed,
        "multitasking": multitasking,
        "operator_reported_capacity_band": band,
        "conservative_limit": conservative_limit,
        "max_new_actions": quota,
        "enqueue_allowed": quota > 0,
        "policy": "OPERATOR_HEURISTIC_REOBSERVE_AFTER_EACH_ENQUEUE",
        "forbidden": ["BLIND_FILL_QUEUE", "CANCEL_PLAYER_QUEUE", "CLAIM_FIXED_GAME_LIMIT"],
        "proof_ceiling": "OFFLINE_QUEUE_ESTIMATE_NOT_SIMS_QUEUE_ATTESTATION",
    }
