# Household upkeep — Servo four-motive health and bill-payment queue

**Status:** Offline host planning and observation, not live game automation or P08 gameplay certification.
Owners: betterinstincts/household_upkeep.py, contracts/household-upkeep.v1.json, and existing host_stack/host_listener, queue_capacity and budget_eval.
Consultation: contracts/consultations/BI-HOUSEHOLD-SERVO-BILLS-20261109.v1.json.

## Architecture and noninterference

On each ACTIVE opt-in host-listener tick, a bounded household_upkeep snapshot is evaluated independently of gardening, school, careers and aspirations. The monitor yields a separate servo_health list and bill_health status even when the player or another microsystem owns the screen. It returns at most one proposed queue action; it never calls SendInput, creates a polling daemon, changes saves or claims actual payment.

The result recommends the next observation in 30 seconds, but that value is NOT an automatically installed timer. The host listener's existing explicit activation/tick limits remain authoritative. Player activity, survival-critical human needs, Build/Buy, wrong viewport, overlays and career/school duties retain their host priority. No new agent may cancel the user's own queue. Critical Servo or overdue-bill work may outrank optional gardening only after these guards.

## Servo: four needs, two main maintenance owners

Servo needs are Durability, Charge, Fun and Social, not the human six-motive schema. Conservative policy defaults (not patch-certified EA tuning): Durability watch <=0.50 / critical <=0.20, Charge watch <=0.35 / critical <=0.15; Fun and Social watch <=0.35.

Durability low -> choose another eligible helper with an actually observed TUNE_UP_SERVO action targeting that exact Servo. Prefer HUMAN helpers first. When no HUMAN is available, a peer Servo (sim_ref != target) may be proposed only if its Robotics skill is verified at or above `servo_helper_policy.min_robotics_level` (default 3). If the only candidate helper is a Servo lacking verified Robotics, the gate is `UPKEEP_HELPER_SKILL_GAP` with a `diy_skill_force` servo_core hint — never invent panel PASS and never queue practice_skill. If broken, require the separate observed REPAIR_SERVO affordance. Charge low -> the Servo's own observed RECHARGE_SERVO interaction; do not misroute as human Energy. Low Fun -> observed SERVO_FUN_ACTIVITY by the Servo. Low Social -> observed SOCIALIZE_SERVO by an available human (HUMAN-only). PAY_BILLS remains HUMAN-only. Actor identity, queue, need urgency, player reservations and capacity all require fresh proof. Wet/water-exposed Servos hold unverified new actions and flag risk. Self Tune Up on the peer path is forbidden; Enhancement-3 self-maintenance stays a separate action_id. Exact live menu unlocks and salvage-parts cost are NOT assumed.

Unknown/offscreen Servos use needs_verified:false with needs:null; inventing four numeric values is forbidden. Monitoring all observed Servos is bounded to 16 entries per capture. No per-frame scans, arbitrary game-mode switches or autonomous resource purchases.

## Bills: observe -> affordable -> queue -> verify paid

An opt-in household_upkeep.bill identifies the exact bill_ref, independently verified UNPAID state, amount in simoleons, household_funds, due_in_sim_hours, and attempt lifecycle NONE|QUEUED|DISPATCHED. bill_payment_authorized:true is a required local-session opt-in. A bill is a recurring observed obligation, not an invented monthly/weekly timer or Build/Buy purchase.

Only when UNPAID, in the conservative <=72 Sim-hour lookahead, funds cover the observed amount, no attempt is pending, and a free HUMAN Sim has an actual enabled PAY_BILLS action does the planner propose ONE payment. Missing amount/affordability/actor/queue/menu -> hold and route a shortfall to the existing budget/income owner. No money cheats, bill cheating, or unapproved catalog purchases.

After enqueue, reobserve the exact actor queue and mark QUEUED. After executing the attempt mark DISPATCHED and DO NOT repeat on the same unpaid observation. A PAID flag alone is PAID_UNVERIFIED. Only PAID with payment_proof_ref and outcome_capture_ref establishes VERIFIED_PAID. Any action requires an independent local screen_admit handoff, current UI and actual host/game evidence.

## Input contract

Add household_upkeep under the existing host-listener observation alongside its ordinary six human needs and queue. Example below uses fictional refs and time 0, not a real observation:

