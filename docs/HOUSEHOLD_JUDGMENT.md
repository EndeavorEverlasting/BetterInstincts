# Fixed-roster household skill judgment — Fifth Gear (2026-11-09)

**Goal:** Level requested skills on the original N portraits, without creating characters, going online or competing for desktop control.

## Algorithm

1. Observe the Live portrait count and exact ordered identities. Attest the first selected portrait. N is not a guessed cap.
2. For skill S1, level portrait 0, then 1 through N−1 to the target (normally 10). Close the console within each cell. Space advances only under fresh admitted input ownership. Never toggle the already-closed console before Space.
3. Repeat for skill S2 only after S1 visits all N portraits. Skip previously dispatched cells through the existing completion ledger, while retaining portrait alignment.
4. Use bounded play-brief, Skills panel observation and re-pause. Cheat text, toasts and DISPATCHED ledger entries are not level-10 PASS.

## Hard judgment boundaries

Skill progression does not authorize adding or creating a Sim or Servo, merging households, CAS additions, new pets, Build/Buy mutations, Gallery, Store, EA Connect or internet features. A new member increases N and violates the approved task. A changed/reordered/missing roster means STOP_AND_RECONCILE. When an observed connection-required modal appears, select Stay Offline, not Connect. Player commands always outrank host automation.

Run foreground-only. Detached household skill screen-input workers are rejected before launch. No daemon or second scheduler is created. The opt-in CLI requires repeated --roster-key values matching --members and --first-portrait-attested, plus a verified local host session and PID. The policy module is only a fail-closed scope evaluator: it cannot itself grant a control permit.

**Important proof ceiling:** The remote GitHub planning/execution code does not currently capture live on-screen portrait IDs. Comparing CLI-provided roster keys with themselves checks input structure, NOT actual game roster stability. Real P08 proof therefore requires the local Windows game agent to observe selected portraits between steps, reject drift, inspect the skills panels on a disposable save and record an exact-game-build receipt. Do not assert automatic prevention of all other independent Cursor processes.

## Canonical owners

- Skill catalog and traversal: betterinstincts/diy_skill_force.py, scripts/diy_skill_force.py, contracts/diy-skill-force.v1.json.
- Judgment policy: contracts/household-judgment.v1.json, betterinstincts/household_judgment.py.
- Global menu offline guard: betterinstincts/menu_blockers.py, contracts/host-menu.v1.json.
- Player and screen admission: betterinstincts/screen_admit.py; independent save/build rules remain intact.

## Acceptance and prompt roles

P95 repairs the console/Space call stack; P82 supplies falsifiers; P124 keeps one owner; P07 owns tests, CI and main-branch integration; P08 is genuine local-game observation and remains open without such receipts. P00/P01 preserve governance and harness safety. Before an operator installs changed live Cursor user rules, archive and verify the current settings; a GitHub merge is not local activation.

Plan only (no game input): python -m scripts.diy_skill_force household --members 3 --skill handiness

Local opt-in example: python -m scripts.diy_skill_force household --members 3 --skill handiness --execute --roster-key SIM_A --roster-key SIM_B --roster-key SERVO_C --first-portrait-attested --process-id PID --session-id SESSION

Report CHANGED | PROVED | NEXT, separating planner, typed cheat, panel observation, merge and local installed state.

## P83 review and P04 Windows install / P08 live gate (2026-11-09)

The latest [local handoff](handoff/BI-HOUSEHOLD-SKILL-LOCAL-P04-2026-11-09.md) and [dispatch manifest](../plans/active/BI-HOUSEHOLD-SKILL-LOCAL-P04.dispatch.v1.json) supersede copy-and-run bulk examples as **operator guidance** until the real per-cell selected portrait/roster observer and per-effect player-input gate are proven on a disposable Windows save. The prior command-line `--roster-key` comparison only checks typed roster values against themselves. `DISPATCHED` ledger skip receipts are not panel proof; with no dispatch remaining the result is `HOUSEHOLD_SKILL_FORCE_NO_PENDING_DISPATCH_UNVERIFIED` and the executor performs **zero** game input. The default bootstrap recipe is a plan only. Do not alter existing user saves, the roster, account settings or online mode. This remote repo change does not install or run anything on the local game host.

Single-member skip records are also named `SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED` and do not move the cursor. The distinction applies to both cell and whole-household observations; neither provides live Skills-panel proof.
