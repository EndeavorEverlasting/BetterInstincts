## Career-event autonomy is a separate peer lane

This document's sticky teen-homework service is unchanged. For **adult/part-time career chance cards**, follow [CAREER_DECISIONS.md](CAREER_DECISIONS.md) → `contracts/career-decisions.v1.json` → existing `career_service.evaluate_career_event_turn`. For rabbit-hole **Work Hard** tone and portrait handoff, use [CAREER_PERFORMANCE.md](CAREER_PERFORMANCE.md). The Career HUD is Live panel J, but chance-card response IDs come from exact dialog tuning/event observation, not bottom-right panel coordinates. These routes are in four compact [glossary](GLOSSARY.md#career-and-work-routing) terms; agents only demand-load the relevant detailed contract. An installed native event handler remains distinct from pure policy and current game P08 has not been proved here.

# Career service — async microsystem (P95)

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**Provenance:** `spec-architecture-prompts.v1.json` blob `5926a198a14567de55110ed19e922fc444b4dec7`
**Machine owner:** [`contracts/career-service.v1.json`](../contracts/career-service.v1.json)
**Evaluator:** `betterinstincts.career_service` / `python -m scripts.career_service`
**Lane note:** [`CAREER_PERFORMANCE.md`](CAREER_PERFORMANCE.md) (BI-006-adjacent scaffolding, not certification)

## Design brief

- **Subject:** Career-panel duties as a peer microsystem beside need services — starting with teen **High School Student** daily **homework**.
- **Audience:** local host agents that otherwise stay stuck in needs and forget schoolwork.
- **Job:** Keep a sticky `CAREER_OBLIGATION` alive across survival suspensions; evaluate every observation in tandem with `need_services`; resume homework policy only when survival is green and premises allow.
- **Architecture:** Thin continuity/orchestration seam over existing `teen_homework` / `school_day` / `scenario_goals` owners — not a second homework planner, not a daemon, not adult promotion proof.
- **Upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-40FE662CF`.
- **Not:** BI-006 GAME_CERTIFIED career advancement; inventing inventory; background scanners; overriding player queues.

## Why this exists

Need microsystems already load-balance in tandem. Career was only a cascade poll / one-shot host gate, so agents recovered hunger/energy and dropped the teen's daily homework. Ontology already requires `GOAL_THREAD` continuity across interruptions; this microsystem is that continuity for career-panel work.

## Microsystem states

| State | Meaning |
| --- | --- |
| `IDLE` | No career obligation attached |
| `TRACKING` | Obligation held; not yet actionable (queue/needs peers still busy) |
| `SUSPENDED_FOR_SURVIVAL` | Hunger/bladder/energy critical — hold obligation, do not queue homework |
| `PREMISES_BLOCKED` | At school / school day — hold obligation |
| `READY` | Survival green at home — resume teen_homework policy lanes |
| `YIELDED` | Player-first / busy — preserve tracking if already obligated |
| `COMPLETE` | Explicit `homework_pending=false` (book presence alone never reopens) |

## Success call stack (evaluate-only)

```
observation (+ optional prior career_service state)
  -> career_service.evaluate_career_service
       attaches high_school_student when teen homework/school signals present
       carries sticky obligation from prior_state when still pending
  -> delegates READY lanes to teen_homework (and school_day when active)
  -> host_stack surfaces career_service even when next_gate is survival/needs
  -> domain_cascade career receipt cites career_service
  -> host_tandem emits CAREER_OBLIGATION_HELD while needs/garden run;
       after survival recovers, CAREER_READY_HANDOFF before gardening resume
