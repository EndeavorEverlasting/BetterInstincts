# BetterInstincts: canonical agent entrypoint

Before edits, samples or experiments, read mandatory `docs/AGENT_OPERATING_RULES.md`, `docs/ONTOLOGY.md`, `docs/DOCTRINE.md`, `docs/LEDGER.md` and `docs/PROMPT_INVOCATIONS.md`. Commit `contracts/consultations/` before behavior changes; run `scripts/semantic_preflight.py`. Detailed rules are preserved, not waived.

## P00/P01 interaction sovereignty

Ontology revision 6: human input anywhere (game, mod, keyboard, mouse, voice or other app) outranks agents. `contracts/effect-authority.v1.json` separates reviewed read-only background work from screen/game effects (15s idle, fresh dual probes before/after focus, scene/save/target recheck) and OS/unknown effects (deny). Retain interrupted intent, reconcile outcomes, never blindly replay. Never change Bluetooth, Print Screen, Escape/U, drivers, accessibility or Windows settings. Run `scripts/check_human_sovereignty.py`. Unadopted tools and mid-call actions remain unproven.

## Windows peripheral authority boundary

`contracts/peripheral-authority.v1.json` and `scripts/check_peripheral_boundary.py` deny game agents Windows Bluetooth service, driver, pairing and input-preference changes. Idle/player permits never grant OS repair authority: route incidents to SysAdminSuite Field Workflow. Run the checker and `tests.test_peripheral_boundary` with ontology preflight; see `docs/PERIPHERAL_INCIDENT.md`.

## Invariants

- **Player first:** explicit user control wins; no uncontrolled loops. Preserve any chosen interaction shape.
- **Save-safe:** Unknown/user saves protected. Never edit/delete/migrate/overwrite saves or game files; never delete Slot_00000007.
- **Build structure / FLOOR_2:** before any Build/Buy purchase or mutation, census all floors/rooms, back up to My Library and verify model readback. Retain `admit_live_structure_effect`; unknown coverage denies. Details: docs/BUILD_LIBRARY_CHECKPOINT.md.
- **Storage:** no arbitrary profile writes, auto-discovery, daemons, telemetry or unbounded logs.
- **Performance:** bounded work; no per-frame global scans or unmeasured hooks.
- **Evidence:** separate tests, build, PR, merge and gameplay. docs/SCENE_INTELLIGENCE.md owns independent cues; unknown denies.
- **Continuity:** preserve intent and update docs/LEDGER.md, docs/ROADMAP.md and active sprint; no chat-only corrections.
- Offline installation only; never EA Connect. Preserve lot-boundary, EA-file-first geometry and live-host policies in the mandatory detailed rules.

P00/P01 world-traversal: see `docs/WORLD_TRAVERSAL_HARNESS.md`; BI-002 remains active.

## Existing operator/agent handoffs

- Judgment P04: `docs/handoff/BI-JUDGMENT-LEARNING-P04-2026-11-07.md`.
- Cursor pre-effect guard: `.cursor/hooks.json` → `.cursor/hooks/operator_boundary.py` (`contracts/operator-desktop-boundary.v1.json`). No agent may disable, dodge or remove the guard. Hooks must activate locally; separate tools need separate enforcement.

## Trajectory and proof

plans/active/BI-001.md is merged; plans/active/BI-002.md owns the game-lab gate. docs/HORIZON.md and plans/horizon.v1.json retain six needs, balance, income, skills and career order. docs/COMPATIBILITY.md and docs/LIVE_CERT.md require exact game build and immutable older certifications. BI-002 requires actual vanilla/modified trials and rollback; absent host means BLOCKED_LOCAL_GAME_ACCESS, active rather than complete. Report CHANGED | PROVED | NEXT, checks, SHA, push/PR/merge and actual live status. An offline pass is not gameplay proof.

## P00/P01 navigation law

For deterministic household region traversal and no-progress loop recovery consult `docs/HOUSEHOLD_NAVIGATION.md`, `contracts/household-navigation.v1.json`, `betterinstincts/household_navigation.py` and `scripts/check_household_navigation.py`. Never equate camera pan/visual adjacency with verified Sim travel, movement with progress, or a route proposal with CONTROL_PERMIT. Preserve human-first, off-lot, save, portrait, scene and existing BI-002 boundaries.