```json
{
  "schema": "betterinstincts.household-upkeep/v1",
  "capture_ref": "capture:current", "observed_at_unix": 0,
  "household_verified": true, "scene_verified": true, "queue_verified": true,
  "bill_payment_authorized": true,
  "servos": [{"sim_ref": "servo:one", "needs_verified": true,
    "needs": {"durability": 0.18, "charge": 0.8, "fun": 0.8, "social": 0.8},
    "broken": false, "water_exposure": "NONE", "maintenance_attempt": "NONE", "charge_attempt": "NONE"}],
  "actors": [{"sim_ref": "sim:helper", "kind": "HUMAN",
    "available": true, "queue_verified": true, "player_reserved": false,
    "urgent_needs": false, "multitasking": false, "queue": []}],
  "observed_actions": [{"action_id": "TUNE_UP_SERVO", "actor_ref": "sim:helper",
    "target_ref": "servo:one", "capture_ref": "capture:current", "available": true}],
  "bill": {"bill_ref": "bill:current", "state": "UNPAID", "bill_verified": true,
    "amount": 300, "household_funds": 1500, "due_in_sim_hours": 10, "attempt": "NONE"}
}
```

One actor queue row contains action_id, origin (PLAYER/HOST/SIM_AUTONOMY/UNKNOWN) and optional target_ref. Unknown/player-owned queue entries hold new work. Existing queued action+target and per-target QUEUED/DISPATCHED attempts suppress duplicate proposals. Each selected action carries a deterministic proposal_key for the captured actor/target/action; this is NOT in-game proof.

## P08 live proof still required

The installed Sims build, real four-motive screenshot, actual eligible helper menu, exact Tune Up/Recharge/Repair effects, independent queue completion, bill UI and balance delta are not accessible from this GitHub lane. A local opt-in host runner must verify all of them under exact game version and player-idle control before any autonomous input. CI cannot certify these observations.

## Servo fire-risk laundry gate (2026-11-09)

Incident: a Servo with low Durability plus laundry (dryer lint) caused fires. `evaluate_household_upkeep` now returns `laundry_policy` (advisory, `dispatch_authorized=false`) from `contracts/household-upkeep.v1.json` `servo_fire_risk`:

- **Durability first:** a BROKEN Servo or durability at/below `durability_critical` -> `BLOCKED_REPAIR_FIRST` (prerequisite `REPAIR_SERVO` / `TUNE_UP_SERVO`, reobserve before laundry). Unverified durability -> `HOLD_DURABILITY_UNVERIFIED`; stale capture -> `HOLD_REOBSERVE_STALE`.
- **Clothesline over dryer when unsupervised:** `USE_CLOTHESLINE` when `laundry.clothesline_available`.
- **Dryer lint:** unsupervised dryer is forbidden unless the Lint-Less Handiness upgrade is installed (`DRYER_ALLOWED_LINT_LESS`), otherwise `HOLD_UNSUPERVISED_NO_LINT_LESS`; a supervised dryer needs a clean lint trap (`CLEAN_LINT_THEN_DRYER_SUPERVISED`).
- Optional observation `laundry`: `{supervised, clothesline_available, dryer_lint_state: CLEAN|DIRTY|UNKNOWN, lint_less: INSTALLED|NOT_INSTALLED|UNKNOWN}`. Missing data is treated as unsupervised/unknown (fail closed).

Proof ceiling `OFFLINE_SERVO_FIRE_POLICY_NOT_LIVE_FIRE_PREVENTION_PROOF`; Lint-Less/clothesline availability is observation-gated (pack and Handiness dependent).

## 2026-11-12 — Cooperative Servo maintenance and Gardener-Bot care

**Authority:** existing `household_upkeep` is still the one read-only
orchestrator. `contracts/household-upkeep.v1.json` now includes the
`utilibot_policy` and stronger `servo_helper_policy`; no new daemon,
per-frame hook, desktop clicker, EA script or installed mod is introduced.

