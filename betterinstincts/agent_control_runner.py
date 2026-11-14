"""Guarded last-resort computer use + always-on semantic codification coverage.

An adapter supplies one validated atomic game effect to the EXISTING
CooperativeScreenQueue. An active, explicitly opted-in host listener stores a
PREPARE journal record BEFORE admission and a receipt after queue execution.
Physical player activity yields; the same in-memory control session can wait
and resume via fresh trusted idle probes, without repeating completed work.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from betterinstincts.control_discovery import EVENT_SCHEMA, QUEUE_STATES
from betterinstincts.host_listener import (
    HostListenerError, read_control_discovery, record_control_discovery, status,
)
from betterinstincts.workflow_interop import CooperativeScreenQueue


class AgentControlRunnerError(ValueError):
    pass


class AgentControlRunner:
    """Single effect in flight; no agent callback can escape standard queue gates.

    This is NOT a background worker, desktop hook or authority grant. A real
    local actor must supply fresh scene/save/queue/target validation, effect
    adapter and idle probe. A persistent listener remains ACTIVE while control
    is PAUSED_FOR_PLAYER; only the action lane waits for user inactivity.
    """

    def __init__(self, session_id: str, queue: CooperativeScreenQueue):
        if not isinstance(queue, CooperativeScreenQueue):
            raise AgentControlRunnerError("COOPERATIVE_SCREEN_QUEUE_REQUIRED")
        if status(session_id)["state"] != "ACTIVE":
            raise AgentControlRunnerError("ACTIVE_LISTENER_REQUIRED")
        read_control_discovery(session_id)  # fail before ANY effect if no journal
        self.session_id = session_id
        self.queue = queue
        self.current_work_id: str | None = None
        self.last_queue_state: str | None = None

    def _write(self, kind: str, work_id: str, **fields: object) -> dict:
        state = read_control_discovery(self.session_id)
        return record_control_discovery(
            self.session_id,
            {"schema": EVENT_SCHEMA, "seq": state["events_count"] + 1,
             "kind": kind, "work_id": work_id, **fields},
            explicit_opt_in=True,
        )

    def prepare_effect(
        self, *, work_id: str, action_ref: str, object_class_ref: str,
        before_capture_ref: str, authority_ref: str,
        validate: Callable[[], Awaitable[bool]],
        effect: Callable[[], Awaitable[object]],
    ) -> dict:
        """Journal before any computer-use effect is queued.

        The queue's existing helper inserts an immediate checkpoint before
        the supplied atomic effect, on top of idle/focus/ownership validation.
        Every subsequent GUI operation must be a separate prepared work_id.
        """
        if self.current_work_id is not None or self.queue.pending or (
            self.queue.pending_observations or self.queue.suspended
        ):
            raise AgentControlRunnerError("ONE_EFFECT_IN_FLIGHT_REQUIRED")
        if not callable(validate) or not callable(effect):
            raise AgentControlRunnerError("CALLBACKS_REQUIRED")
        receipt = self._write(
            "PREPARE", work_id,
            action_ref=action_ref, object_class_ref=object_class_ref,
            before_capture_ref=before_capture_ref, authority_ref=authority_ref,
        )
        # A failed enqueue leaves a PREPARED journal candidate for investigation,
        # rather than silently erasing the action from a future agent's context.
        self.queue.enqueue_effect(work_id, validate, effect)
        self.current_work_id = work_id
        self.last_queue_state = None
        return receipt

    async def pulse(self) -> dict:
        """One opted-in activity attempt; waiting never closes computer use."""
        if self.current_work_id is None:
            raise AgentControlRunnerError("NO_PREPARED_EFFECT")
        if status(self.session_id)["state"] != "ACTIVE":
            raise AgentControlRunnerError("LISTENER_INACTIVE")
        result = await self.queue.run_once()
        queue_state = result["state"]
        if queue_state not in QUEUE_STATES:
            raise AgentControlRunnerError("UNEXPECTED_QUEUE_STATE")
        if queue_state != self.last_queue_state:
            self._write("QUEUE_STATUS", self.current_work_id,
                        queue_state=queue_state)
            self.last_queue_state = queue_state
        # WAITING_FOR_USER is a PAUSE, not a terminated session. The caller may
        # keep ticking an explicitly active session; two fresh idle checks and
        # scene validation occur on EACH later effect admission.
        return {
            **result, "session_id": self.session_id,
            "behavior_paused_for_player": queue_state == "WAITING_FOR_USER",
            "listener_remains_active": True,
            "needs_outcome_evidence": queue_state in {
                "COMPLETED", "NEEDS_RECONCILIATION"},
            "proof_ceiling": "QUEUE_RECEIPT_NOT_VERIFIED_GAME_OUTCOME",
        }

    async def wait_and_pulse(self, *, max_checks: int = 120) -> dict:
        """Bounded listener-driven idle wait; no daemon, no forced UI capture."""
        if type(max_checks) is not int or not 1 <= max_checks <= 120:
            raise AgentControlRunnerError("WAIT_BUDGET_INVALID")
        result = {}
        for _ in range(max_checks):
            result = await self.pulse()
            if result["state"] not in {"WAITING_FOR_USER", "WAITING_FOR_AGENT"}:
                return result
            await self.queue.sleep(self.queue.poll_seconds)
        return {
            **result, "state": "WAIT_BUDGET_REACHED",
            "behavior_paused_for_player": True,
            "listener_remains_active": True,
        }

    def record_observed_outcome(
        self, *, outcome: str, after_capture_ref: str, outcome_ref: str,
        player_interrupted: bool,
    ) -> dict:
        """Separate queue completion from a distinct actual game observation."""
        if self.current_work_id is None:
            raise AgentControlRunnerError("NO_PREPARED_EFFECT")
        if self.last_queue_state not in {"COMPLETED", "NEEDS_RECONCILIATION"}:
            raise AgentControlRunnerError("NO_OBSERVED_EFFECT_ATTEMPT")
        receipt = self._write(
            "OUTCOME", self.current_work_id,
            outcome=outcome, after_capture_ref=after_capture_ref,
            outcome_ref=outcome_ref, player_interrupted=player_interrupted,
        )
        self.current_work_id = None
        self.last_queue_state = None
        return receipt
