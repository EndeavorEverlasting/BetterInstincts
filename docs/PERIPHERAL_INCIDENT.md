# Desktop input and Bluetooth incident

Critical incident reported November 10, 2026; onset between the previous night and the report. The primary affected mouse is ProtoArc EM11. A second M343 mouse is a separate diagnosis.

## Ownership

- BetterInstincts owns game capture and cooperative desktop input. Capture must not restore or foreground the game, intercept physical Print Screen, change keyboard/mouse preferences, or configure Bluetooth. `scripts/game_capture.py` now uses passive PrintWindow capture; minimized windows yield an explicit operator-restoration error.
- SysAdminSuite owns Windows peripheral diagnostics and recovery: per-user Bluetooth service state, adapter errors, targeted restart, driver re-enumeration and driver-package recovery. Companion procedure: `docs/field/BLUETOOTH-PERIPHERAL-RECOVERY.md` in SysAdminSuite, branch `fix/bluetooth-peripheral-recovery-20261110`.
- Cursor session attribution remains unresolved. Repository author metadata and overlapping work are insufficient to identify a responsible agent.

## Evidence and limits

An earlier peripheral repair changed the Print Screen shortcut preference. Restoring its previous state was physically confirmed by the operator. The inspected BetterInstincts capture function did not write that preference; PrintWindow is a separate API.

The Bluetooth per-user service was stopped while the main Bluetooth service ran. Historical adapter command timeouts were observed. A targeted adapter restart succeeded and both services subsequently ran. The operator identifies the per-user service as the likely fault. The service transition and adapter restart occurred together, so service causality is not isolated. Mouse movement/click confirmation remains required before closure.

Before this change, capture restored Sims and called SetForegroundWindow, introduced in commit 7fa277b8. This is a confirmed interference mechanism, not proof of the Bluetooth cause. Regression tests protect passive capture and minimized-window refusal. Live capture quality remains unverified.

Do not repair capture failures by altering OS screenshot preferences or resetting peripherals. Human activity in Cursor, Codex or any other app takes precedence over game automation. Other game-input adapters still require their existing fresh player-presence and admission checks; passive capture does not grant input authority.
