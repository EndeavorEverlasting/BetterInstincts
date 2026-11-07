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

## 2026-11-06 — First real CAS boot follow-on: baseline preparation

PR #13 was merged at `240811991a183ce2d99b07c42f8056587c0d6cce`. First real `TS4_x64` boot reached CAS for patch `1.121.361.1020` DX11; no Live Mode, vanilla trials or modified evidence observed. Focus-stealing automation is a known failure mode. Physical/operator gate remains select **No thanks!** → disposable adult Sim → empty lot → Live Mode, and signal `READY_LIVE` to the LOCAL game agent.

Once the agent independently observes the intended disposable Live Mode state, run the previously recorded `game_host confirm` command with the actual patch and private capture ref; immediately run `python -m scripts.game_baseline --run-id bi002-first-boot`. The new command creates/reuses an empty, version-bound `live_cert` run; `NOT_OBSERVED` Studio permits vanilla baselines only and blocks package attestation until a real Studio build is captured via `python -m scripts.live_cert studio --run-id bi002-first-boot --build ACTUAL_STUDIO_BUILD`. Run status, take five real vanilla measurements and record each with full evidence. Do not fake numbers, synthesize rows or represent recipe readiness as a Live Mode observation. Local game control is not present in this ChatGPT runtime; no fake focus recovery or automation was launched here.

## 2026-11-07 — Current successor gate after P95/P67/P62 evaluator merge

**Current repository proof**: PR #21 merged to main at commit d102d9b1413024a1fd330494a4e41f9ce3ed1a3c. GitHub Actions main run 42392413124 PASSED: 178 offline tests, one skipped, focused evaluator, backward compatibility, horizon, doctrine, scene/save safety, assets, whitespace, and compile. New tracked paths: betterinstincts/host_eval.py, scripts/host_eval.py, tests/fixtures/host-eval.v1.json, tests/test_host_eval.py, docs/HOST_EVAL.md. Host_stack and instincts_host now gate player-directed/busy/absent action and Save As. These results are NOT live Sims evidence.

**Outstanding local live incident**: prior run bi002-quiz-boot on Windows/TS4 patch 1.121.361.1020, disposable Charlee LabLab / Bargain Bend, observed PrintWindow FULL_CLIENT_BLACK and operator secondary-monitor mouse-tracking platform wireframe. Camera ladder attempted but failed to restore the viewport. PID 45380 is a *historical* PID, not a verified current process. No confirmed process restart, loaded household, or six-needs-green receipt has been obtained in this provider-only session. Do NOT Resume, overwrite personal/Richardson saves, or target another Sims process.

**First executable Windows host gate**:
1. Inspect current checkout status and pull the merged main safely (no destructive reset). Identify current TS4_x64 process/window using the existing local-game capability; independently verify current PID, executable and intended disposable session before any WM_CLOSE. If no matching process remains, do not attempt to close historical PID 45380.
2. If matching session is still anomalous, use the existing gated recovery command with CURRENT_CONFIRMED_PID (not historical PID):
   
   python -m scripts.viewport_recover --capture --process-id CURRENT_CONFIRMED_PID --execute --authorize-restart --run-id bi002-quiz-boot --out dist/game-host/bi002-quiz-boot/viewport-restart.png --receipt dist/game-host/bi002-quiz-boot/viewport-restart-receipt.json

   The authorization is limited to the previously described disposable lab restart. Verify WM_CLOSE dispatch, then actual process exit; WM_CLOSE_POSTED is not exit proof. Do not use TerminateProcess, and do not blindly replay a receipt.
3. Relaunch and select ONLY the registered LAB_CREATED LabLab disposable save through the existing game_host + save_guard path. Use a fresh run ID if the previous receipt namespace cannot safely be reused. Never Resume. Verify PrintWindow CONTENT_PRESENT *and* independent map/Live scene cues before performing need clicks. PrintWindow can miss DX wireframe, so treat a conflicting secondary-display observation as an anomaly requiring investigation.
4. Prefer Send Alone to Join while needs are critical; maintain control of the home lot. Inspect six need levels and real object availability; obtain/place safe lab objects for food, bathroom, energy, hygiene, fun and social. Respect player direction and busy/absent state; do not execute a needs click until the host gate is safe. Record before/after needs and host action IDs.
5. Run the deterministic evaluator on real **operator/sensor-attested** observations, not the committed synthetic fixtures:

   python -m scripts.host_eval --cases dist/game-host/bi002-quiz-boot/host-eval-observations.v1.json --out dist/host-eval/bi002-quiz-boot.json

   The input must comply with the versioned fixture fields; a CI fixture pass does not attest the actual runtime. A blocked or incomplete evaluation means repair/recapture before acting.
6. After all six needs are independently observed green, Save As a NEW BI_CONT continuation only under the existing save guard and player-authorization gates. Keep BI-002 hunger live_cert 5 vanilla + 5 modified measurements, rollback, queue safety and maintainer review separate and still ACTIVE.

**P95/P67/P62 and Trifecta proof**: P95 call-stack design and prototypes plus P67/P62 executable deterministic regression layers were applied and CI-verified. The Moonwake local Windows Trifecta/orchestration process was not executable from the GitHub-only provider context and has NOT been marked as invoked or passed. The next local agent must run the real local capability/orchestration gate, then distinguish local runtime receipts from these repository tests.

**Next success condition**: actual process/window and lab save verified, PrintWindow CONTENT_PRESENT, map and Live independently attested, six needs observed and tended without player override, new guarded lab continuation Save As when green, durable real receipt. No declarations of GAME_CERTIFIED before BI-002 live A/B proof.
