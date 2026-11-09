# Autonomy, off-screen Sims and top-left Discovery Quests

## Decision / ownership

**Existing host surfaces remain authoritative:** `task_continuity` owns target evidence, `gardening_service` owns its next observed plant interaction, `host_listener` owns opt-in observations, `player_presence` and `workflow_interop` own the idle/input lease, `ui_microsystems` owns semantic panel identifiers, and `screen_atlas` owns native hitbox admission. No duplicate listener, autonomy replacement engine or blind cancellation loop.

### Game setting is context, not an override

The Sims 4 gameplay menu offers autonomy Full/Off and a selected-Sim exemption in supported builds. The host accepts the **observed** setting as an input to moderation, but never changes it. Full autonomy doesn't void player goals; Off doesn't prove every queued action was user-authored. Conflicts are reobserved. The source-only program cannot certify which interactions run while a Sim is unselected. Different game patches may change behavior; local lab P08 is required.

### Off-screen household Sim continuity

```text
Sim Tim: user queues fertilization for plants A/B/C
    → switch selected portrait to Sim Alex
    → selected_sim_continuity gates Tim to SIM_NOT_SELECTED
    → persist goal/target evidence only in caller's existing bounded task state
    → DO NOT assume Tim's queued game actions continued or failed
    → when Tim is reselected: require independently verified portrait+queue
    → task_continuity picks first not-verified-done target from fresh observation
    → gardening_service plans at most one exact-target visible action
    → independent screen_admit and resulting in-game outcome remain mandatory
```

`selected_sim_observation` is optional in the existing `gardening` payload; when supplied with `task_continuity` it gates the pre-existing path, including when another household Sim is selected. Legacy gardening without these fields is unaffected. The evaluator does not auto-select Tim or inspect private background processes.

### Positive whims are *opportunities*, negative actions are *queue observations*

`autonomy_moderation` accepts bounded per-Sim observations with current actor/queue proof, an observed autonomy setting, actions carrying an independently grounded origin/effect, and optional wishes/whims carrying benefit proof.

- **Positive whim:** only an observed, beneficial and enabled candidate, and only when no ongoing player goal or queue would be preempted. The result is a **queue candidate** (not an actual queued interaction).
- **Harmful action:** only `SIM_AUTONOMY` with an observed `RELATIONSHIP_HARM` or `ENVIRONMENT_HARM` effect, exact queue-slot reference, provenance/effect evidence, selected Sim and explicit moderation opt-in. The result is **one cancellation proposal**, never direct cancellation, and the host needs independent live scene/click arbitration, human inactivity and post-effect verification.
- **Protected/unknown:** player entries, goal-related actions, unidentified provenance, unselected Sim, settings/queue contradiction, player input, critical needs and imminent obligations cannot be canceled. A generic chat, use of phone or unliked whim is not by itself a negative action. No repeated auto-retry.

**Consumer boundary:** optional `autonomy_observation` can be supplied through the current gardening object, reusing the existing listener/stack. Non-gardening use is pure read-only service until another domain integrates it. No host input adapter or persistent data store is installed.

### Top-left Discovery Quest micro-router

`discovery_hud.evaluate_discovery_hud` is a separate **panel-classification/routing** layer:

| Verified active quest | Canonical owner | Behavior |
| --- | --- | --- |
| **Navigating Needs** | `navigating_needs` | Reuses observed incomplete goals and current six motives |
| **Scoring Simoleons** | `scenario_goals` | Reuses earned-income/crafting goal catalog; no cash cheat |
| **You and Your Phone** | observed phone-menu affordances | Plans one *exactly matched visible/enabled* action; never invents texts, calls, travel or entitlements |
| Skillful Sims / Lifelong Aspirations / Always on the Move | future existing domain peers | Identified but no invented click |

This is **Discovery Quest** provenance; don't confuse it with a social event, scenario screen, aspiration panel or unrelated top-left overlay. Requires verified Live Mode, scene, panel, selected Sim, fresh capture and observed incomplete goals. The `top_left_discovery` entry in `contracts/ui-microsystems.v1.json` exposes semantic inspection slots, explicitly uncalibrated until local P08 target measurement. **No input permit or claim of an actual goal tick.**

## P95 / P124 / Trifecta gates

P95: the call stacks and explicit absence-of-evidence states above. P124: isolate pure components and reuse old owners. P82: unit/falsifier tests for cross-Sim corruption, provenance, positive whims, goals and stale capture. P07: CI, ontology consulted before source mutation, branch integration. P08 remains **open**: exact game build, disposable approved lab save, live player/queue observation, verified queue cancel/goal resolution, reversible rollout and no regression to hunger BI-002. Offline PASS is not a playable mod or an installed options UI.

### Already-realized harm is a different recovery lane

If independent evidence shows an autonomous action **already** caused a relationship/environment cost, a queue cancel cannot reverse it. The moderation evaluator can instead propose one currently observed, target-matched, enabled repair/apology/cleanup affordance with an opt-in policy, current actor/capture evidence and no input permit. Even a successful attempt requires independent proof of the resulting relationship or environmental state; never claim harm was erased merely because an apology/repair was queued. A player-authored harmful act is never silently undone.
