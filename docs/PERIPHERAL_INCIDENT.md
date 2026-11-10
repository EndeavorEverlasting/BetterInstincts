# Desktop input and Bluetooth incident

Critical incident reported November 10, 2026; onset between the previous night and the report. The primary affected mouse is ProtoArc EM11. A second M343 mouse is a separate diagnosis.

## Ownership

- BetterInstincts owns game capture and cooperative desktop input. Capture must not restore or foreground the game, intercept physical Print Screen, change keyboard/mouse preferences, or configure Bluetooth. `scripts/game_capture.py` now uses passive PrintWindow capture; minimized windows yield an explicit operator-restoration error.
- SysAdminSuite owns Windows peripheral diagnostics and recovery: per-user Bluetooth service state, adapter errors, targeted restart, driver re-enumeration and driver-package recovery. Companion procedure: `docs/field/BLUETOOTH-PERIPHERAL-RECOVERY.md` in SysAdminSuite, branch `fix/bluetooth-peripheral-recovery-20261110`.
- Cursor session attribution remains unresolved. Repository author metadata and overlapping work are insufficient to identify a responsible agent.

## Evidence and limits

An earlier peripheral repair changed the Print Screen shortcut preference. Restoring its previous state was physically confirmed by the operator. The inspected BetterInstincts capture function did not write that preference; PrintWindow is a separate API.

The Bluetooth per-user service was stopped while the main Bluetooth service ran. Historical adapter command timeouts were observed. A targeted adapter restart succeeded and both services subsequently ran. Windows then discovered ProtoArc EM11 NL. Native exact-name ConfirmOnly pairing succeeded and its matching Bluetooth HID mouse node was healthy. The operator confirmed movement and clicks work. Print Screen baseline remained intact. Functional recovery is confirmed; recurrence cause remains open. The operator identifies the per-user service as the likely fault. The service transition and adapter restart occurred together, so service causality is not isolated.

Before this change, capture restored Sims and called SetForegroundWindow, introduced in commit 7fa277b8. This is a confirmed interference mechanism, not proof of the Bluetooth cause. Regression tests protect passive capture and minimized-window refusal. Live capture quality remains unverified.

Do not repair capture failures by altering OS screenshot preferences or resetting peripherals. Human activity in Cursor, Codex or any other app takes precedence over game automation. Other game-input adapters still require their existing fresh player-presence and admission checks; passive capture does not grant input authority.


## Fail-closed Cursor project boundary (stacked hardening after PR #160)

The passive capture fix only covers PrintWindow. Additional project-level pre-effect hooks in `.cursor/hooks.json` route Cursor shell/file effects through `.cursor/hooks/operator_boundary.py` (contract: `contracts/operator-desktop-boundary.v1.json`). The default agent shell action is **DENY** unless it matches a narrow read-only/offline-test allowlist. Agent Delete is denied; agent Write/Edit is repository-scoped and cannot alter the guard configuration, source hooks, AGENTS.md or protected save files. OS service/device/driver/registry/Print Screen mutation and arbitrary shell launch are not available as an automatic capture-repair strategy.

This is defense in depth, not a system-wide security boundary: project hooks must load locally and other IDEs/external computer-control tools need independent enforcement. No hook code changes the operator's Windows settings or installs a service. Verify the hook in Cursor's Hooks output before claiming live coverage. Offline tests in `tests/test_operator_boundary.py` are not proof of host-level activation.
