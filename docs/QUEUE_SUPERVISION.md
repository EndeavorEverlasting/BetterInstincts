# Per-Sim queue supervision and activity timing (Sixth Gear)

**Status:** optional, bounded, read-only **EA-native policy port**. Not a game-installed script, a desktop clicker, cancellation permission, background listener, or BI-002 game certification. Canonical owners: `contracts/queue-supervision.v1.json`, `betterinstincts/queue_supervision.py`, existing `betterinstincts/autonomy_moderation.py` and `betterinstincts/queue_capacity.py`.

## Parent goal and evidence

The left-hand Sims 4 Live Mode queue needs **event-level identity**, not an assumed universal maximum: identical semantic jobs should not occupy multiple slots; mutually exclusive outcomes should not be queued together; elapsed activity time and changing needs should inform timely replanning without abandoning player intent.

Sixth Gear P141 comparison: blindly increase a fixed capacity (rejected; the existing 2–3 multitasking / 6–7 ordinary bands are operator heuristics), fixed wall-clock timeouts (rejected; pause, game speed and mood change timing), perpetual HUD cancel-clicker (rejected as EA-native authority violation), **selected:** the existing all-household native policy with a source-attested, conservative per-Sim queue/duration/need supervisor. P95/P82 selected a single snapshot and a bounded same-build, same-action completion history rather than a new daemon, queue engine or hidden persistence layer. P08 exact-game-source/Live Mode is blocked without a local Windows EA runtime.

## Call stack

`evaluate_native_household_autonomy(observation)` → optional `observation["queue_supervision"]` → `evaluate_queue_supervision(..., sims=observation["sims"])` → identity/clock/player/queue guards → existing `evaluate_queue_capacity` → semantic duplicate/exclusivity audit → source-calibrated activity duration → six-needs urgency forecast → **one cancellation/replan suggestion maximum per Sim**. If a queue-supervision candidate is present, it supersedes the legacy native suppression candidate in the output so agents cannot race two proposed cancellations. Without the optional observation, previous native behavior is unchanged.

**Queue identity:** a semantic key must include action intent and exact target, proven from native source or independently reviewed game observation; distinct targets or unrelated tasks are not duplicates. Even the same task/target can legitimately repeat (e.g., two batches or skill practice): cancellation requires independently proven `dedupe_safe=true` and `dedupe_proof_ref` on **both** actions. Mere identical labels never authorize dropping a second task. Contradiction requires a separately certified mutually exclusive outcome group (e.g., two different disposal destinations for the *same* disposable dish), not just a shared object. Each action carries an exact native slot, origin proof, goal-protection proof, Sim ID and capture ID. Any player/unknown-origin action in that Sim's queue, missing policy opt-in or stale snapshot yields. Unknown queue capacity never authorizes another enqueue. A full or uncertain queue holds; the optional supervisor never grants actual enqueue or cancellation authority.

**Duration model:** the caller supplies an observed active-Sim clock, base activity duration, individual proven modifiers for moodlet, temperament, balance and trait, plus at most 12 same-action, same-game-build *completed* measurements. The arithmetic is a provisional multiplicative hypothesis, calibrated by the median of independent actual/predicted ratios (winsorized to 0.5–2.0). It does not claim that a given EA trait has a particular speed factor, or that every moodlet actually changes task time. Missing proven modifiers may display an indicative estimate but cannot trigger forecast-based preemption. Pause and unverified clock stop all timeout-based switching. An activity exceeding the calibrated estimate by at least 75% and 30 seconds, with an **independent observed stall**, triggers reobservation, not blind cancellation.

**Need switching:** use the existing six-needs model's provisional critical and preemptive thresholds, not assumed live EA tuning. A source-proven urgent need or calibrated prediction that the need reaches critical before the current unrelated activity finishes may identify a running **autonomous** slot for reconsideration. The current activity is protected if it already serves that need, is player/unknown-owned, has a protected goal or lacks proof. When a reliable forecast says the current activity has 15 or fewer active-Sim seconds remaining and it is not stalled, preserve the near-finished activity rather than reflexively interrupting. Replans otherwise enforce at least 90 active-Sim seconds since a verified previous switch and request **one** effect proposal, then fresh observation. Unknown rate, profile, origin, save, goal or lease never becomes cancellation permission.

## Example optional native observation

```python
observation["queue_supervision"] = {
    "schema": "betterinstincts.queue-supervision/v1",
    "household_ref": "house:observed", "game_build": "exact:patch",
    "capture_ref": "capture:current",
    "sims": [{
        "sim_ref": "sim:observed", "capture_ref": "capture:current",
        "queue_verified": True, "policy_opt_in": True,
        "multitasking": False,  # observed, not assumed
        "needs": {"hunger": .4, "bladder": .8, "energy": .8,
                  "hygiene": .8, "fun": .7, "social": .7},
        "needs_proof_ref": "proof:needs",
        "need_decay_per_active_second": {"hunger": .0005},
        "decay_proof_ref": "proof:rate",
        "switch_history_verified": True,
        "active_activity": None,  # supply calibrated profile for duration
    }],
}
# The actual queue rows (slot/semantic/provenance metadata) remain in
# observation["sims"][0]["queue"]; they are NOT duplicated here.
```

## Regression probes and proof

`python -m unittest tests.test_queue_supervision tests.test_autonomy_moderation tests.test_queue_study -v`, `python -m scripts.semantic_preflight`, `python -m scripts.check_native_gameplay_authority --base-ref <BASE_SHA>`, `python -m scripts.check_human_sovereignty`, `python -m scripts.check_peripheral_boundary`. Run full offline tests and CI before merge; re-run after changes. Tests include stale capture/slot mismatch, replayed learning samples, missing activity factors, crowding, player-queue overrides, contradictory objectives, paused clock, urgent need served, and cooldown.

**NEXT genuine blocker:** use the existing exact-patch EA native policy owner under [issue #171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171) to obtain attested tuning/hook IDs, actual game clock, action origins and independent before/after observations. Only then build an opt-in, reversible package and execute disposable-save A/B plus rollback. Offline PR/CI/main prove source behavior, not game-native cancellation, simulated duration accuracy, game installation or actual need switches.
