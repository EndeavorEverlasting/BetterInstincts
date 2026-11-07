# P04 — BetterInstincts game-host canonical handoff

## Entry and proved floor

Read in order: AGENTS.md; docs/DOCTRINE.md; docs/LEDGER.md; docs/GAME_HOST.md; docs/LIVE_CERT.md; plans/active/BI-002.execution.v1.json; this handoff; plans/active/BI-GAME-HOST.dispatch.v1.json.

Source baseline: BetterInstincts main commit c5fd5f16f78568050b3ba5aced9a525f85185c2c, merged PR #11. Its candidate c196b2682cd9a39618d3d1605977878f954f8cea passed GitHub Actions run 42335351712 (offline tests, exact-patch preservation, horizon, doctrine, assets, whitespace, compile). The launcher, UI-selection receipt machine and bounded external sample ingest are BUILT + MERGED + CI-TESTED; no claim of the user's real game launching, a saved household loading, or live Sims behavior mutation has been observed.

Do not create competing plans. The existing BI-MODLAB.HANDOFF.md remains the tooling/DBPF handoff; horizon BI-004 remains recurring income. The parent first playable proof gate is BI-002 hunger and is ACTIVE / BLOCKED_LOCAL_GAME_ACCESS.

## LAUNCH ORDER

0. ALREADY DONE — Current Chat / GitHub provider: code integration of scripts/game_host.py, tests/test_game_host.py and docs/GAME_HOST.md on main; synthetic CI passed; no local Sims access. Preserve these receipts. Do not redo them as an imaginary local sprint.
1. PARALLEL READY WHEN REAL LOCAL WORKERS AVAILABLE — GAME-BOOT (one Windows agent) and TUNING-READONLY (separate read-only Sims 4 Studio inspection). These have distinct output files and no write overlap. Without multiple live local workers, serial local work is valid but parallel execution is UNPROVEN, not passed.
2. AFTER BOTH — HUNGER-LIVE: create and verify one reversible tuning package for the exact installed patch, run at least five vanilla and five modified trials on a reset disposable save, then rollback, player queue, loops, exceptions and latency checks, saving actual capture pointers using scripts.live_cert.
3. AFTER LIVE MODE & KNOWN GAME API — SENSOR-BRIDGE may develop a bounded, opt-in in-game object-state producer; only its verified JSONL snapshot may be fed to scripts.game_host poll. The existing poll is a one-shot external JSONL ingestion and does NOT poll live game objects.
4. AFTER HUNGER TRIALS — MAINTAINER REVIEW independently confirms actual package, patch, gameplay delta, player control, rollback and evidence. A certificate for a new patch requires reviewed proof. No release or automatic live CI/CD promotion before that evidence.

## Exact first host commands

Work in the existing BetterInstincts checkout on the Windows machine that actually has the game. Before changing checkout state, inspect git status and existing worktrees; do not reset or overwrite unrelated dirty work. Read docs/GAME_HOST.md and create a private, ignored dist/game-host/local-profile.json with the exact explicitly selected Sims executable path, disposable save alias and host-specific screenshot templates.

1. python -m unittest discover -s tests -v
2. python -m scripts.game_host plan --profile dist/game-host/local-profile.json
3. python -m scripts.game_host launch --profile dist/game-host/local-profile.json --run-id bi002-first-boot --execute
4. Once the real game main menu is visible: python -m scripts.game_host navigate --profile dist/game-host/local-profile.json --run-id bi002-first-boot --execute --disposable-confirmed
5. python -m scripts.game_host status --run-id bi002-first-boot
6. Only when the intended disposable household is actually in Live Mode, confirm with actual full patch: python -m scripts.game_host confirm --run-id bi002-first-boot --disposable-confirmed --game-version ACTUAL.FULL.PATCH.VERSION --capture-ref capture:live-mode-001

