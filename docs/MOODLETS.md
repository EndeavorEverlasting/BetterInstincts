# Moodlets & emotion strip — P95 host sensing

Machine owner: [`contracts/moodlets.v1.json`](../contracts/moodlets.v1.json).
Evaluator: `python -m scripts.moodlets` / `betterinstincts.moodlets`.
Integrated by: `host_stack.evaluate_turn(..., emotion=, moodlets=)` and `event_balance`.

## Design brief

- **Subject:** Bottom-left Sim portrait emotion + moodlet icons.
- **Audience:** local host agent mid-Live.
- **Job:** Stop ignoring moodlets that steer autonomy and pressure needs; fold them into the same call stack as events/needs/homework.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-40FE662CF`.
- **Not:** a trained screenshot classifier. Labels are **supplied** (operator note or future trusted sensor).

## LOCAL_OBSERVED gap (2026-11-07)

Lounge party HUD showed **VERY ANGRY** with scared / angry / uncomfortable moodlets while socials routed outdoors in rain. Host logic previously saw needs meters only. Capture: `operator:event-outdoor-social-20261107`.

## Call-stack role

```
viewport / player
  -> survival needs (bladder/hunger/energy meters)
  -> moodlet-aware routing (tense outdoor social => reinforce EVENT_INDOOR_ROUTING)
  -> event goals / Fun-via-goals
  -> homework hold
  -> other needs
```

`TENSE_MOOD_OUTDOOR_SOCIAL` (angry/scared + outdoor prefix + indoor capacity) strengthens cancel-outdoor / retarget-indoor. `uncomfortable` aligned with low bladder/hygiene prefers toilet/wash before more greet spam.

## Proof ceiling

`SUPPLIED_MOODLET_OBSERVATIONS_NOT_VISION_API`. Missing strip ⇒ `SENSOR_NOT_SUPPLIED`. Does not certify BI-002 or rewrite EA buffs.
