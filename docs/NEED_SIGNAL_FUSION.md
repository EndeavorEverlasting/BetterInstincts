# Need Signal Fusion — Sixth Gear (2026-11-14)

**Owner:** `betterinstincts/need_signal_fusion.py` and `contracts/need-signal-fusion.v1.json`.  
**Public entrypoint:** `evaluate_need_signals(observation, *, now=None, prior_health=None)`.  
**Proof ceiling:** OFFLINE POLICY. The repository has not installed an actual game-native live reader, calibrated computer-vision detector, sensor processes or asynchronous recovery service on the operator's Windows Sims host.

## Original observed problem

The operator's paused Sims 4 Live screenshot shows a **Servo**, with four motives: **Fun, Social, Durability, Charge**. Social is still green but displays **three red downward chevrons**. Charge is lower and yellow; Fun remains green; emotion reads **Fine**. The operator describes a positive cheerful effect without an exact game-verified buff identifier. The three arrows are an **ordinal trend indicator**, not proof of a numerical 3x decline multiplier, exact motive units per Sim minute, or ongoing progress while **PAUSED**. A good mood is not proof of healthy Social trend.

`contracts/occult-needs.v1.json#profiles.servo` already owns those four motives. Do **not** invent Hunger, Bladder, Energy or Hygiene readings for Servo to satisfy an ordinary-six call stack. The historical `host_stack.evaluate_turn` remains an ordinary six-need owner; it accepts only an optional six-profile fusion sidecar. A Servo observer calls the typed `evaluate_need_signals` port directly until an exact-build runtime adapter is independently proven.

## Architecture — two independent asynchronous producers, one pure evaluation port

```text
Read-only EA-native game-time motive/buff observation (future, exact-patch hook)
    -> optional normalized 0..1 level, signed measured rate / Sim minute
Calibrated HUD semantic CV observation (future, reviewed model + current panel)
    -> optional approximate level, direction, arrow_count in {1,2,3}
    -> independent source timestamps, capture IDs and probe proofs
evaluate_need_signals(profile, game_build, sim_ref, feeds, prior_health):
    -> freshness, source/provenance, exact profile and calibration checks
    -> per-source health: HEALTHY / DOWN / QUARANTINED / RECOVERING
    -> single-source fallback when the other is down
    -> two distinct post-reset verified frames before restoring failed source
    -> conflicting simultaneous directions => REOBSERVE, no confident value
    -> paused trend indicator remains advisory; no live-motion inference
    -> existing moodlets.evaluate_moodlets for actually observed labels
    -> source-qualified need urgency and safe moodlet guidance
    -> no gameplay, input, timer, daemon, process restart or queue change
```

The independent processes are **not** presently supplied by this repo. Two consumers can supply independently collected frames at different timestamps. The pure evaluator can continue using one healthy feed until a degraded source is explicitly reset and passes two fresh independent probes. It produces `source_health` to pass into the next invocation as `prior_health`; this is not automatic persistence or a process restart. A damaged host or hung native/CV adapter needs a separately authorized, proven local sensor implementation. **Never restart the game** as part of this pure health check.

### Example source payload (synthetic, not a real game observation)

```json
{
  "schema": "betterinstincts.need-signal-fusion/v1",
  "profile": "servo",
  "sim_ref": "sim:test",
  "game_build": "1.121.361.1020",
  "capture_ref": "capture:review",
  "game_paused": true,
  "player_active": false,
  "feeds": [{
    "source": "HUD_CV",
    "status": "READY",
    "source_ref": "source:calibrated-detector",
    "sample_ref": "sample:one",
    "capture_ref": "capture:panel",
    "sim_ref": "sim:test",
    "game_build": "1.121.361.1020",
    "profile": "servo",
    "observed_at_unix": 2000.0,
    "probe_passed": true,
    "scene_verified": true,
    "calibration_ref": "calibration:current-hud",
    "calibration_verified": true,
    "needs": {
      "social": {"level": 0.69, "direction": "DOWN", "arrow_count": 3,
                 "arrow_proof_ref": "cue:three-down"}
    }
  }]
}
```

Use `now=2000.0` for this synthetic example. No live social numerical rate can be derived from it. A native feed requires `native_hook_ref`, `native_read_verified`, and a distinct `rate_proof_ref` for a numerical `rate_per_sim_minute`; numeric rates are suppressed as active measurements while the game is paused.

### Need-health evidence policy

- Each feed is bounded and requires current exact game build, Sim/profile identity, scene probe, independent source, capture/sample IDs, and age ≤60 seconds.
- Calibrated HUD source must prove calibration; native runtime source must identify a separately inspected real EA read hook. Static tuning XML or a game save can disclose **rules, tuning and historical state**, but not a simultaneously observed active motive trend.
- Two current observations that disagree on direction are **SOURCE_CONFLICT_REOBSERVE**; observations farther apart in time are asynchronous, not same-moment corroboration.
- Missing, stale or invalid feeds are isolated; the other healthy source can continue **advisory-only** detection. A source returning from DOWN/QUARANTINED needs an explicit `reset_ref` plus `reset_probe_passed`, followed by two distinct time-ordered samples before becoming HEALTHY. Replayed same-sample recovery fails closed.
- `game_paused=true` blocks claims of observed instantaneous rate, even if the last indicator shows a decline.
- Player activity wins. A descending Social signal invites diagnosis and safe native-affordance observation, not arbitrary cancellation of dancing, user interaction or queue items.

## Moodlets and favorable activity

The repository already has `betterinstincts/moodlets.py`, integrated in the regular host, which recognizes supplied anger/fear/discomfort and happy/playful moods. This fusion port **reuses it** rather than inventing another owner. A positive emotion can support **PRESERVE_POSITIVE_ACTIVITY_IF_NEEDS_SAFE**, but rapid Social decline yields **DECLINING_NEED_OUTRANKS_POSITIVE_MOOD**. Negative mood suggests review of relief options, constrained by urgently low motives and user intent. Unknown labels, including an unverified screenshot description of a "Cheerful Treat", remain unknown rather than automatically becoming a guessed Sims buff.

## MoonWake Sixth Gear / next real-game gate

P141 scoped strategies: six-need delta alone (misses Servo and direction), CV-only (uncalibrated and occlusion-sensitive), native-only (no installed game hook in GitHub lane), new daemon (unowned global scanning), typed dual-source existing-owner fusion (selected).
P95 implements source/provenance/health/moodlet state; P82 falsifies invalid profile, stale feed, opposite directions, no sensor, paused chevrons, reset replay, and player priority. P08 is **BLOCKED_LOCAL_GAME_ACCESS**. P07/P124 can validate remote code and merge independently of actual game certification, preserving original owners.

**P08 actual acceptance on a user-consented disposable Sims host:** identify installed game build, Discover University pack and exact native motive/buff API using read-only EA tuning inspection. Confirm two successive *unpaused* native values versus HUD arrows on the Servo; compare measured rate, source conflicts and recoveries; verify moodlet identities, user activity and no game/OS/save effects. Only then consider an actual native observer implementation and calibrated CV sensor. Respect independent BI-002 hunger gate and unrelated PR #159 spatial writer.

Background public reading: [SimsCommunity Servo mechanics](https://simscommunity.info/2019/11/15/the-sims-4-discover-university-all-about-servo/) and [Oops19 read-only TuningInspector](https://github.com/Oops19/TS4-TuningInspector).
