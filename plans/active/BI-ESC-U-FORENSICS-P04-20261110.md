# P04 canonical supporting workload — Escape/U selective input forensics

**Parent:** The Sims 4 Escape key still cancels interactions but does not reliably open the Options/pause menu; U also requires investigation. Find the actual cause, prove repair on the operator's Windows game host, and prevent agent recurrence without compromising human ownership.

**P04 resolved from current Moonwake:** `[PARALLEL] Repo-Aware Sprint + Harness Factoring Distributor`, `EndeavorEverlasting/Moonwake:harness/exports/prompt-invocation-catalog.v1.json` at blob `8c281379ba7ccc871947391233b1db72f4a108ef`, source registry `src/tokencorridor/interface/promptkit/registry/base/prompts.json` at blob `848728632c1243ebba023fa0012292a2ad33cada`, resolver `scripts/prompt_invocation_resolver.py`. Intent is **execute P04 to install a canonical workload**, not to install a new global OS key interceptor.

**Owner and machine identity:** `plans/horizon.v1.json#supporting_workloads.escape_u_input_forensics`; existing `plans/active/BI-HORIZON.dispatch.v1.json` owns the executable lane/dependency contract; execution-wide index `plans/active/BI-HORIZON-EXECUTION-WIDE-20261110.v1.json#escape_u_p04_20261110`. Check `python -m scripts.horizon_status` for `supporting_workloads.escape_u_input_forensics`. This **does not change** `BI-002` as active product gate, `BI-WORLD-TRAVERSAL-P08-SENSOR` as next supporting priority, the existing world launch order, or the needs → income → skills → careers roadmap.

## LAUNCH ORDER — exact P04 lanes

1. **ESC_U_OPERATOR_KEY_MATRIX** — OPERATOR_OR_PHYSICAL_RUNTIME: one-at-a-time manual observations of physical Escape cancellation vs Options-menu access, direct P/0 pause, the three-dots UI, and conditional U/Clubs in an already chosen, safe game session. Operator is always in control. Local evidence only.
2. **ESC_U_CURSOR_PROVENANCE** — LOCAL_AGENT_RUNTIME: *independent read-only* audit of active Cursor project-hook state, process/session timestamps and actually executed tool commands, with user-granted local visibility and redaction. No agent simulates physical key input or uploads raw logs. May be investigated independently; on the one physical machine, it must not contend with the first lane's screen ownership.
3. **ESC_U_RECONCILE** — LOCAL_AGENT_RUNTIME, only after both evidence lanes return either an observed result or explicit unavailable status. Compare competing causes, repair a **proved** source defect under a separately consulted bounded code PR if needed, and re-test actual physical user behavior. Absence of Cursor evidence means `UNATTRIBUTED`, never presumed culpability.

**Parallel capacity:** the first two lanes are dependency-independent, but not proven to run concurrently. No verified local adapter is reachable from the current provider; no concurrent screen/cursor automation is permitted on the operator's Sims host. Source audit/CI can proceed without local game effects; `escape_u_observed_parallelism=false` until real launcher receipts prove otherwise. The existing machine dispatch is the authoritative repo-owned primary manifest; do not introduce a competing local work graph just to duplicate Moonwake's generic `Outputs/prompt-parallel-dispatch/manifest.json`.

## VERIFIED repository floor and outstanding question

