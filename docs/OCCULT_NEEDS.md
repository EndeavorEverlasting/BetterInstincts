# Occult-aware needs catalog and reviewed local learning

**Status:** offline, advisory-only. **Parent:** BI-002 hunger certification is still ACTIVE.
The purpose is a typed extension of the existing six-need microsystems, **not** a
second game controller, a new per-frame scanner or a blanket claim that every
occult has six motives.

## Source ownership and scope

- Catalog: [contracts/occult-needs.v1.json](../contracts/occult-needs.v1.json).
- Pure policy: [betterinstincts/occult_needs.py](../betterinstincts/occult_needs.py).
- Existing six-need decisions: `need_services`, `need_service_base`,
  `need_load_balance`, `need-lanes.v1.json` and `fun-service.v1.json`.
  The catalog **references** these action IDs; it does not replace the existing
  lane optimizer, health check, ownership admission or Fun preference model.
- Reviewed demonstrations: `judgment_learning` remains the general-purpose
  contextual learner. This module stores **motive-specific** reviewed successes
  and failures without altering the general learner or automatically capturing
  input. The two models are independent advisory sources, not competing live
  actuators.
- Game implementation owner: existing [native gameplay authority](NATIVE_GAMEPLAY_ARCHITECTURE.md).
  No unproven EA tuning identifiers, embedded Python hooks or UI click authority.

## Motive sets and safety semantics

| Profile | Observed/expected motives in this **candidate catalog** | Separate handling |
| --- | --- | --- |
| Ordinary human / alien / spellcaster / werewolf | Bladder, Hunger, Energy, Hygiene, Fun, Social | Spellcaster Charge and werewolf Fury are auxiliary risk/ability meters, not assumed positive-recovery needs |
| Vampire | Bladder, Thirst, Vampire Energy, Hygiene, Fun, Social | Thirst and power actions require local menu evidence; drinking from another Sim is PLAYER_ONLY |
| Mermaid | Bladder, Hunger, Energy, Hydration, Fun, Social | Hydration replaces Hygiene; confirm actual panel and available water actions |
| Fairy | Energy, Hygiene, Fun, Social, Emotional Force | **No Hunger/Bladder.** Regeneration and Absorb Emotion are distinct remedies |
| Servo | Fun, Social, Durability, Charge | **No Hunger/Bladder/Hygiene.** Self-tune-up needs an observed enhancement/capability; water is a risk, not a recovery action |
| Ghost / temporary PlantSim / skeleton / unknown hybrid | No default invented motive mapping | `LOCAL_MOTIVE_SCHEMA_REQUIRED`: abstain until exact patch and actual panel validated |

The candidate types above are **exact schemas**; a caller must supply the
current, complete motive panel. No missing value is filled with a human default.
Pack entitlement is explicitly supplied, never inferred from Sim appearance or
file names. The Fairy-specific substitutions and emotion actions are documented
in the [EA Fairy guide](https://help.ea.com/en/articles/the-sims/the-sims-4/fairy-guide/).
The Servo four-motive taxonomy and vulnerability are described in
[Sims Community's Discover University guide](https://simscommunity.info/2019/11/15/the-sims-4-discover-university-all-about-servo/).
All non-EA action labels remain hypotheses until corroborated on the exact
installed build, including localizing menus, object eligibility and pack behavior.

Action lists live **per motive**, not per skill progression subsystem. A skill
may contribute an affordance to a need (for example, a cooking activity serving
Hunger), but actually training Cooking or advancing a career remains governed
by BI-005/BI-006. No training action bypasses unmet survival needs.

## Mathematical controller (pure policy)

Let `x_n∈[0,1]` be a verified observed value of motive `n`. A motive
is actionable only while `x_n < 0.55`; candidates are visited by ascending
`x_n` (larger deficit `1-x_n` first), preserving catalog order on ties.
The thresholds are inherited from `contracts/needs.v1.json`; no new independent
need thresholds are introduced.

Every candidate must first be in the **current observed menu/action set** and
pass pack, capability, player-activity and profile gates. If action `a` has
reviewed helpful count `h` and harmful count `d`, a smoothed within-motive
estimate is

`p(a | profile, patch, motive) = (h + 1) / (h + d + 2)`.

This estimate affects **only which observed remedy for the same current motive**
comes first. It becomes a ranking signal only with `h+d >= 3`, `h >= 3`,
and `h/(h+d) >= 0.75`. If `d >= 1` and `h = 0`, the candidate is
suppressed until independent reviewed evidence justifies revision.
Neither a high posterior nor a low meter grants gameplay authority.

A helpful observation additionally requires measured `Δx = after-before >= 0.02`
**and** explicit operator review. A harmful judgment may capture an adverse side
effect even when the measured meter increased. These are bounded associations,
**not randomized causal inference**; direct local A/B controls must still
validate actual gameplay benefit.

## Call stack and portable persistence

```
explicit Sim type + installed packs + exact patch + observed motive panel
  -> load_catalog / exact typed profile and range validation
  -> player-first/scene/capability gates + action availability
  -> preemptive motive priority
  -> optionally inspect reviewed model for same profile + patch + platform
  -> action recommendation (execute=false) OR ABSTAIN
  -> separate existing native/human control admission, never auto-queue
```

The `new_model` and `learn` functions return plain JSON-compatible,
**in-memory** objects. A user can intentionally serialize them in an explicitly
chosen, local application profile in a future approved host integration; this
module neither chooses nor writes a path. Each model contains at most 128
distinct opaque review references (no raw screenshots or identity), and rejects
replayed references, malformed legacy data, mismatched versions, unsupported
actions and unreviewed training. Saturation denies additional learning rather
than discarding replay evidence and silently retraining it.

Example from a **repository checkout** (evaluation only):

```python
from betterinstincts.occult_needs import recommend

snapshot = {"bladder": .9, "hunger": .1, "energy": .8,
            "hygiene": .8, "fun": .8, "social": .8}
result = recommend("human", snapshot, ["QUICK_MEAL", "COOK_MEAL"],
                   game_version="1.121.361.1020", platform="windows")
assert result["state"] == "ADVISORY" and result["execute"] is False
```

## P95 → P82 → P08 → P07 → P124 evidence gates

- **P95 architecture:** retain one owner for ordinary six-need planning; profile
  wrapper, explicit action availability and existing source IDs are the new seam.
- **P82 falsifiers:** unknown profiles, wrong pack, stale patch, wrong meter
  shape, NaN, player activity, consent-gated actions, evidence replay, harmful
  experience and unobserved actions must not produce executable effects.
  Tests measure all of these offline.
- **P08:** real local Sims 4 build + installed packs, player-first gate and
  disposable save observations remain **NOT_RUN** in provider-only execution.
  Do not pretend Python unit tests are live trials.
- **P07:** bounded consultation-before-code, unit tests, native-route
  classification, PR checks and provider-verified integration.
- **P124:** maintain one action registry and profile schema, no copied
  six-need controller, no extra writer/daemon or host input hook. A later change
  to native behavior needs EA-source evidence and separate local trials.

**Local next gate:** compare panel motive sets, normalized observation values,
actual action availability/effect and player queue control for a human, Fairy,
Servo, Vampire and Mermaid on the installed patch; record safe pack-specific
fixtures, and separately complete BI-002 vanilla/modified hunger 5+5 plus
rollback before claiming native behavior improvements.

## Rollback

Revert the policy+catalog branch; there are no game mods, user saves,
external settings, profiles or processes to remove.
