# Household upkeep — Servo four-motive health and bill-payment queue

**Status:** Offline host planning and observation, not live game automation or P08 gameplay certification.
Owners: betterinstincts/household_upkeep.py, contracts/household-upkeep.v1.json, and existing host_stack/host_listener, queue_capacity and budget_eval.
Consultation: contracts/consultations/BI-HOUSEHOLD-SERVO-BILLS-20261109.v1.json.

## Architecture and noninterference

On each ACTIVE opt-in host-listener tick, a bounded household_upkeep snapshot is evaluated independently of gardening, school, careers and aspirations. The monitor yields a separate servo_health list and bill_health status even when the player or another microsystem owns the screen. It returns at most one proposed queue action; it never calls SendInput, creates a polling daemon, changes saves or claims actual payment.

The result recommends the next observation in 30 seconds, but that value is NOT an automatically installed timer. The host listener's existing explicit activation/tick limits remain authoritative. Player activity, survival-critical human needs, Build/Buy, wrong viewport, overlays and career/school duties retain their host priority. No new agent may cancel the user's own queue. Critical Servo or overdue-bill work may outrank optional gardening only after these guards.

## Servo: four needs, two main maintenance owners

Servo needs are Durability, Charge, Fun and Social, not the human six-motive schema. Conservative policy defaults (not patch-certified EA tuning): Durability watch <=0.50 / critical <=0.20, Charge watch <=0.35 / critical <=0.15; Fun and Social watch <=0.35.

Durability low -> choose another eligible HUMAN Sim with an actually observed TUNE_UP_SERVO action targeting that exact Servo. If broken, require the separate observed REPAIR_SERVO affordance. Charge low -> the Servo's own observed RECHARGE_SERVO interaction; do not misroute as human Energy. Low Fun -> observed SERVO_FUN_ACTIVITY by the Servo. Low Social -> observed SOCIALIZE_SERVO by an available human. Actor identity, queue, need urgency, player reservations and capacity all require fresh proof. Wet/water-exposed Servos hold unverified new actions and flag risk. Self Tune Up, required Robotics level, salvage-parts cost, and menu unlocks are NOT assumed.

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