**Actual game basis:** Discover University Servos have four needs:
**Charge, Durability, Fun, Social**. Servos can recharge themselves and
enhanced Servos may self-tune; other Sims perform ordinary Tune Ups.
Fix-O-Matic is a selectable enhancement module that can autonomously repair
objects and broken Utili-Bots, including Gardener-Bots. Its vanilla tuning
can also cause **excessive peer tune-ups**, so this new policy deliberately
restricts proactive Tune Ups to targets at or below verified **0.50**
Durability and never duplicates QUEUED/DISPATCHED work. All values are
offline hypotheses until the exact EA build is inspected. References:
[Sims Community Servo guide](https://simscommunity.info/2019/11/15/the-sims-4-discover-university-all-about-servo/),
[Robotics deep-dive](https://simscommunity.info/2019/11/09/discover-university-everything-we-learned-from-the-deep-dive-livestream/)
and [excessive Fix-O-Matic tune-up research](https://modthesims.info/d/686077).

**New planner flow**, bounded to the already-authorized observation tick:

```
fresh verified household + active Live scene + known queue origin
  -> Servo rows (all four real motives; broken, wet, maintenance attempt)
  -> Utili-Bot rows (exact bot ID/type; Charge and Durability only)
  -> independently rank Servo/Bot critical damage, charge and watch candidates
  -> inspect active household helpers, observed Robotics/module and own reserves
  -> prefer qualified Servo peer, else a verified human helper
  -> exact current actor->target observed enabled menu + free queue
  -> at most one advisory proposal; separate local input approval stays DENIED
  -> reobserve outcome and attempt before proposing again
```

Servo peers only help other robots when their **own** Servo four-motive
snapshot is verified, not broken/wet, and Charge >=0.45 and Durability >=0.35;
human household members remain the fallback. Their Robotics level must be
explicitly verified >=3 or, for **repairing a broken Utili-Bot only**, their
Fix-O-Matic module must be confirmed enabled and verified. These numeric
levels are local policy hypotheses, not asserted EA unlock levels.
Regardless of skill/module, the current actor-target action must actually
be observed available; a module name alone never grants an execution permit.
When a Servo needs to recharge, its own observed RECHARGE_SERVO action is
eligible at Charge <=0.45; this is proactive reserve management during
normal host ticks, not an invented continuous schedule. A peer may help a
Servo with Social only with a verified observed interaction and safe reserves.
A Servo's separately observed SERVO_SELF_TUNE_UP requires confirmed self-tune
enhancement, safe charge, and no competing peer path; it is never confused
with an actor helping itself via TUNE_UP_SERVO.

**Gardener-Bot and other Utili-Bots:** `observation.utilibots` is an optional
list (maximum 16). Each row has `bot_ref`, one of `GARDENER_BOT`,
`CLEANER_BOT`, `FIXER_BOT` or `PARTY_BOT`, `needs_verified`,
`broken`, `water_exposure`, `needs` with *exactly* Durability and
Charge when verified, plus `maintenance_attempt` and `charge_attempt`
in NONE/QUEUED/DISPATCHED. Unknown motives require `needs:null`;
never replace them with a human or Servo profile. Repair candidates require
broken:true and observed `REPAIR_UTILIBOT`. Watch Durability <=0.50
uses observed `TUNE_UP_UTILIBOT`; Charge <=0.45 uses observed
`RECHARGE_UTILIBOT`. The exact form/availability of charging is game
and menu dependent—do **not** infer a charger, purchase one, or automatically
place a station. Wet/RISK bots are held for player review.
These semantic action IDs are *not* EA tuning IDs.

**Candidate states and safety:** existing `candidate_count`, one-action
`next_actions`, `proposal_key`, `servo_health` and bill/laundry
outputs are preserved. New `utilibot_health` reports each object even
while screen work is player-owned. Bot recommendations contain
`target_kind`; robot helpers include `helper_kind` and an explicit
`helper_qualification`. The queue and independent post-action observation
still own execution and completion evidence. A recommendation alone never
means a Servo was maintained, a Gardener-Bot repaired or a battery charged.

**P95/P82 acceptance and falsifiers:** prior policy had only Servo targets,
a human-first helper list and Charge watch 0.35. The strengthened target
supports four typed Utili-Bots, cooperative Servo-first fallback, self-care
reserves and earlier Charge watch 0.45. Its tests must reject missing
helper motive proof, bad module evidence, unsafe charge, unsupported bot
need schema, water, stale menu, duplicate queued/dispatched attempts and any
player override; normal Servo health, bill payment, laundry fire policy,
existing need services and host listener remain regression controls.

**P08 still OPEN:** Genuine Sims 4 local proof requires exact patch +
Discover University, a disposable household with two Servos and a
Gardener-Bot, fresh enabled interaction menu evidence, helper battery and
Robotics/module panel, a controlled peer Tune Up and Gardener-Bot
repair/charge, independent observed post-action meter/object deltas, no
player queue interruption, vanilla-versus-modified comparison and rollback
where a native mod is eventually introduced. This source-only policy is
not an EA-native playable autonomy change and cannot complete BI-002.