Do not treat New Game click as Live Mode: it first enters Create-a-Sim/placement. Avoid Resume since it could select an unintended personal slot. If a UI step fails midway, per-click receipts prohibit blind replay: inspect the actual screen, safely restart a new session and preserve the original receipt. Never edit, overwrite, delete, migrate or enumerate personal saves; do not auto-discover user-profile folders, copy EA assets or touch other mods. Mods install requires an explicitly chosen BetterInstincts subfolder, preview and rollback. No background daemons, scheduled polling or private account telemetry without distinct authorization.

## Runtime partition and ownership

CURRENT_CHAT_RUNTIME + GitHub provider: source and PR work, done. CI_OR_REMOTE_RUNNER + GitHub Actions: deterministic synthetic checks, passed. LOCAL_AGENT_RUNTIME: selected executable, menu screenshots, Sims4Studio tuning, non-overlapping live A/B and opt-in sensor development; not connected here. OPERATOR_OR_PHYSICAL_RUNTIME: only genuine account authentication, unsafe manual decisions and final maintainer review. GitHub is a provider, never itself the Windows Sims host. Record source, commit, build, run, observation, certification and release as independent states.

## Prompt invocation and factoring receipt

Resolved CURRENT 144-entry Moonwake registry (the renamed TokenCorridor repository), AGENTS.md, invocation resolver and P04 runtime-partition contract. Invoked/applicable semantic workflows: P03 repository evidence; P97 prior-art and game launcher; P141 bounded selection; P41 stateful-game safety; P19 deployment guard; P11/P51/P67/P94/P112/P113 regression and eval; P52 boundary factoring; P66 durable ledger; P83/P84/P115 iterate and repair CI; P105 gated promotion. P61 local checkout occurs only on the game host. P102 ongoing polling and P104 generator are deferred until a real verified game sensor exists. Trifecta in required order: P08 live runtime gate identified BLOCKED_LOCAL_GAME_ACCESS; P82 prototype/measure/refine produced tested safe host slice and repaired failed CI; P07 code committed, CI proved and PR #11 merged. P04 here factors the post-integration local lanes. Prompt semantics applied do not imply external agent skill execution, local game success or completed local parallel dispatch.

The typed dispatch machine map is plans/active/BI-GAME-HOST.dispatch.v1.json. Moonwake's generic parallel dispatch CLI is not installed in BetterInstincts, so this JSON is an ownership/re-entry contract rather than a fabricated runner execution receipt. The local capability ladder must be probed before claiming parallelism. GAME-BOOT and TUNING-READONLY have graph width two, but zero connected real local workers were launched from this chat. Autonomy gap: local Windows launcher + independently authorized game-capable agent attachment, then actual receipt handoff. Do not require the user to paste repeated prompt packs when a verified local worker can operate directly.

## CHANGED | PROVED | NEXT

CHANGED: scripts/game_host.py, tests/test_game_host.py, docs/GAME_HOST.md on main; this P04 handoff and companion dispatch contract on subsequent tracked integration. All game-session output remains Git-ignored under dist/game-host. No game or save bytes were mutated by this remote sprint.

PROVED: PR #11 merged to main at c5fd5f16f78568050b3ba5aced9a525f85185c2c; candidate CI 42335351712 succeeded. Game-host launch is still PROCESS_DISPATCH_ONLY until a real local process observation, then UI requests are CLICK_DISPATCH_ONLY, Live Mode confirmation is OPERATOR_ATTESTATION_UNREVIEWED, ingested state is EXTERNAL_SAMPLE_UNVERIFIED. Neither UI nor JSONL synthetic proof grants GAME_CERTIFIED.

NEXT: run the first real Windows game launch against an explicitly selected disposable slot; provide real patch and Live Mode capture. Inspect hunger tuning, build reversible package, run scripts.live_cert baseline/modified/rollback trials, review and certify only on independently observed evidence. Subsequent patch-specific object sampler and bounded polling/CI promotion are successors, not substitutes for the hunger gate.
