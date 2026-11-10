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

## P00/P01 and portable CLI follow-through

The operator later paired a second mouse and intentionally powered it off while retaining the connected ProtoArc. SysAdminSuite now lists paired-connected, paired-disconnected and unknown separately, prepares a portable runtime without a target SDK, and reports existing/delegated service rights versus required elevation. BetterInstincts ontology revision 4 and the existing cooperative queue preserve arbitrary user interaction, atomic effects and observed reconciliation of partial work.

Validation: 84 focused interop/admission/capture/ontology tests passed; six doctrine tests pass after compacting root routing while preserving detailed mandatory rules. Full CI also exposed UI-microsystem contract failures. The original dcfa26a baseline reproduced the same UI failures (the selected doctrine/UI test group failed with 10 failures and 15 errors before this branch); the pre-existing governance budget failure in that group is now fixed. UI-contract failures remain an integration blocker; the new focused checks are not presented as a green full suite.
