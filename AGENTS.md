# BetterInstincts: canonical agent entrypoint

Before edits, samples or experiments, read mandatory `docs/AGENT_OPERATING_RULES.md`, `docs/ONTOLOGY.md`, `docs/DOCTRINE.md`, `docs/LEDGER.md` and `docs/PROMPT_INVOCATIONS.md`. Commit `contracts/consultations/` before behavior changes; run `scripts/semantic_preflight.py`. Detailed rules are preserved, not waived.

## P00/P01 interaction sovereignty

Ontology revision 4 embraces any user-chosen game/mod, mouse, keyboard, voice/assistive or other-app interaction. Adopted autonomous effects yield on activity or unknown presence. Resume after two fresh trusted idle probes and target revalidation. Prefer verified native semantic APIs; desktop fallback requires explicit opt-in. Use the existing cooperative queue's enqueue_effect; partial work retains intent and requires observed reconciliation plus a rebuilt remainder. Never change peripheral preferences or UAC to aid automation. Passive capture never steals focus. Unadopted agents and executing native calls are not forcibly intercepted.

## Invariants

- **Player first:** explicit user control wins; no uncontrolled loops. Preserve any chosen interaction shape.
- **Save-safe:** Unknown/user saves protected. Never edit/delete/migrate/overwrite saves or game files; never delete Slot_00000007.
- **Build structure / FLOOR_2:** before any Build/Buy purchase or mutation, census all floors/rooms, back up to My Library and verify model readback. Retain `admit_live_structure_effect`; unknown coverage denies. Details: docs/BUILD_LIBRARY_CHECKPOINT.md.
- **Storage:** no arbitrary profile writes, auto-discovery, daemons, telemetry or unbounded logs.
- **Performance:** bounded work; no per-frame global scans or unmeasured hooks.
- **Evidence:** separate tests, build, PR, merge and gameplay. docs/SCENE_INTELLIGENCE.md owns independent cues; unknown denies.
- **Continuity:** preserve intent and update docs/LEDGER.md, docs/ROADMAP.md and active sprint; no chat-only corrections.
- Offline installation only; never EA Connect. Preserve lot-boundary, EA-file-first geometry and live-host policies in the mandatory detailed rules.

## Trajectory and proof

plans/active/BI-001.md is merged; plans/active/BI-002.md owns the game-lab gate. docs/HORIZON.md and plans/horizon.v1.json retain six needs, balance, income, skills and career order. docs/COMPATIBILITY.md and docs/LIVE_CERT.md require exact game build and immutable older certifications. BI-002 requires actual vanilla/modified trials and rollback; absent host means BLOCKED_LOCAL_GAME_ACCESS, active rather than complete. Report CHANGED | PROVED | NEXT, checks, SHA, push/PR/merge and actual live status. An offline pass is not gameplay proof.

## Operator desktop effect boundary (PR #160 → #161)

Operator control of keyboard, mouse, Bluetooth/HID devices, screenshot preferences and personal saves outranks automation. Never use Windows service/driver/device reset, registry changes, Print Screen remapping, forced foreground, or protected-save mutation as a capture recovery workaround. Game capture is passive; game input requires fresh player-presence, shared desktop ownership and game-specific admission independently.

Cursor project pre-effect policy: `.cursor/hooks.json` → `.cursor/hooks/operator_boundary.py`, governed by `contracts/operator-desktop-boundary.v1.json`, `docs/PERIPHERAL_INCIDENT.md` and `tests/test_operator_boundary.py`. Unknown shell/effect actions fail closed; write/delete outside the repository and writes to protected policy are denied. No agent may disable, dodge or remove the guard to complete a task. Other harnesses require their **own** equivalent enforcement; a checked-in hook is not proof of local Cursor activation or OS-wide isolation. Operator-reviewed Windows peripheral recovery is owned by SysAdminSuite, not BetterInstincts.
