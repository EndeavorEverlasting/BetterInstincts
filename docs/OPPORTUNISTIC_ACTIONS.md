# Sixth Gear — Class-transition homework and targeted chat whims

**Capability:** BetterInstincts can use a freshly verified school homework interaction
even close to or during the class transition, while preserving attendance; and it
can translate an observed named chat whim into on-lot talk or a verified
**R → Relationships → exact person → Chat** route. This is a source-integrated
**host advisory**, not an installed Sims 4 EA mod or a Win32 auto-clicker.

## Parent failure corrected

The existing `school_day` and `teen_homework` planners conservatively blocked
all school-premises homework. The operator observed that in a particular Sims 4
session homework could still finish just before and after class began, followed
by attendance. A blanket timing denial was therefore too restrictive. We have
**not** reversed the old default: it remains when game-affordance evidence is
missing, stale or contradictory. Instead, `opportunistic_actions` qualifies a
precise exception and `host_stack` prioritizes it over that old heuristic
only when its positive proof gates pass.

A visible social whim for **Chat with [specific Sim]** was not translated
into a target action. The existing `social_opportunity` handles invite OK/Cancel
with occult protection but not missing chat actions. The new path resolves
the exact Sim first, then chooses a proven on-lot conversation or Relationships
chat. When an off-lot invitation is the only route, the existing occult
safety conditions still apply; no invitation is automatically sent.

## Homework: evidence-bound permitted seam

One optional `school_homework_window` object, supplied to a currently active
host-listener turn from **actual independently observed** current-game UI or
EA-native evidence, contains:

```json
{
  "capture_ref": "capture:example-local-observed",
  "game_version": "1.121.361.1020",
  "school_phase": "class_time",
  "homework_available": true,
  "homework_running": false,
  "class_attendance_preserved": true,
  "observed_actions": ["DO_HOMEWORK"],
  "source_kind": "GAME_UI_VERIFIED"
}
```

This example is **synthetic**, not a game observation or proof that the example
build supports the seam. The parent observation must also assert school
premises, school day active, homework pending, inventory book present, six
independently observed needs, queue and multitasking state. Exact current
capture and phase must match. An already-running homework interaction with
`CONTINUE_HOMEWORK` emits a **continue and preserve class** plan instead
of duplicating the queue. Verified classroom attendance must not be canceled.
Uncertain attendance, player activity, critical needs, stale capture,
unavailable interaction, missing inventory or full/unknown queue holds.
Never infer completed homework from queuing alone.

The policy uses the same existing conservative queue budget as the teen
homework evaluator; it does not infer a universal game-wide queue capacity.

## Chat whim: a specific person, a real route

An observed string such as `Chat with Morgan` becomes a candidate only after
exact, unique matching against a supplied fresh Sims relationship-library
record. The record must contain a stable opaque `sim_id`, matching
`capture_ref`, `on_lot` boolean, and observed action labels:

```json
{
  "name": "Morgan",
  "sim_id": "sim:illustrative",
  "on_lot": false,
  "capture_ref": "capture:example-local-observed",
  "observed_actions": ["RELATIONSHIP_CHAT"],
  "occult_status": "HUMAN"
}
```

These values are illustrative, not personal game evidence. The action routes are:
- **On the lot, chat observed:** find exact person → observed Chat action.
- **Off lot, relationship chat observed:** R panel → exact relationship card
  → observed Chat action → recheck named queue outcome.
- **Off lot, invite observed but direct chat unavailable:** only if the unique
  Sims lookup and allowlisted occult evidence make an invite safe; review
  invitation → reobserve actual arrival → then Chat.
- **No verified person/action or ambiguous name:** inspect/reobserve, never
  select an arbitrary Sim or manufacture a chat command.

`queued_social_targets` can supply exact current `sim_id`, `action_kind`
and `capture_ref` to prove the conversation is already queued. If a generic
chat label is present without a target identity, the policy **reobserves**
rather than piling on duplicate or contradictory actions. Generic wishes
(`Chat with someone`) are not converted to fictional named targets.

Every recommendation has `execute_allowed: false` and requires independent
native-gameplay authority or a fully admitted one-effect disposable host lab.
No planner physically types `R`, presses a menu, cancels a player queue or
edits a save.

## Integration / developer proof

- Pure evaluator owner: `betterinstincts/opportunistic_actions.py`
- Host result priority and feedback: `betterinstincts/host_stack.py`
- Active host listener validation/passthrough: `betterinstincts/host_listener.py`
- Machine contract: `contracts/opportunistic-actions.v1.json`
- Local read-only inspector: `scripts/opportunistic_actions.py`
- Falsifying regressions: `tests/test_opportunistic_actions.py`

A local agent may inspect a separately authorized observation file:

```sh
python -m scripts.opportunistic_actions --observation PATH_TO_CURRENT_VERIFIED_JSON
python -m unittest tests.test_opportunistic_actions tests.test_school_day tests.test_teen_homework -v
python -m scripts.check_ontology --base-ref ACTUAL_PR_BASE_SHA
python -m scripts.check_native_gameplay_authority --base-ref ACTUAL_PR_BASE_SHA
```

For actual in-game realization, the local Windows Sims 4 instance must
independently certify source-calibrated game version/phase, currently visible
homework action with before/after homework progress and **unbroken attendance**,
then the exact R relationship panel target and queued chat with a fresh
after-action capture. If the game rejects an action or the native hook is
unknown, the policy must abstain rather than looping clicks. The EA-native
port must be evidenced on the exact installed patch via the existing native
architecture and independent rollback tests; this host policy is not a
replacement for native mechanics.

**BI-002 hunger live A/B and rollback remains ACTIVE**; the new feature does
not replace or unnecessarily gate it.
