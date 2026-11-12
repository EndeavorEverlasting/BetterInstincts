# Local gameplay certification evidence loop — contract v1

## 2026-11-11 — replay-safe observation references (P141 → Fifth Gear)

Each `observation_ref` is a **distinct opaque evidence reference within one run**, including across baseline, modified and rollback stages. Reusing the same reference under a different stage or trial ID is `DUPLICATE_OBSERVATION_REF`: `record` rejects it before appending, and `status`/`evaluate` fail closed on legacy or tampered persisted rows. Two independently observed trials need different evidence references; stage/trial numbers alone do not establish independence. Test fixtures use explicitly synthetic, unique references.

This guard checks string identity only; it does **not** authenticate screenshots, timecodes, observations, trial comparability or that any Sims session actually occurred. Maintainer review of original local game evidence, the 5+5 baseline/modified trials, rollback and player queue remains mandatory. No offline evidence, status percentage or CI run closes BI-002.


## 2026-11-12 — closer proof-reference hygiene

Trial `observation_ref` must be 3–160 characters, nonempty after trimming, free of leading/trailing whitespace and free of unprintable/control characters. A padded spelling, whitespace-only ID or hidden newline/NUL is **not** another independent capture. Invalid references raise `OBSERVATION_REF_INVALID` before appending a new row, and legacy/persisted invalid evidence causes `status` and `evaluate` to fail closed. Existing synthetically generated test IDs remain acceptable when properly shaped; this does not prove the underlying image or observed gameplay is genuine.

Capture IDs are case-sensitive opaque references: the recorder **does not** guess a canonical image from the text or hash private screenshots. Genuine distinct capture verification, selected disposable save, exact patch, 5+5 gameplay trials, rollback and reviewer approval remain outside offline validation.

## What exists
`scripts/live_cert.py` is a **local-only evidence recorder and evaluator**. It never reads Sims game files, installs a mod, inspects Sims processes, polls the filesystem, or collects telemetry. It stores at most 150 bounded rows under `dist/live-cert/<run-id>/` in the repository, excluded from Git. A completed numerical evaluation is **not** a game certificate; it returns `MEASUREMENTS_PASS_REVIEW_REQUIRED` for independent review.

## Local agent quickstart (fill values from actual installed game)
From repo root (Python 3.11+; game Python is separate):
```sh
python -m scripts.live_cert init --run-id bi002-local-001 --game-version 1.121.342.1030 --platform windows --sims4studio-build VERIFIED_LOCAL_BUILD
python -m scripts.live_cert status --run-id bi002-local-001
```
**Example version is instructional only**; replace with the exact main-menu version. First verify exact version support via `python -m scripts.compatibility_status --game-version ACTUAL_FULL_VERSION --platform windows --module hunger`; this currently returns UNKNOWN_VERSION (exit 3) because no game profile is certified. Unknown does not block **experimentation**, but it blocks supported-release claims.

Before any command: select disposable save and explicit Mods root; record game version, enabled packs, S4S version, targeted hunger tuning and worktree status. No automatic game path discovery.

After Sims 4 Studio has exported **one explicitly selected** XML tuning file, run `python -m scripts.tuning_audit --xml "ACTUAL_EXPORTED_XML_FILE"`. This emits the root's resource identifiers, tuning SHA256, and a shortlist of attribute-name hints without copying EA XML into source control. The heuristic list is investigative, not a list of certified safe scoring overrides.

After **each actually observed** baseline, modified and rollback trial:
```sh
python -m scripts.live_cert record --run-id bi002-local-001 --stage baseline --trial 1 --seconds-to-eat 100 --min-hunger 0.2 --sim-lag-ms 50 --player-interruptions 0 --action-loops 0 --exceptions 0 --observation-ref capture:local-baseline-1
python -m scripts.live_cert status --run-id bi002-local-001
```
The numeric values in this example are **synthetic instructions**. Never reuse them as factual measurements. Minimum real observations: >=5 baseline, >=5 modified, >=1 rollback, with stable scenario and distinct capture references. Observations should include evidence captures/timecoded video or experiment notes actually made while the game was running. Use the same units and event definitions across test versions.

