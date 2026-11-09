# Multi-target task continuity / autonomous distraction recovery

**P95** owns the deterministic continuity call stack; **P124** keeps it beside the existing `gardening_service` and `host_stack`, not in a duplicate scheduler. **Trifecta:** P82 falsifiable offline cases, P07 integration, P08 exact-build local gameplay proof **OPEN**.

## Tim fertilizes every plant

The player selects a bounded list of plants to fertilize. The local agent passes an honest `task_continuity` snapshot inside the ordinary `gardening` observation. Each target has a stable object reference and PENDING, IN_PROGRESS, or VERIFIED_DONE state. Only an independently observed outcome with a receipt permits VERIFIED_DONE. The stable goal and remaining targets are carried forward by the observation producer / existing listener receipts; this module does **not** auto-write a hidden task ledger or poll the game.

A **fresh** verified queue containing an already queued Fertilize action is left alone, not duplicated. A different newly player-authored action yields immediately. For an independently provenance-verified `SIM_AUTONOMY` chat or other detour, the evaluator emits `AUTONOMOUS_TASK_INTERRUPTION`, preserves the first incomplete plant and suggests inspecting/correcting the detour after independent admission. **It never cancels a chat itself.** An unproven origin, unknown scene, stale capture, mismatched actor or ambiguous queue instead requires reobservation. Once the verified queue is clear, a fresh enabled `FERTILIZE` menu entry on that exact remaining plant may be planned, one action per turn.

## Call stack and safety

```text
existing opt-in host_listener tick + fresh current capture
  -> host_stack.evaluate_turn / existing needs & responsibilities
    -> gardening_service.evaluate_gardening_turn
      -> task_continuity.evaluate_task_continuity (pure, bounded)
      -> one exact-target observed Fertilize candidate OR safe wait/reobserve
  -> independent host screen_admit + presence lease for EACH real UI step
  -> observation of outcome before marking target VERIFIED_DONE
```

Do not mistake `player_directed` (active human interaction right now) for the saved player command that started the job. Human input and all explicit player changes still preempt host control. Needs emergencies, attendance and homework outrank gardening; an autonomous distraction is **not** an emergency. Do not blind-cancel, spam queues, force timers or claim completion from queue disappearance. UI/action origin proof and exact patch cues require live Windows evidence.

## Required input example (illustrative, not a game observation)

```json
{
  "schema": "betterinstincts.task-continuity/v1",
  "goal_id": "goal:tim-fertilize", "sim_ref": "sim:tim",
  "action_id": "FERTILIZE", "player_command_ref": "command:human-1",
  "capture_ref": "capture:current", "observed_at_unix": 0,
  "queue_verified": true,
  "targets": [
    {"target_ref": "plant:1", "state": "VERIFIED_DONE", "outcome_ref": "receipt:1", "outcome_capture_ref": "capture:prior"},
    {"target_ref": "plant:2", "state": "PENDING"}
  ],
  "queue": [
    {"action_id": "CHAT", "target_ref": "sim:visitor", "sim_ref": "sim:tim",
     "origin": "SIM_AUTONOMY", "origin_proof_ref": "event:actual-origin",
     "capture_ref": "capture:current"}
  ]
}
```

The sample timestamp is intentionally invalid for live use. A real sensor must supply its current timestamp and evidence; do not use example references as actual proof. The default `gardening` path remains backward-compatible when `task_continuity` is absent. Offline tests do not prove the mod altered The Sims 4 or that native game queues expose origin.