```

## Failure call stacks

| Failure | Host response |
| --- | --- |
| Survival critical | `SUSPENDED_FOR_SURVIVAL` + `obligation_held=true` |
| Premises / school day | `PREMISES_BLOCKED` + hold |
| Player directed / busy | `YIELDED`; do not authorize career clicks |
| homework_pending=false | `COMPLETE` / clear — never reopen from book metadata |
| Missing prior + no signals | `IDLE` |

## Module map

| Module | Responsibility | Side effects |
| --- | --- | --- |
| `career_service` | Sticky obligation, tandem state, compact receipt | none |
| `teen_homework` | Homework recovery / queue policy | none |
| `school_day` | In-school goal catalog | none |
| `host_stack` | Always expose attached career_service beside need_services | none |
| `domain_cascade` | Career domain polls via career_service | none |
| `host_tandem` | Async observe events + career handoff after needs | none |

## P82 admission

- **Hypothesis:** Sticky career obligation evaluated every tandem tick prevents agents from forgetting teen homework after survival preemption, without letting career outrank critical needs.
- **Baseline:** host_stack/domain_cascade call teen_homework only when that gate wins `next_gate`; suspended turns lose career visibility.
- **Falsifier:** Dropping `obligation_held` while `homework_pending=true`; queuing homework under survival-critical needs; reopening completed homework from book tokens alone.
- **Measure:** `tests/test_career_service.py` + host_tandem career continuity cases.

## Proof ceiling

`HOST_CAREER_MICROSYSTEM_TANDEM_NOT_DAEMON_NOT_BI006_CERT`. Live homework completion remains OPEN (P08). Does not close BI-002 or BI-006.

## Civil Designer Eco-Invention drafting

[EA's career guide](https://help.ea.com/en/articles/the-sims/the-sims-4/the-sims-4-civil-designer-career/) identifies the Electronic Drafting Tablet as a level-2 reward and Draft Eco-Invention Concept as a Green Technician rank-4 unlock. The rank-4 daily task is Fabricate an Eco-Upgrade Part. The drafting route requires a separately observed, pending Eco-Invention objective. The operator's catalog observation shows the tablet at §0. Recheck the live listing.

1. In Live Mode, use the canonical **I** hotkey to open the active Sim's personal inventory. Confirm the panel after pressing it. With the inventory unfiltered, scan from top to bottom using fresh list bounds and the current layout and selected-Sim revisions. One step requests one scroll with its current cursor point. A repeated page, gaps in coverage, or a 24-page cap leaves the search inconclusive.
2. Recover the exact Electronic Drafting Tablet from the current lot if the household owns it and pickup is available. Check household storage and consult the last verified lot and object identity before replacing the tablet. Review a known prior lot through the existing travel owner if appropriate. Reobserve there before treating a tablet as a current-lot target.
3. If owned routes are exhausted and catalog recovery is enabled, enter Build/Buy and search **tablet**. If the exact tablet is verified locked or missing, the opt-in cheat route submits **testingcheats true**, **bb.ignoregameplayunlocksentitlement**, then **bb.showhiddenobjects**, one line and one acknowledgement at a time. The recorded order is an operating sequence. Runtime evidence of a required order remains open. Close the console, refresh the search, and verify the exact name, §0 price, placement, and full-lot My Library checkpoint. Buy and place a single tablet. Observe the placed object, return to Live Mode, move it to the same Sim's personal inventory, and confirm ownership there.
4. Select only the exact enabled **Draft Eco-Invention Concept** on that object. Check for an existing queued draft. Reconcile the dispatched effect before requesting any further step, including when the player takes over or the game changes scenes. Verify an actual blueprint and objective progress separately.

The `career_drafting` sidecar passes through the existing host listener with independently classified mode and matching game version, actor, lot, and listener session. Its `betterinstincts.career-drafting/v1` envelope binds `game_build`, `session_ref`, `save_ref`, `household_ref`, `sim_ref`, `objective_ref`, `lot_ref` and `capture_ref`. The current inventory, object, interaction, and catalog observations repeat those scope fields. For Build/Buy, carry the prior `OPEN_BUILD_BUY_FOR_TABLET` advisory as `replacement.live_search_receipt` with a distinct Live capture. An attempted effect is pending until its actual outcome is observed. Keep the native action, UI calibration, and effect receipts private.

Run `python -m scripts.career_service --drafting-observation OBSERVATION.json --observed-mode LIVE` to inspect a fresh observation. For catalog evaluation, supply the observed Build/Buy mode and `--drafting-lot-model LOT_MODEL.json`. This evaluator and listener are advisory. Issue #171 owns exact-build EA object, interaction and effect binding and authorized local play proof. Screen actions use the existing lab admission path.
