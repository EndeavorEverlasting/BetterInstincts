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

## P02/P12 refreshed successor ownership

The current work includes Cursor hooks in stacked PR #161, base #160 branch, inspected at cebec2d. This is a separately owned agent-harness implementation, not proof of local activation. Five of six local Windows hook tests passed; the symlink-creation fixture required an unavailable privilege (WinError 1314). The original external-adapter gap is narrowed only for registered/loaded Cursor event paths. Parent UI-contract CI repair, Windows hook fixture portability and actual allow/deny canaries remain distinct gates. Canonical successor panels/factoring/proof map are tracked in SysAdminSuite docs/plans/bluetooth-desktop-closeout-20261110.plan.md (PR #562); docs/LEDGER.md carries the local pointer. Do not modify the #161 branch from this parent lane.

## Windows peripheral ownership — cross-repository fail-closed semantic boundary

Machine contract: `contracts/peripheral-authority.v1.json`. BetterInstincts may observe game state and, after independent player/context admission, operate the **game**; it may not configure Windows Bluetooth service state, PnP radio/driver nodes, pairing records, input locks or screenshot/mouse preferences. A game capture error, unusable pointer, stalled desktop, stopped `BluetoothUserService_*`, Bluetooth PIN prompt or invisible mouse routes to the existing SysAdminSuite field recovery owner, not a game adapter or new orchestration subsystem. Even an apparently idle player does not authorize OS repair. `scripts/check_peripheral_boundary.py` is a source-level regression barrier for this owned code; external agents and processes are not kernel-sandboxed by this checker. In-source and newly registered adapters still require independent player/session/scene/intent gates. Never claim that a static scan proved a third-party agent cannot touch Windows.

The operator has confirmed both Bluetooth mice connect after repair of Windows Bluetooth services. Functional Bluetooth pairing is recovered. The earlier simultaneous adapter/service transitions do not establish a uniquely isolated underlying failure cause. BetterInstincts' historical game-window foreground interference is a **separate proved defect** and must not be misrepresented as a Bluetooth-service cause. This keeps `RCA`, `functional acceptance`, `OS owner`, `game-side protective controls`, and `live runtime proof` distinct.
