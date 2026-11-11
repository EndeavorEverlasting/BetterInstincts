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


## Fail-closed Cursor project boundary (stacked hardening after PR #160)

The passive capture fix only covers PrintWindow. Additional project-level pre-effect hooks in `.cursor/hooks.json` route Cursor shell/file effects through `.cursor/hooks/operator_boundary.py` (contract: `contracts/operator-desktop-boundary.v1.json`). The default agent shell action is **DENY** unless it matches a narrow read-only/offline-test allowlist. Agent Delete is denied; agent Write/Edit is repository-scoped and cannot alter the guard configuration, source hooks, AGENTS.md or protected save files. OS service/device/driver/registry/Print Screen mutation and arbitrary shell launch are not available as an automatic capture-repair strategy.

This is defense in depth, not a system-wide security boundary: project hooks must load locally and other IDEs/external computer-control tools need independent enforcement. No hook code changes the operator's Windows settings or installs a service. Verify the hook in Cursor's Hooks output before claiming live coverage. Offline tests in `tests/test_operator_boundary.py` are not proof of host-level activation.

## Direct game-host navigation (second admission gap)

`scripts/game_host.py navigate --execute` previously used `pyautogui.locateAllOnScreen` and `gui.click` without the canonical per-process screen lease. It now requires an active host-listener session bound to the launched Sims PID on Windows, holds `betterinstincts.screen_admit.admitted_screen_lease`, confirms two fresh idle-presence samples, and requires the exact Sims PID to own foreground before **each template observation and each click**. A changed foreground, missing session, expired/unknown human-idle evidence or competing input ownership fails closed rather than restoring or hijacking another window. Offline FakeGui tests remain offline; they do not prove live Windows behavior.

## Escape/U selective game-input forensic matrix

**Open issue; no physical host proof yet (2026-11-10).** The operator reports physical Escape works in Windows and cancels an in-game action, but does not consistently open the Sims Options/pause menu; U was also reported affected. This narrows the failure to context-sensitive in-game handling without proving whether the cause is a Sims UI/modal state, a mod, another process, or an injected-key side effect. GitHub commit/PR authorship cannot identify an individual Cursor session or prove it edited Windows keyboard settings.

**Repository evidence chain:** #97 introduced the hotkey-first Win32 dispatch; #98 introduced planned Escape cancellation after missed clicks; #104 added app-scoped (uninstalled) camera follow hotkey semantics; #110 explicitly stopped using Esc to close the cheat console because it opened the game menu; #147 prohibited Escape spam; #160 corrected focus-stealing capture; #161 added project-scoped Cursor pre-effect hooks (activation on this host unverified); #162/175/177/180 strengthened authority/adoption boundaries. The original shared `scripts/win32_input.py#send_key_chord` used press/release loops without `finally`, so exceptions could strand synthetic key-downs. The bounded current repair balances injected key-up on interruption. **This is a proven source-level gap, not a proven incident cause.** Source code uses virtual keys and does not install a global keyboard hook or remap physical Escape/U.

### Read-only manual test (operator-owned; no unattended input)

1. Let BetterInstincts/Cursor input automation become inactive or terminate its **own** jobs without disabling Windows devices, services or accessibility; keep the affected save untouched. Use a disposable game session if entering gameplay.
2. With the **physical** keyboard and Sims visibly foregrounded, record exact game build, Live/Build/Buy, visible modal/held object/cheat console, and whether the Options **three-dots** click works. Do not repeatedly press Esc.
3. In an active overlay, press Esc **once**: did it cancel? With no overlay or held object, press Esc **once**: did Options open? These are different expected paths. Use P (or 0) **only if the clock is visibly running** to test direct pause; do not toggle it again while paused/unknown.
4. Test U only in verified Live Mode and **only** if Get Together/Clubs is available. Otherwise record `PACK_OR_UI_UNVERIFIED`, not a failed keyboard. Test typing a literal U in a benign external text field separately, without key injection or remapping.
5. Compare with the three-dots menu button. If neither Esc nor three-dots opens Options, examine game UI/modal/mod state before alleging key remapping. If P/0 pauses but Esc fails to open Options, the clock key path works and the failure is menu-specific. If the fault disappears only when a particular automation exits, collect its process/session/command timeline before attributing causality.
6. Store a **sanitized** per-case outcome table (no raw keystroke capture, game saves, user documents, or private log payloads): timestamp, process/PID, game build, scene, overlay, human vs injected, menu-click, Esc-cancel, Esc-menu, P/0 pause, U/Clubs entitlement, automation-active, result. Do not make host setting changes to conduct this test.

**No-agent host mutation rule:** no registry remap edits, `BlockInput`, global keyboard hook, Bluetooth/service restart, Print Screen setting, keyboard accessibility change, save edit, force-kill of unrelated apps, or agent-controlled key test while the player owns the desktop. The next closure gate is locally reproduced human-input behavior and, if indicated, read-only Cursor session/tool-call timeline correlated to timestamps. A green GitHub CI run cannot certify physical input.

