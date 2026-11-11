# Human-first interoperability — P00/P01 executable harness

## Operator-visible state — November 10, 2026

P00 source owner: `AGENTS.md` → `docs/AGENT_OPERATING_RULES.md` /
`docs/DOCTRINE.md` → `contracts/ontology.v1.json` revision 6 /
`contracts/glossary.v1.json`. P01 machine entrypoint:
`contracts/human-first-harness.v1.json` validated by
`python -m scripts.check_human_sovereignty --json`.

These files are repository code/CI evidence; **they are not** an assertion
that Windows, Cursor hooks, installed app, or live Sims game has adopted them.

## Codebase map and owner lanes

| Lane | Canonical owner | Input and result |
| --- | --- | --- |
| Human/idle gate | `betterinstincts/control_handoff.py`, `player_presence.py` | Trusted global input age, explicit busy; fail closed |
| One-screen effect | `betterinstincts/screen_admit.py` | Session/PID, exclusive desktop lock, two idle checks **before** focus, two after, exact Sims foreground |
| Read-only background | `betterinstincts/workflow_interop.py` | Reviewed bounded callbacks, active session, no desktop lease |
| Browser cooperative input | `betterinstincts/playwright_interop.py` | Existing page; per-effect checkpoint and URL/locator validation |
| Win32 game adapters | `scripts/win32_input.py` + explicit caller leases | Raw functions do NOT arbitrate presence; legacy CAS/host-menu paths need adoption review |
| Passive capture | `scripts/game_capture.py` | PrintWindow without focus or input; local screenshot quality unproven |
| Windows denial | `contracts/peripheral-authority.v1.json`, `scripts/check_peripheral_boundary.py` | No Bluetooth, registry, screenshot, Escape/U, accessibility control |
| Cursor project hook | `.cursor/hooks.json`, `.cursor/hooks/operator_boundary.py` | Repository-scoped best-effort guard, not OS sandbox; local activation unobserved |

The machine registry enumerates recognized source paths and known legacy
exceptions; future files with effectful Win32 signatures fail the registry
check until classified. `MIXED_PATHS_REVIEW_REQUIRED`,
`UNADOPTED_LEGACY_NO_LIVE_AUTHORITY` and `LOW_LEVEL_CALLER_GATE_ONLY`
**are known gaps, not approvals**. Do not execute those uncovered paths in
a live game until separately adopted, reviewed, and independently admitted.
Never bypass a known gap by delegating raw input to another agent.

## Agent workflow and scoped skill

1. Open root `AGENTS.md` and mandatory detailed rules. Read P00 ontology
   revision 6 and the sole `effect-authority` contract; never create a rival
   controller, input daemon, or replacement governance file.
2. Declare one branch owner, file scope, effect classification, player/saves
   authority, canonical development/install/worktree path and proof ceiling.
3. For a new effect entrypoint, add a reviewed `sources` record in the
   harness manifest. Unknown source **fails CI** until classified. A
   classification label does not prove runtime gate enforcement.
4. Commit ontology consultation first. Run local semantic preflight, unit
   tests, harness validator, peripheral scanner, doctrine validator, and CI.
5. Diagnose and repair failing contracts or scanner inventory. Preserve
   previous certified game builds and user's saves.
6. Report CHANGED / PROVED / NEXT with exact commit SHA, PR, merge status,
   CI proof and separate local host installation/hook activation/live
   physical-interruption results. No green-PR-to-game-cert promotion.

Scoped Cursor skill:
`.cursor/skills/human-first-interoperability/SKILL.md`. Existing
`.cursor/hooks.json` remains the project hook; **do not install or alter
live machine instructions or devices without explicit operator control**.

## Artifact and canonical path registry

- Machine semantics: `contracts/ontology.v1.json`,
  `contracts/glossary.v1.json`, `contracts/effect-authority.v1.json`,
  `contracts/human-first-harness.v1.json`.
- Consultation receipts: `contracts/consultations/BI-*.v1.json` introduced
  before behavior changes; chronology checked by CI.
- Runnable code/tests: `betterinstincts/`, `scripts/`, `tests/`.
- Durable human report: this file; `docs/LEDGER.md` owns dated status.
  Disposable generated evaluations belong under ignored `dist/`.
- Native installation/path owner: `contracts/workstation-paths.v1.json`,
  resolver `bootstrap.py`. Distinguish development checkout, isolated
  worktrees, user-installed app, actual game Mods path and native entrypoint.
  Never infer the Windows install is current merely from a GitHub merge.

## Checks and proof gates

```sh
python -m scripts.check_human_sovereignty --json
python -m unittest tests.test_human_sovereignty_governance tests.test_human_first_harness -v
python -m scripts.check_ontology
python -m scripts.check_peripheral_boundary
python scripts/validate_doctrine.py
python -m unittest discover -s tests -v
```

CI covers registered source semantics, static denial and offline fixtures.
It cannot prove that raw external agents are blocked, an executing native
Win32 call is preempted, the user regains focus on every monitor, the
operator's keyboard mapping remained physically unchanged, or that a
Sims gameplay mod is installed and working. P08 live canaries must demonstrate
physical takeover with multiple apps, no input after interruption,
safe resume and exact-game foreground, and no peripheral/input setting changes.
BI-002 hunger certification remains independent.

## P00/P01 governance and proof checklist

The mandatory detailed operating contract records instruction precedence,
one-writer branch/worktree ownership, bounded sprint declaration, expected
artifacts, forbidden OS/save mutation, and completion receipts. P00 owns
governance; P01 owns source scanning, codebase and artifact maps, tests and CI;
neither supplies a general OS input bypass. The GitHub-connected runtime
is **not** the installed Windows game host. A maintainer must recheck local
Cursor hook activation and player-reclaim behavior separately.

## Moonwake closers — legacy execution gate, not just registry labels

P83 verified an input-authority discrepancy: registry rows marked
`UNADOPTED_LEGACY_NO_LIVE_AUTHORITY` did not by themselves stop an
`--execute` command from reaching raw foreground focus/Win32 SendInput.
P03's first safe sprint installed the pure repository-owned runtime
`betterinstincts/legacy_screen_boundary.py` denier at the six entrypoints
for CAS completion/placement, quiz/household clicks, school Send Alone,
and multi-step host-menu automation. **These commands now fail closed for
live input**; read-only plans remain available. This is a deliberate
temporary safety block, not completion of functional adapter adoption.

The P01 registry names each legacy `guard_entrypoint` and verifies its
literal denial call via Python AST; new potential input sources are also
discovered under both `scripts/` and `betterinstincts/`. Changing a status
label or inserting an admission keyword in a comment cannot independently
authorize a raw input path. Focus/game mutation remains explicitly unproven
until the adapter is rebuilt on `admitted_screen_lease`, exact game version,
scene/target/queue evidence and at-most-one-effect reconciliation.
In particular, `--operator-screen-released` is not a trustworthy
desktop-wide idle probe or permission to override the player.

This protection is cooperative **inside the repository**. It does not
intercept independent tools, non-Python agents, imported raw Win32 helpers,
or a native call already in progress. No Windows game device was tested or
configured by this repository commit. See
`docs/handoff/BI-HUMAN-FIRST-CLOSERS-P04-2026-11-10.md` for scoped
successor work, ownership and physical local certification.