- [PR #183](https://github.com/EndeavorEverlasting/BetterInstincts/pull/183) **merged** at `03b8cc488fc856daf35cd6babadf12cd36fe93ad`. Offline CI passed and `main` readback verified that the old `PAUSE_MENU` id now describes a context-dependent Escape cancel/menu event, separate from P clock-pause. U maps to entitlement-gated Clubs; Win32 injected chords release key-downs on interrupt. No physical Windows verification implied.
- Historical code chain: #97 hotkey-first input, #98 Esc cancellation recovery, #104 app-only follow, #110 Esc/cheat-console menu collision, #147 no Esc spam, #160 passive capture, #161 Cursor project effect hook, #162 peripheral authority, #175/#177 human-first semantics, #180 fail-closed legacy adapters. Git metadata alone does not identify a responsible Cursor session.
- The operator's empirical signal: physical Esc works outside Sims and cancels in Sims but not the expected in-game menu action. That suggests a **selective game/UI/input-path defect**, not proof of disabled physical Escape. Keep competing explanations alive: an overlay captures Esc; game UI state or mod interference; an unbalanced injected modifier; a still-running agent; or an independent Windows/game issue.

## Compact preflight / operator authority

- **Host/routing:** ChatGPT + authenticated GitHub provider = `CURRENT_CHAT_RUNTIME` for repository writes; provider is *not* Windows. GitHub Actions = `CI_OR_REMOTE_RUNNER` for offline checks. Cursor's installed Windows environment = `LOCAL_AGENT_RUNTIME` only when verified on host. Actual key test = `OPERATOR_OR_PHYSICAL_RUNTIME`.
- **Owned:** this runbook, existing Horizon/dispatch/validator/status/test/docs authority, sanitized private ignored receipt paths and a future isolated, evidence-based code patch if justified.
- **Forbidden:** touching Windows Bluetooth, drivers, input services, registry or scan-code mappings, Print Screen preferences, accessibility, global hotkey hooks, external apps, original game saves (especially `Slot_00000007`), or live TS4 input without a new explicit permit. Do not treat inability to run UI as authorization to repair devices. Do not kill unrelated applications or capture raw keystrokes.
- **Independent PR writers:** #149 needs/homework and #159 spatial perception remain separate; do not overwrite those branches. PR #183 is already merged, not reopened.

## Lane acceptance and privacy-preserving receipts

**A — Manual input differential:** On a stable Live screen with the exact game build noted, physically verify Esc outside-game and inside-game behavior, first with an overlay/held action and then with no overlay. Record separately `esc_cancel`, `esc_options_menu`, `three_dot_options_menu`, `p_pause_when_clock_playing`, `u_clubs`, `get_together_attested`, `mode`, `game_build` and `automation_active`. U lacking the expansion is `NOT_APPLICABLE`, not broken. P is non-idempotent: test **only** when clock visibly playing, never toggle again blindly. No automatic hotkey replay.

**B — Read-only Cursor attribution:** On an actual local host, inspect `.cursor/hooks.json` activation (not just existence), project path, configured local hooks output, agent process identity, and relevant command/timing data. Record only redacted timestamps, execution outcomes and opaque local references, no raw keystrokes/transcripts or desktop screenshots in public Git. Distinguish `KNOWN_CHANGED_HOST_SETTING`, `PROVED_INPUT_INTERCEPTION`, `RELATED_BUT_UNPROVEN`, and `UNATTRIBUTED`. An unrelated source commit is not evidence that the corresponding agent changed Windows settings.

**C — Reconcile:** Build a table of the two observed dimensions (Options click/menu vs Esc/menu, P pause, and U Clubs) and the active automation state. If Options click fails as well as Esc, investigate game/modal/UI state first. If Options click works while Esc doesn't, compare actual key capture/mod state and agent process timeline. If P pauses while Esc doesn't open menu, do not conflate clock pause with menu failure. If symptoms follow a named process, collect a causal sequence before assigning responsibility. Only a demonstrated effect mechanism may trigger a new scoped patch. Confirm correct human Escape/U behavior in a disposable or otherwise approved game session after correction.

**Local receipts:** `dist/game-host/<approved-run-id>/escape-u-manual-matrix.json` and `dist/game-host/<approved-run-id>/escape-u-cursor-provenance.json` remain private/ignored; publish only sanitized findings and status. Unknown/unavailable evidence stays unknown. No automatic collector, keylogger, watchdog, service or daemon.

## Machine status progression (future local acceptance)

The initial public repository status remains `ROUTED_LOCAL_EVIDENCE_OPEN` with physical observations `NOT_OBSERVED` and attribution `UNATTRIBUTED`. A locally observed result can be recorded as `LOCAL_OBSERVED_WITH_RECEIPT` for `physical_escape_menu`; for `physical_u_clubs` use either `LOCAL_OBSERVED_WITH_RECEIPT` or `NOT_APPLICABLE_PACK_ABSENT` after an actual entitlement review. Cursor hook state may become `LOCAL_VERIFIED_WITH_RECEIPT`; causality may become `DIRECT_LOCAL_EVIDENCE_REVIEWED` only with a direct reviewed session trace. Distinct local receipt references must remain private under `dist/game-host/<approved-run-id>/` and are represented in `supporting_workloads.escape_u_input_forensics.proof_receipts` by safe ignored-path pointers, not raw logs.

Do not change the workload to `REVIEWED_LOCAL_EVIDENCE` until Esc, entitlement-aware U and `physical_recovery=ACCEPTED_AFTER_LOCAL_RETEST` each have independent local receipts; `scripts/check_horizon.py` refuses incomplete promotion. It is acceptable for Cursor attribution to remain `UNATTRIBUTED` after a genuine physical repair. A local accepted game test is still not a BI-002 tuning certification.

## Verification and finish criteria

```sh
python -m scripts.horizon_status
python -m scripts.check_horizon
python -m unittest tests.test_p04_escape_u_workload tests.test_horizon_status -v
python -m unittest tests.test_ui_chrome tests.test_win32_input -v
python scripts/check_human_sovereignty.py
python scripts/check_peripheral_boundary.py
```

Offline PASS = workload is discoverable and guards haven't regressed. Physical key and game acceptance = separate operator-observed gate. Only after both dimensions pass may the incident be marked resolved, and a causal Cursor finding must be independently sourced before assigning responsibility. Keep BI-002 and world-sensor work alive without making this non-gate lane a synthetic global blocker.

**Next exact local read-only command:** `python -m scripts.horizon_status`. Then operator-approved physical A/B input observation and independent read-only provenance lane. Report **CHANGED | PROVED | NEXT**, including actual commit/PR, local hook state and separate physical/Windows/game proof statuses.
