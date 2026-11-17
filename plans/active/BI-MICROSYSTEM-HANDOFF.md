# Household microsystem queue handoff

## Runtime contract

The optional installed policy joins reports from Needs, Career,
Contingencies and Skills against each active household portrait's left-side
action queue. Domain owners keep their own readiness, deadline, prerequisite
and affordance decisions. Independent domain evaluations can finish
separately. Each result must refer to the queue snapshot's current capture.
Dependent steps advance only when their domain owner observes the
prerequisite. The native callback serializes effects.

- Consider tiers in the listed order for each portrait. A current `CLEAR`
  report or an independently observed queued action covering the same work
  admits the next tier. Missing, failed or pending higher-tier evidence
  holds that portrait. Other qualified portraits can continue.
- Compare admissible candidates lexicographically by tier, then by
  urgency × expected benefit ÷ expected Sim minutes. Break ties between
  portraits in observed circular order starting with the selected Sim.
  Break ties within a portrait by stable work reference.
- Recompute from two separate fresh observations before one effect. A
  different queue revision, winning proposal, actor, save, input generation
  or player takeover withdraws admission. When the winner is on a
  different portrait, the existing portrait transaction switches first
  and requires a separate selection readback and a fresh decision.
- Enqueue at the tail unless a contiguous trailing segment of pending,
  lower-priority BetterInstincts actions allows earlier insertion. Running
  and native actions retain their order. Player-owned or unknown queue
  rows hold that portrait. An uncertain enqueue stays pending until a
  correlated observation establishes its queue slot, completed effect or
  definite absence of effect.

## Adapter packet

Implement `read_microsystem_handoff(frame)` with schema
`betterinstincts.microsystem-handoff/v1`. Provide `game_build`, `run`,
`save`, `household`, `capture`, `selected`, the ordered `roster`,
`safe_to_leave` and an actor-keyed `members` map. An absent member has
no admissible action. For each available actor provide the frame's
`capture`, `available: true`, `player_queue: false`,
`queue_verified: true`, `queue_ref`, measured `slots_free`, ordered
`queue` and `lanes`. Change `queue_ref` whenever queue slots, capacity
or ownership change.

A queue row carries a unique `slot`, a stable logical `work` reference,
`origin`, and `state` (`RUNNING` or `PENDING`). BetterInstincts rows
carry their priority `domain`. Use stable work references that identify
a unit of intent for that actor, such as one occurrence of a career task.
The exact same reference joins the lane option, the queued row and the
receipt. A later, independently observed occurrence uses its own reference.

Lane keys are `NEEDS`, `CAREER`, `CONTINGENCIES` and `SKILLS`. Give each
lane its own `capture` and `state`. `READY` includes 1–16 `options`, each
with a unique `work`, an exact native `proposal`, `urgency` and `benefit`
in (0, 1], and `minutes` in [1, 1440]. Report `CLEAR` only after the
current domain evaluation finds no open work or safely defers it.
Use `WAITING` or `FAILED` while a higher tier remains unresolved.

Implement `submit_microsystem_if_current(decision, frame)` as one atomic EA
queue operation. Recheck the frame, ownership, exact proposal, `queue_ref`,
capacity and optional `before_slot` before effect. Return `NO_EFFECT` only
when rejection is certain. Independently implement
`read_microsystem_outcome(decision, frame)` for a later observation. Return
its `capture`, `request_capture`, `actor`, `work`, `proposal`,
`readback_ref` and `status`. `QUEUED` includes a verified `slot`,
`COMPLETED` an independent `effect_ref`, and `NO_EFFECT` definitive
rejection evidence.

In this opt-in mode the four lanes supply normal gameplay proposals.
Integrate existing domain owners and their protected constraints at that
adapter boundary. Legacy installed configurations continue to use their
existing proposal paths. Game-blocking modal and restock ownership use the
existing runtime gates. The optional package needs the existing portrait
binding and an exact-build `installed_microsystem_handoff_binding_ref`.

## Evidence and next gate

Sixth Gear scoped the sprint to priority handoffs. P141 selected a shared
callback coordinator after comparing independent native writers, a single
blocking cascade and diagnostics alone. Existing callback and queue
ownership ruled out duplicate writers. A whole-household serial evaluator
would let one failed lane hold unrelated portraits. Diagnostics alone
would leave the dispatch decision unchanged. P95 joined fresh household
ranking to the existing portrait and native callbacks. P82 exercised tier
release, independent portrait progress, stale evidence, and lost
acknowledgements against deterministic fixtures. P08 is
`BLOCKED_LOCAL_GAME_ACCESS`. P07 and P124 retain the existing gameplay,
packaging and portrait transaction boundaries.

Source proof:

```sh
python -m unittest tests.test_microsystem_handoff tests.test_installed_player_runtime tests.test_portrait_handoff tests.test_native_ecology_bundle -v
python -m scripts.native_ecology_bundle build --help
```

For [#171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171),
start with exact-build EA source inspection and the native queue call and
readback. Bind the packet and queue ports on the Windows game host and run
the owned package on one admitted disposable household. Observe a
Needs → Career → Contingencies → Skills sequence, a full or away portrait
releasing attention, a competing lower-priority whim, player takeover
between frames and a rejected or delayed enqueue. Record actual native
slot order and action completion separately. Compare an unchanged
player-directed queue and verify ownership-scoped uninstall and rollback.
