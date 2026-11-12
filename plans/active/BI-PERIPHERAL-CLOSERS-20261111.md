# Peripheral sovereignty — P83 → P03 → P141 → P124 → P04 Closers (2026-11-11)

## Identity, priority, and status
- Parent: never let BetterInstincts agents or game/capture recovery disrupt the human operator's mouse, keyboard, Bluetooth, Print Screen, HID, Windows services/drivers or accessibility and input preferences.
- Main baseline before this sprint: `a44a7c67dd44e8dd36fecbd4435695b674b9ebc5`, merged PR #188. Existing independent safety and offline CI jobs passed. Other live gameplay PRs #149 and #159 are separately owned and must not be modified.
- Host and provider: GitHub provider in CURRENT_CHAT_RUNTIME; this is not the user's Windows host or a local Cursor installation.
- Lane: security regression / agent-harness enforcement. Owned: existing scanner, project pre-effect hook, machine contracts, adversarial tests, ledger and safety handoff. Forbidden: OS repairs, driver/HID/pairing effects, existing game/save state, new daemon, conflicting PRs, unapproved host settings.
- First change: consultation `contracts/consultations/BI-PERIPHERAL-CLOSERS-P83-P03-P141-P124-P04-20261111.v1.json` committed before code changes.
- Validation: `python -m scripts.check_peripheral_boundary`; `python -m unittest tests.test_peripheral_boundary tests.test_operator_boundary -v`; `python -m scripts.check_ontology --base-ref BASE_SHA`; full GitHub CI; `git diff --check`.
- Proof ceiling: source, GitHub CI, merge and provider readback only. Local project hook activation and physical peripheral behavior are unobserved.

## P83 — verify inherited claims, correct the observed gaps
- **Verified:** #188 is merged into main, ontology revision 9/contract/scanner are present; both source and offline GitHub jobs passed.
- **Verified source gap:** scanner omitted executable PowerShell `.psm1` modules (original #188 code review thread PRRT_kwDOVQaLnc62XloJ). The failsafe expression only matched `pyautogui` and `pya`, omitting `gui` as used by this repo (thread PRRT_kwDOVQaLnc62XloN).
- **Verified source gap:** Cursor hook allowed `python -m unittest ...` and `python -m scripts.check_*` while normal agent writes to `tests/*.py` were admitted. A test argv is not inherently safe: importing an agent-edited test can execute arbitrary top-level code on the operator's host.
- **Unproven:** particular AI agent caused the original Bluetooth incident; local Cursor hook was activated; SysAdminSuite observer captured a successful generic Mouse-to-ProtoArc transition; M343 outcome; Sims live gameplay.
- **Repair:** recognize executable PowerShell and Windows helper suffixes; reject any alias disabling a Python input failsafe; deny interpreter/test execution through the Cursor agent shell; protect existing machine policies, validators and boundary tests from ordinary agent file writes. Keep ordinary developer code edits and read-only git diagnostics; route tests to isolated CI.

## P03 — bounded evidence-first sprint
Sole owner of the connected source repair: `.cursor/hooks/operator_boundary.py`, `scripts/check_peripheral_boundary.py`, their respective tests, and existing contracts. No second guard, shell-runner, Windows service or global input hook. First pass reproduces all three source-level gaps with hostile tests. Second pass checks semantic ownership and CI, then merges the exact green head.

## P141 — competing next-investigation theses (not implementations)
1. **Installed project-hook admission proof** (SELECT): The strongest remaining uncertainty is whether the actual local Cursor session loads this hook and denies a mutable test command. **Falsifier:** a controlled benign allow + rejected Python command is seen in current project hook output without any local executable running. Cheapest investigation: local read-only canaries on the operator-owned host. Route to local P08-style real-harness certification; do not call GitHub CI host proof.
2. **Broader CI source recognizers** (ADVANCE HERE only for demonstrated omissions): Incremental known file suffixes and aliased failsafe patterns improve coverage. **Alternative/falsifier:** if source scanning catches these already, no new detector is needed; review #188 and current source established both omissions. Directly included in this bounded P03 repair, not a separate architecture program.
3. **Privileged BetterInstincts Windows repair service** (REJECT): Would centralize mouse recovery but violates the established SysAdminSuite ownership and human-control boundary; no evidence makes it safe or needed.
4. **New generic desktop agent executor/sandbox** (DEFER): Could safely run mutable tests locally, but would introduce a second runtime and authority surface without a measured need beyond GitHub CI. Investigate only if CI cannot support required iterations or an independently reviewed restricted runner already exists.

Selected next strategic investigation: **prove effective local project-hook activation** after safe repository integration; first-source repair is dependency-ready already and should not be blocked by host availability.

## P124 — one canonical place per decision
- Shell/admission: `.cursor/hooks/operator_boundary.py` and `contracts/operator-desktop-boundary.v1.json`.
- Static executable scanner: `scripts/check_peripheral_boundary.py` and `contracts/peripheral-authority.v1.json`.
- Ontology: existing revision 9 is already adequate; no additional semantic concept or vanity revision.
- Regression tests: `tests/test_operator_boundary.py` and `tests/test_peripheral_boundary.py`.
- No new scanner, queue, daemon, scripting system, or background job; preserve each existing owner.

## P04 — dependency, host and dispatch factoring

| Lane | Owner/runtime | Dependency | Action and expected proof | Status |
| --- | --- | --- | --- | --- |
| A — code hardening | GitHub provider / CURRENT_CHAT_RUNTIME | Existing merged #188 | Commit reviewed guards/tests, verify independent safety and full CI, integrate green PR into main; preserve commits and SHA | IN_PROGRESS at sprint entry; close with provider receipt |
| B — Cursor activation | Operator-approved LOCAL_AGENT_RUNTIME on Windows | A merged to canonical local checkout | Inspect Cursor Hooks output, benign `git status --short` allow and `python -m unittest tests.test_operator_boundary -v` **denied before execution**; record sanitized allow/deny receipt and real host path; no registry/Bluetooth/game changes | HOST_GATE_UNPROVEN; no local executable agent access through this provider |
| C — SysAdminSuite recurrence | SysAdminSuite local Windows owner / OPERATOR_OR_PHYSICAL_RUNTIME | Natural recurrence, independent of A/B | Observer captures preselection endpoint IDs and later names/HID/movement; separately test M343; never auto-pair ambiguous `Mouse` entries | EXTERNAL_OWNER_AND_PHYSICAL_GATE |
| D — Sims gameplay | BetterInstincts BI-002 local game-lab owner | Exact build, authorized disposable session | Vanilla/modified hunger trials + rollback; unrelated to peripheral closeout and not a prerequisite | EXISTING_ACTIVE_PARENT_UNPROVEN |

Execution placement: A stays in current GitHub-connected runtime. B and C are not safe to simulate on the GitHub runner, and the operator's local Windows host cannot be accessed from this runtime. No dispatch claim for those lanes. A is a single shared-file dependency-writer; **PARALLEL EXECUTION: NOT_APPLICABLE — source repair graph width is 1**. After merge B and C are separate host owners and may proceed independently when their own safe adapters are available. Do not ask the operator to relay repo context between agents.

## Closeout standard
CHANGED: list exact paths and correction. PROVED: independently observed CI/job status, merge SHA and readback. NEXT: one host-side activation check with benign allow + denied Python intent, no execution. Keep `ROOT_CAUSE_NOT_ISOLATED`, `NO_AGENT_ATTRIBUTION`, `LOCAL_HOOK_UNOBSERVED`, and `BI-002_ACTIVE` unchanged until distinct evidence exists.
