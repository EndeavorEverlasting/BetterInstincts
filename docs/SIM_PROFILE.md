# Active Sim profile inspection — P95 host sensing

Machine owner: [`contracts/sim-profile.v1.json`](../contracts/sim-profile.v1.json).
Evaluator: `python -m scripts.sim_profile` / `betterinstincts.sim_profile`.
Integrated by: `host_stack.evaluate_turn(..., traits=, skills=, likes=, …)` as read-only `sim_profile`.

## Design brief

- **Subject:** The active Sim’s character panels — skills, likes/dislikes, traits, aspiration, whims — composed with the moodlet strip.
- **Audience:** Players who notice a desire (e.g. gardening) in moodlets without knowing where personality/skill truth lives; local host agents that must not invent that truth.
- **Job:** Durable discovery + normalized host inspection. Not a second Sims UI; not BI-005 skill practice.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-0F2FB5920`, `UP-1B0AFA8BE`, `UP-40FE662CF`.

## How to check as a player (discovery map)

| Surface | Where in HUD | What it answers |
| --- | --- | --- |
| Moodlet strip | Bottom-left portrait icons | Temporary buffs / some activity cues (what you already noticed) |
| Whims / desires | Desire cards near needs (pack-dependent) | Short-term wants (“garden”, etc.) |
| Simology | Sim Info → Simology | Traits, aspiration, life stage |
| Skills | Sim Info → Skills | Current skill **levels** (reading ≠ growth cert) |
| Likes & Dislikes | Simology-adjacent Preferences | Stable activity preferences |
| Needs | Bottom-right meters | Survival still outranks hobbies |

## Call-stack role

```
player HUD panels (supplied labels)
  -> sim_profile.evaluate_sim_profile
  -> moodlets.evaluate_moodlets (composed, not duplicated)
  -> host_stack.out["sim_profile"]  # read-only attachment
  -> gate SIM_PROFILE_INSPECT (advisory; never practice_skill)
```

Name collisions avoided:

- **This feature** = Live Simology / skills / preferences inspector.
- `select_sim_to_play` = household picker on Load Game.
- Compatibility **patch** profiles = `compatibility/` game builds.

## P82 admission

- **Hypothesis:** Composing supplied skills/preferences/whims with moodlets explains gardening-class desires without vision invention.
- **Falsifier:** Profile report invents labels, queues `practice_skill`, or claims BI-005 / skill-growth proof.
- **Measure:** Contract load + SENSOR_NOT_SUPPLIED + gardening evidence match + host_stack attachment + doctrine paths.

## Proof ceiling

`SUPPLIED_SIM_PROFILE_OBSERVATIONS_NOT_VISION_API_NOT_BI005`. Missing inputs ⇒ `SENSOR_NOT_SUPPLIED`. Does not close BI-002, BI-005, or rewrite EA personality systems.