After building the game mod and recording its actual hash and vanilla tuning hash:
```sh
python -m scripts.live_cert attest --run-id bi002-local-001 --package-sha256 ACTUAL_64_HEX --tuning-source-sha256 ACTUAL_64_HEX --tuning-resource-id ACTUAL_GAME_RESOURCE --capture-ref evidence:review-001 --disposable-save-confirmed --user-selected-mods-root-confirmed
python -m scripts.live_cert evaluate --run-id bi002-local-001
```
The last command creates `dist/live-cert/<run-id>/report.json` and exits nonzero if incomplete/failing; even a zero exit is **only reviewed numeric observations**. For publication, human maintainer must verify the actual game, tuning, package, evidence and exact patch before signing a separate certification record.

## Machine-observable progress and harness hooks
- **INIT** creates a bounded run manifest; CLI refuses overwritten run IDs.
- **RECORD** appends validated stage/trial rows and emits the updated counts/verdict as JSON; duplicate stages/trials, negative metrics, unsafe paths and excessively large event streams fail.
- **STATUS** returns bounded counts, observation progress percentage (not certification percentage), outstanding stage, and next gate; no background daemon or polling.
- **Compatibility query** uses exact patch, platform and module; an untested version explicitly returns UNKNOWN_VERSION (nonzero exit).
- **Tuning auditor** inspects one explicitly selected XML read-only, bounded to 2MB, without copying game content to Git.
- **STATUS** returns completion counts and `next_gate`, without mutating; agents can run this after each trial to report progress. No background daemon.
- **ATTEST** adds manually verified identifiers/hashes; does not forge or infer data.
- **EVALUATE** writes bounded report, returns numerical pass/fail/incomplete, never emits `CERTIFIED`.
- **PR/CI** validate contracts/synthetic regressions and older certified profiles; a local gameplay recording is not reclassified by CI as observed runtime proof.

## Metrics (predeclared for BI-002)
Median time to begin eating improves by >=15% over >=5 vanilla trials, no player queue interruptions, no action loops or exceptions, modified median observed lag <= max(120% baseline, baseline+5ms), rollback smoke safe. Results are a prototype measure, not universal balance judgment. If vanilla already performs well or the experiment harms gameplay, report falsification and revisit the behavior choice with recorded evidence.

## Privacy and storage
The run receipt contains no OS user paths, save name, household IDs, Sims data, personal names or background collections. Put capture identifiers, **not personal URLs/private screenshots**, in observations. Keep raw media out of Git. A local agent may summarize sanitized evidence in a PR; it must not commit generated `dist/` or personal save data. No automatic upload or hidden telemetry.

## Camera-edge semantic live certification — open P08 gate (2026-11-09)

The operator's "screen edge" means the Sims **client camera-pan trigger/guard area**, not the monitor border. `contracts/camera-traverse.v1.json#edge_interaction` uses a conservative 48px avoidance band; it is **not** a measured engine activation threshold. Offline P82 behavior classification does not prove that mouse movement stops the game camera.

On the **exact installed game build** and a disposable lab save, with user control respected, independently observe and record: (1) window origin/size, display scaling and Live/Build/Buy mode; (2) pointer dwell at all four client edges/corners versus safe interior and whether camera movement actually starts/stops over multiple seconds; (3) top controls, bottom HUD, active-Sim portraits and other near-edge targets successfully clicked without prolonged drift; (4) verified UI action and cursor release followed by host `SAFE_CURSOR_REST`; (5) stable target frame/camera revision after rest, fresh recapture following any pan, and no world click on stale pixels; (6) user activity interruption yields without moving their cursor; (7) unknown focus/scene/target fails closed. Preserve existing save/Build library gates and never treat an offline simulation or SendInput ACK as live camera proof.

A PASS requires timestamped before/after capture(s), exact input session and ownership, observed camera stillness and UI result, plus a non-regression check that the player can use edge controls normally. Keep this gate **OPEN** until those observations exist.
