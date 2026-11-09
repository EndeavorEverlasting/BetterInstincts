# P95 — Tooltip and Hover Temporal Learning

Status: offline executable semantic-event adapter; no live Sims sensor, game input or playable mod claim. BI-002 remains ACTIVE.

## Goal and domain vocabulary

A hover can reveal a tooltip and imply an opportunity, but does not by itself indicate a successful action or human intent. A calibrated adapter (not yet installed) may call the opt-in listener on a semantic tooltip transition. Events are hover, tooltip_visible, tooltip_hidden, action, outcome. References are sanitized tokens, not raw tooltip text, names, screenshots, mouse keys or coordinates.

The action must be explicitly bound to the active tooltip target and an interaction_ref. A later outcome must use that interaction_ref and an evidence_ref. Only operator_reviewed helpful/harmful results count as reviewed successes/failures. Unreviewed outcomes remain pending. Observed association is not causal proof.

The reducer computes five rolling windows: 3, 5, 10, 30 and 60 minutes, with per-target/tooltip/action attempts, reviewed helpful/harmful counts, pending reviews and reviewed success rate. Three reviewed observations, at least three helpful, and at least 75% helpful mark a candidate as learning_eligible. This boolean neither trains the existing judgment model nor grants control.

## P95 call-stack prototype

Successful observational path:
1. Explicitly activate host_listener; no automatic job or global input hook.
2. A future calibrated UI observer or operator supplies a single sanitized event (not a screenshot or raw tooltip).
3. scripts.host_listener hover calls host_listener.observe_hover with per-call explicit opt-in.
4. Active session and one-writer file lock gate admission; hover_learning.observe validates schema/source/time/targets and collapses duplicate visible polls.
5. Atomic bounded state under ignored dist/host-listener/SESSION/hover-learning.json.
6. hover_learning.evaluate returns machine-readable 180/300/600/1800/3600-second projections.
7. Optional future human review can feed the separate judgment_learning owner. No SendInput, no cancellation and no implicit training.

Failure call stack: inactive session/absent opt-in -> BLOCKED; unexpected raw fields/target mismatch/no matching action/duplicate outcome -> BLOCKED; identical tooltip-visible poll -> UNCHANGED_TOOLTIP; unreviewed outcome -> pending, not successful; time regression or event/byte budget -> reject; history older than 60 minutes -> expire on next new event.

## Program state owners and bounds

- Existing host_listener owns session activation and ignored repository-local storage; at most one writer per session, atomic sidecar replacement, 64-KiB maximum state.
- New pure hover_learning reducer owns event-time transitions, deduplication, per-event provenance and 256-event one-hour memory bound.
- Existing judgment_learning exclusively owns manually reviewed model updates; no new independent trainer.
- Existing control_handoff and screen_admit exclusively own player-first input admission and the 15-second idle boundary. Hover data never creates an action permit.
- External sensor calibration, polling interval, localization, UI patch compatibility and real cursor/mouse behavior remain unproven; no daemon or OS-level mouse/keyboard hook is installed.

## Example manual offline call

Activate: python -m scripts.host_listener activate --session-id hover_lab_01

Write sanitized event JSON to dist/hover-event.json:

    {
      "schema": "betterinstincts.hover-event/v1",
      "id": "hover_0001",
      "at_ms": 1800000000000,
      "kind": "tooltip_visible",
      "source": "operator_supplied",
      "target_ref": "object:plant",
      "tooltip_ref": "tip:watering"
    }

Ingest: python -m scripts.host_listener hover --session-id hover_lab_01 --event dist/hover-event.json --explicit-opt-in

Deactivate: python -m scripts.host_listener deactivate --session-id hover_lab_01

Focused validation: python -m unittest tests.test_hover_learning -v

Ontology preflight: python -m scripts.semantic_preflight --consultation contracts/consultations/BI-HOVER-TEMPORAL-20261109.v1.json --operation repo_mutation --file betterinstincts/hover_learning.py

## Alternatives and second-pass critique

Rejected a global mouse/keyboard recorder and second background monitor: these bypass opt-in and duplicate existing host owners. Rejected writing hover logic into the click executor: observation is not authority. Selected an existing-listener port with a pure semantic reducer, enabling a later calibrated sensor without touching the game-input path.

Second-pass repair: persisted action records have an internally derived tooltip_ref, so validation must accept derived values without trusting caller-forged extras; events older than one hour rotate rather than endlessly filling long-running sessions.

Proof ceiling: supplied/synthetic semantic events and reviewed associations in offline tests, not live Sims telemetry, observed gameplay efficacy, installed sensor, auto-learning or a game-certified mod. Next real-game gate: consented disposable save, exact patch and scene corroboration, measured tooltip visibility transition + action + independent after-state + operator review. BI-002 hunger verification remains open.
